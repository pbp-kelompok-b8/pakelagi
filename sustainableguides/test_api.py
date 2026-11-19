from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import Guide

User = get_user_model()

class GuideRESTAPITests(APITestCase):
    """Menguji endpoint REST API (GET, POST, PUT, PATCH, DELETE), otorisasi, dan sanitasi XSS."""

    def setUp(self):
        self.user_a = User.objects.create_user(username='apiauthor', password='password123')
        self.user_b = User.objects.create_user(username='otheruser', password='password123')

        self.published_guide = Guide.objects.create(
            author=self.user_a,
            category='PERAWATAN',
            title='Panduan API Terbit',
            ringkasan='Ringkasan API',
            konten='## Cara Mencuci\nGunakan air dingin.',
            status='DISETUJUI',
            is_published=True,
            date_published=timezone.now()
        )
        self.pending_draft_a = Guide.objects.create(
            author=self.user_a,
            category='REUSE',
            title='Draf API Pending A',
            ringkasan='Ringkasan draf A',
            konten='Isi draf A',
            status='PENDING',
            is_published=False
        )

    def test_api_get_published_guides_list_and_filter(self):
        url = reverse('sustainableguides:api_list_create')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], 'Panduan API Terbit')

        # Filter kategori yang tidak ada item terbitnya
        res_filtered = self.client.get(url + '?category=REUSE')
        self.assertEqual(res_filtered.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_filtered.data), 0)

    def test_api_create_guide_requires_authentication_and_sanitizes_xss(self):
        url = reverse('sustainableguides:api_list_create')
        payload = {
            'category': 'PERBAIKAN',
            'title': 'Judul <script>alert(1)</script>Baru',
            'ringkasan': 'Ringkasan <b>aman</b>',
            'konten': 'Isi panduan lengkap.',
            'image_url': 'https://images.unsplash.com/photo-123'
        }

        # Anonim ditolak (401/403)
        res_anon = self.client.post(url, payload, format='json')
        self.assertIn(res_anon.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

        # User login berhasil membuat draf berstatus PENDING
        self.client.force_authenticate(user=self.user_a)
        res_auth = self.client.post(url, payload, format='json')
        self.assertEqual(res_auth.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res_auth.data['title'], 'Judul alert(1)Baru')
        self.assertEqual(res_auth.data['status'], 'PENDING')
        self.assertFalse(res_auth.data['is_published'])

    def test_api_detail_visibility_permissions(self):
        # Panduan yang sudah terbit bisa diakses anonim
        pub_url = reverse('sustainableguides:api_detail', args=[self.published_guide.id])
        res_pub = self.client.get(pub_url)
        self.assertEqual(res_pub.status_code, status.HTTP_200_OK)
        self.assertIn('<h2>', res_pub.data['content_html'])

        # Draf yang belum terbit tidak bisa dilihat oleh pengguna lain (404)
        draft_url = reverse('sustainableguides:api_detail', args=[self.pending_draft_a.id])
        self.client.force_authenticate(user=self.user_b)
        res_other = self.client.get(draft_url)
        self.assertEqual(res_other.status_code, status.HTTP_404_NOT_FOUND)

        # Pemilik draf bisa melihat draf miliknya sendiri
        self.client.force_authenticate(user=self.user_a)
        res_owner = self.client.get(draft_url)
        self.assertEqual(res_owner.status_code, status.HTTP_200_OK)

    def test_api_update_and_delete_permissions(self):
        draft_url = reverse('sustainableguides:api_detail', args=[self.pending_draft_a.id])

        # User B mencoba PATCH draf milik User A -> 403 Forbidden
        self.client.force_authenticate(user=self.user_b)
        res_forbidden = self.client.patch(draft_url, {'title': 'Bajakan'}, format='json')
        self.assertEqual(res_forbidden.status_code, status.HTTP_403_FORBIDDEN)

        # User A melakukan PATCH pada draf miliknya yang masih PENDING -> 200 OK
        self.client.force_authenticate(user=self.user_a)
        res_ok = self.client.patch(draft_url, {'title': 'Judul Diperbarui via API'}, format='json')
        self.assertEqual(res_ok.status_code, status.HTTP_200_OK)
        self.pending_draft_a.refresh_from_db()
        self.assertEqual(self.pending_draft_a.title, 'Judul Diperbarui via API')

        # User A mencoba mengubah panduan yang sudah DISETUJUI -> 400 Bad Request
        pub_url = reverse('sustainableguides:api_detail', args=[self.published_guide.id])
        res_locked = self.client.patch(pub_url, {'title': 'Coba Ubah'}, format='json')
        self.assertEqual(res_locked.status_code, status.HTTP_400_BAD_REQUEST)

        # User A menghapus draf miliknya yang masih PENDING -> 204 No Content
        res_del = self.client.delete(draft_url)
        self.assertEqual(res_del.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Guide.objects.filter(id=self.pending_draft_a.id).exists())