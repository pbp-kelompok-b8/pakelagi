from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import Client, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from profiles.models import Profile

from .models import Guide

User = get_user_model()

@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class GuideRESTAPITests(APITestCase):
    """Menguji endpoint REST API (GET, POST, PUT, PATCH, DELETE), otorisasi, dan sanitasi XSS."""

    @classmethod
    def setUpTestData(cls):
        cls.password = 'Guide-test-session-password'
        cls.user_a = User.objects.create_user(username='apiauthor', password=cls.password)
        cls.user_b = User.objects.create_user(username='otheruser')
        Profile.objects.create(user=cls.user_a, display_name='Penulis')
        Profile.objects.create(user=cls.user_b, display_name='Member lain')

        cls.published_guide = Guide.objects.create(
            author=cls.user_a,
            category='PERAWATAN',
            title='Panduan API Terbit',
            ringkasan='Ringkasan API',
            konten='## Cara Mencuci\nGunakan air dingin.',
            status='DISETUJUI',
            is_published=True,
            date_published=timezone.now()
        )
        cls.pending_draft_a = Guide.objects.create(
            author=cls.user_a,
            category='REUSE',
            title='Draf API Pending A',
            ringkasan='Ringkasan draf A',
            konten='Isi draf A',
            status='PENDING',
            is_published=False
        )

    def test_canonical_routes(self):
        self.client.force_authenticate(user=self.user_a)
        for url in (
            '/api/v1/guides/', '/api/v1/guides/my-submissions/',
            f'/api/v1/guides/{self.pending_draft_a.pk}/',
        ):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_incomplete_owner_cannot_manage_or_read_private_guides(self):
        collection = reverse('guides_api:list')
        history = reverse('guides_api:my_submissions')
        detail = reverse('guides_api:detail', args=[self.pending_draft_a.pk])
        public_detail = reverse('guides_api:detail', args=[self.published_guide.pk])
        payload = {'title': 'Judul baru', 'ringkasan': 'Ringkasan baru', 'konten': 'Isi baru'}
        self.client.force_authenticate(user=self.user_a)
        profile = Profile.objects.get(user=self.user_a)
        profile.display_name = '  '
        profile.save(update_fields=['display_name'])

        for state in ('blank', 'deleted'):
            if state == 'deleted':
                profile.delete()
            for method, url, expected in (
                ('get', history, 403), ('get', detail, 404), ('post', collection, 403),
                ('put', detail, 403), ('patch', detail, 403), ('delete', detail, 403),
            ):
                with self.subTest(profile=state, method=method, url=url):
                    kwargs = {'data': payload, 'format': 'json'} if method in {'post', 'put', 'patch'} else {}
                    response = getattr(self.client, method)(url, **kwargs)
                    self.assertEqual(response.status_code, expected)
            self.assertEqual(self.client.get(collection).status_code, 200)
            self.assertEqual(self.client.get(public_detail).status_code, 200)

        self.assertEqual(Guide.objects.count(), 2)
        self.pending_draft_a.refresh_from_db()
        self.assertEqual(self.pending_draft_a.title, 'Draf API Pending A')

    def test_api_get_published_guides_list_and_filter(self):
        url = reverse('guides_api:list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], 'Panduan API Terbit')

        # Filter kategori yang tidak ada item terbitnya
        res_filtered = self.client.get(url + '?category=REUSE')
        self.assertEqual(res_filtered.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_filtered.data), 0)

    def test_public_reads_hide_unapproved_and_unreleased_guides(self):
        now = timezone.now()
        for review_status, is_published, date_published in (
            ('PENDING', True, now),
            ('DITOLAK', True, now),
            ('DISETUJUI', False, now),
            ('DISETUJUI', True, None),
            ('DISETUJUI', True, now + timedelta(days=1)),
        ):
            with self.subTest(status=review_status, flag=is_published, date=date_published):
                guide = Guide.objects.create(
                    author=self.user_a, title='Belum publik', ringkasan='Ringkasan', konten='Konten',
                    status=review_status, is_published=is_published, date_published=date_published,
                )
                self.assertEqual(self.client.get(f'/api/v1/guides/{guide.pk}/').status_code, 404)
        response = self.client.get('/api/v1/guides/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item['id'] for item in response.json()], [self.published_guide.pk])

    def test_history_is_private_and_scoped_to_owner(self):
        url = '/api/v1/guides/my-submissions/'
        self.assertEqual(self.client.get(url).status_code, 403)
        other_draft = Guide.objects.create(
            author=self.user_b, title='Draf lain', ringkasan='Ringkasan', konten='Konten',
        )
        self.client.force_authenticate(user=self.user_a)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        history = response.json()
        self.assertEqual(history['count'], 2)
        self.assertEqual(history['pending_count'], 1)
        ids = [item['id'] for item in history['results']]
        self.assertEqual(ids, [self.pending_draft_a.pk, self.published_guide.pk])
        self.assertNotIn(other_draft.pk, ids)

    def test_rejection_notes_are_not_exposed_on_published_guides(self):
        # Approval does not clear rejection notes left from an earlier review.
        notes = 'Catatan hanya untuk pengirim'
        Guide.objects.filter(pk=self.published_guide.pk).update(rejected_notes=notes)
        url = f'/api/v1/guides/{self.published_guide.pk}/'
        for endpoint in ('/api/v1/guides/', url):
            with self.subTest(endpoint=endpoint):
                response = self.client.get(endpoint)
                self.assertEqual(response.status_code, 200)
                data = response.json()
                self.assertIsNone((data[0] if isinstance(data, list) else data)['rejected_notes'])

        Guide.objects.filter(pk=self.pending_draft_a.pk).update(status='DITOLAK', rejected_notes=notes)
        self.client.force_authenticate(user=self.user_a)
        response = self.client.get(f'/api/v1/guides/{self.pending_draft_a.pk}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['rejected_notes'], notes)

    def test_only_superuser_has_privileged_detail_read_access(self):
        staff = User.objects.create_user(username='guide-staff', is_staff=True)
        moderator = User.objects.create_superuser(username='guide-moderator')
        Profile.objects.create(user=staff, display_name='Staf')
        url = f'/api/v1/guides/{self.pending_draft_a.pk}/'
        self.client.force_authenticate(user=staff)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.force_authenticate(user=moderator)
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(self.client.get('/api/v1/guides/my-submissions/').status_code, 403)
        Profile.objects.create(user=moderator, display_name='Moderator')
        self.assertEqual(self.client.patch(url, {'title': 'Ubah'}, format='json').status_code, 403)
        self.assertEqual(self.client.delete(url).status_code, 403)
        self.pending_draft_a.refresh_from_db()
        self.assertEqual(self.pending_draft_a.title, 'Draf API Pending A')

    def test_session_login_and_csrf_protect_create(self):
        client = Client(enforce_csrf_checks=True)
        origin = {'HTTP_ORIGIN': 'https://testserver'}
        response = client.get('/accounts/login/', secure=True)
        self.assertEqual(response.status_code, 200)
        response = client.post('/api/v1/accounts/login/', {
            'username': self.user_a.username, 'password': self.password,
        }, content_type='application/json', secure=True,
            HTTP_X_CSRFTOKEN=client.cookies['csrftoken'].value, **origin)
        self.assertEqual(response.status_code, 200)
        self.assertIn('sessionid', client.cookies)

        url = '/api/v1/guides/'
        payload = {'title': 'Draf sesi', 'ringkasan': 'Ringkasan', 'konten': 'Konten'}
        response = client.post(url, payload, content_type='application/json', secure=True, **origin)
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Guide.objects.filter(title='Draf sesi').exists())
        response = client.post(url, payload, content_type='application/json', secure=True,
                               HTTP_X_CSRFTOKEN=client.cookies['csrftoken'].value, **origin)
        self.assertEqual(response.status_code, 201)
        guide = Guide.objects.get(pk=response.json()['id'])
        self.assertEqual(guide.author_id, self.user_a.pk)
        self.assertEqual(guide.status, 'PENDING')

    def test_api_create_guide_requires_authentication_and_sanitizes_xss(self):
        url = reverse('guides_api:list')
        payload = {
            'category': 'PERBAIKAN',
            'title': 'Judul <script>alert(1)</script>Baru',
            'ringkasan': 'Ringkasan <b>aman</b>',
            'konten': 'Isi panduan lengkap.',
            'image_url': 'https://images.unsplash.com/photo-123'
        }

        # Anonim ditolak oleh autentikasi sesi.
        res_anon = self.client.post(url, payload, format='json')
        self.assertEqual(res_anon.status_code, status.HTTP_403_FORBIDDEN)

        # User login berhasil membuat draf berstatus PENDING
        self.client.force_authenticate(user=self.user_a)
        res_auth = self.client.post(url, payload, format='json')
        self.assertEqual(res_auth.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res_auth.data['title'], 'Judul alert(1)Baru')
        self.assertEqual(res_auth.data['status'], 'PENDING')
        self.assertFalse(res_auth.data['is_published'])

    def test_api_detail_visibility_permissions(self):
        # Panduan yang sudah terbit bisa diakses anonim
        pub_url = reverse('guides_api:detail', args=[self.published_guide.id])
        res_pub = self.client.get(pub_url)
        self.assertEqual(res_pub.status_code, status.HTTP_200_OK)
        self.assertIn('<h2 id="cara-mencuci">Cara Mencuci</h2>', res_pub.data['content_html'])

        # Draf yang belum terbit tidak bisa dilihat oleh pengguna lain (404)
        draft_url = reverse('guides_api:detail', args=[self.pending_draft_a.id])
        self.client.force_authenticate(user=self.user_b)
        res_other = self.client.get(draft_url)
        self.assertEqual(res_other.status_code, status.HTTP_404_NOT_FOUND)

        # Pemilik draf bisa melihat draf miliknya sendiri
        self.client.force_authenticate(user=self.user_a)
        res_owner = self.client.get(draft_url)
        self.assertEqual(res_owner.status_code, status.HTTP_200_OK)

    def test_api_update_and_delete_permissions(self):
        draft_url = reverse('guides_api:detail', args=[self.pending_draft_a.id])

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
        pub_url = reverse('guides_api:detail', args=[self.published_guide.id])
        res_locked = self.client.patch(pub_url, {'title': 'Coba Ubah'}, format='json')
        self.assertEqual(res_locked.status_code, status.HTTP_400_BAD_REQUEST)

        # User A menghapus draf miliknya yang masih PENDING -> 204 No Content
        res_del = self.client.delete(draft_url)
        self.assertEqual(res_del.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Guide.objects.filter(id=self.pending_draft_a.id).exists())