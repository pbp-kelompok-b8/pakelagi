from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import Guide
from .forms import GuideForm
from profiles.models import Profile

User = get_user_model()

# Create your tests here.

class GuideFormAndSecurityTests(TestCase):
    """Menguji validasi form dan sanitasi input terhadap serangan XSS."""

    def test_valid_guide_form(self):
        form = GuideForm(data={
            'category': 'PERAWATAN',
            'title': 'Merawat Kain Linen',
            'ringkasan': 'Panduan singkat mencuci linen.',
            'konten': '## Langkah 1\nCuci dengan air dingin.',
            'image_url': 'https://images.unsplash.com/photo-123'
        })
        self.assertTrue(form.is_valid())

    def test_xss_strip_tags_removes_malicious_html(self):
        """Memastikan tag <script> dibersihkan tetapi teks di luarnya tetap tersimpan."""
        form = GuideForm(data={
            'category': 'PERAWATAN',
            'title': 'Judul <script>alert(1)</script>Bersih',
            'ringkasan': 'Ringkasan <b>tebal</b> <script>evil()</script>',
            'konten': 'Isi <iframe src="evil.com"></iframe> panduan',
            'image_url': ''
        })
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['title'], 'Judul alert(1)Bersih')
        self.assertEqual(form.cleaned_data['ringkasan'], 'Ringkasan tebal evil()')
        self.assertNotIn('<script>', form.cleaned_data['title'])
        self.assertNotIn('<iframe', form.cleaned_data['konten'])

    def test_xss_html_only_payload_rejected(self):
        """Payload yang hanya berisi tag HTML (seperti <img onerror=...>) harus ditolak."""
        form = GuideForm(data={
            'category': 'PERAWATAN',
            'title': '<img src="x" onerror="alert(\'XSS!\')">',
            'ringkasan': '<script></script>',
            'konten': '<svg onload="alert(1)"></svg>',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('title', form.errors)
        self.assertIn('ringkasan', form.errors)
        self.assertIn('konten', form.errors)

    def test_image_url_rejects_javascript_and_http_schemes(self):
        """Memastikan URL gambar menolak javascript: atau http:// biasa."""
        form_js = GuideForm(data={
            'category': 'PERAWATAN',
            'title': 'Tes URL',
            'ringkasan': 'Ringkasan',
            'konten': 'Isi konten',
            'image_url': 'javascript:alert(1)'
        })
        self.assertFalse(form_js.is_valid())
        self.assertIn('image_url', form_js.errors)

        form_http = GuideForm(data={
            'category': 'PERAWATAN',
            'title': 'Tes URL HTTP',
            'ringkasan': 'Ringkasan',
            'konten': 'Isi konten',
            'image_url': 'http://insecure-website.com/img.jpg'
        })
        self.assertFalse(form_http.is_valid())
        self.assertIn('image_url', form_http.errors)


class GuidePublicViewsTests(TestCase):
    """Menguji halaman publik (daftar panduan, filter kategori, detail, dan keamanan render Markdown)."""

    def setUp(self):
        self.user = User.objects.create_user(username='penulis', password='password123')
        
        self.published_guide = Guide.objects.create(
            author=self.user,
            category='PERAWATAN',
            title='Panduan Terbit',
            ringkasan='Ringkasan terbit',
            konten='## Subjudul\nIsi panduan terbit.',
            status='DISETUJUI',
            is_published=True,
            date_published=timezone.now()
        )
        self.unpublished_approved_guide = Guide.objects.create(
            author=self.user,
            category='REUSE',
            title='Panduan Disetujui Belum Terbit',
            ringkasan='Ringkasan',
            konten='Isi panduan.',
            status='DISETUJUI',
            is_published=False
        )
        self.pending_guide = Guide.objects.create(
            author=self.user,
            category='PERBAIKAN',
            title='Panduan Pending',
            ringkasan='Ringkasan',
            konten='Isi panduan.',
            status='PENDING',
            is_published=False
        )

    def test_guide_list_only_shows_published_guides(self):
        response = self.client.get(reverse('sustainableguides:list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Panduan Terbit')
        self.assertNotContains(response, 'Panduan Disetujui Belum Terbit')
        self.assertNotContains(response, 'Panduan Pending')

    def test_guide_list_category_filter(self):
        response = self.client.get(reverse('sustainableguides:list') + '?category=PERAWATAN')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Panduan Terbit')

        response_empty = self.client.get(reverse('sustainableguides:list') + '?category=REUSE')
        self.assertEqual(response_empty.status_code, 200)
        self.assertNotContains(response_empty, 'Panduan Terbit')

    def test_guide_detail_accessible_only_if_published(self):
        # Artikel yang sudah terbit -> 200 OK
        res_ok = self.client.get(reverse('sustainableguides:detail', args=[self.published_guide.id]))
        self.assertEqual(res_ok.status_code, 200)
        self.assertContains(res_ok, 'Panduan Terbit')

        # Artikel yang disetujui tapi belum terbit -> 404 Not Found
        res_unpub = self.client.get(reverse('sustainableguides:detail', args=[self.unpublished_approved_guide.id]))
        self.assertEqual(res_unpub.status_code, 404)

        # Artikel yang masih pending -> 404 Not Found
        res_pending = self.client.get(reverse('sustainableguides:detail', args=[self.pending_guide.id]))
        self.assertEqual(res_pending.status_code, 404)

    def test_guide_detail_escapes_stored_xss_in_markdown(self):
        """Jika database telanjur menyimpan script berbahaya, guide_detail wajib meng-escape-nya."""
        malicious_guide = Guide.objects.create(
            author=self.user,
            category='PERAWATAN',
            title='Artikel XSS',
            ringkasan='Ringkasan',
            konten='<script>alert("XSS")</script>\n[Klik](javascript:alert(1))',
            status='DISETUJUI',
            is_published=True,
            date_published=timezone.now()
        )
        response = self.client.get(reverse('sustainableguides:detail', args=[malicious_guide.id]))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, '<script>alert("XSS")</script>')
        self.assertContains(response, '&lt;script&gt;')
        self.assertNotContains(response, 'href="javascript:alert(1)"')

    def test_markdown_links_from_valid_form_are_sanitized_in_detail(self):
        form = GuideForm(data={
            'category': 'PERAWATAN',
            'title': 'Tautan berbahaya',
            'ringkasan': 'Ringkasan',
            'konten': '[Klik](JaVaScRiPt:alert(1))',
        })
        self.assertTrue(form.is_valid(), form.errors)
        guide = form.save(commit=False)
        guide.author = self.user
        guide.status = 'DISETUJUI'
        guide.is_published = True
        guide.date_published = timezone.now()
        guide.save()

        response = self.client.get(reverse('sustainableguides:detail', args=[guide.id]))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('href="javascript:', response.context['content_html'].lower())


class GuideMemberCRUDAndAuthTests(TestCase):
    """Menguji CRUD draf oleh member serta otorisasi kepemilikan dan status draf."""

    def setUp(self):
        self.user_a = User.objects.create_user(username='usera', password='password123')
        self.user_b = User.objects.create_user(username='userb', password='password123')
        Profile.objects.create(user=self.user_a, display_name='User A')
        Profile.objects.create(user=self.user_b, display_name='User B')

        self.draft_a = Guide.objects.create(
            author=self.user_a,
            category='PERAWATAN',
            title='Draf Milik A',
            ringkasan='Ringkasan A',
            konten='Konten A',
            status='PENDING'
        )
        self.approved_a = Guide.objects.create(
            author=self.user_a,
            category='PERAWATAN',
            title='Draf A Sudah Disetujui',
            ringkasan='Ringkasan',
            konten='Konten',
            status='DISETUJUI'
        )

    def test_anonymous_user_redirected_from_member_pages(self):
        res_drafts = self.client.get(reverse('sustainableguides:my_submissions'))
        self.assertEqual(res_drafts.status_code, 302)

        res_edit = self.client.get(reverse('sustainableguides:edit_draft', args=[self.draft_a.id]))
        self.assertEqual(res_edit.status_code, 302)

    def test_user_only_sees_own_drafts(self):
        self.client.login(username='userb', password='password123')
        response = self.client.get(reverse('sustainableguides:my_submissions'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Draf Milik A')

    def test_submit_draft_creates_pending_guide(self):
        self.client.login(username='usera', password='password123')
        response = self.client.post(reverse('sustainableguides:submit_draft'), {
            'category': 'REUSE',
            'title': 'Draf Baru Dikirim',
            'ringkasan': 'Ringkasan baru',
            'konten': 'Isi panduan baru',
            'image_url': ''
        })
        self.assertEqual(response.status_code, 200)
        new_guide = Guide.objects.get(title='Draf Baru Dikirim')
        self.assertEqual(new_guide.author, self.user_a)
        self.assertEqual(new_guide.status, 'PENDING')
        self.assertFalse(new_guide.is_published)

    def test_edit_draft_success_for_owner_when_pending(self):
        self.client.login(username='usera', password='password123')
        response = self.client.post(reverse('sustainableguides:edit_draft', args=[self.draft_a.id]), {
            'category': 'PERBAIKAN',
            'title': 'Draf Milik A Diperbarui',
            'ringkasan': 'Ringkasan baru',
            'konten': 'Konten baru',
            'image_url': ''
        })
        self.assertEqual(response.status_code, 302)
        self.draft_a.refresh_from_db()
        self.assertEqual(self.draft_a.title, 'Draf Milik A Diperbarui')

    def test_cannot_edit_other_users_draft(self):
        """User B tidak boleh mengedit draf milik User A (harus 404)."""
        self.client.login(username='userb', password='password123')
        response = self.client.post(reverse('sustainableguides:edit_draft', args=[self.draft_a.id]), {
            'category': 'PERBAIKAN',
            'title': 'Dibajak User B',
            'ringkasan': 'Ringkasan',
            'konten': 'Konten',
        })
        self.assertEqual(response.status_code, 404)

    def test_cannot_edit_non_pending_draft(self):
        """Draf yang sudah DISETUJUI atau DITOLAK tidak boleh diedit lagi."""
        self.client.login(username='usera', password='password123')
        response = self.client.post(reverse('sustainableguides:edit_draft', args=[self.approved_a.id]), {
            'category': 'PERBAIKAN',
            'title': 'Coba Ubah Saat Sudah Disetujui',
            'ringkasan': 'Ringkasan',
            'konten': 'Konten',
        })
        self.approved_a.refresh_from_db()
        self.assertNotEqual(self.approved_a.title, 'Coba Ubah Saat Sudah Disetujui')

    def test_delete_draft_permissions_and_status_lock(self):
        # User B mencoba hapus draf User A -> 404
        self.client.login(username='userb', password='password123')
        res_other = self.client.post(reverse('sustainableguides:delete_draft', args=[self.draft_a.id]))
        self.assertEqual(res_other.status_code, 404)
        self.assertTrue(Guide.objects.filter(id=self.draft_a.id).exists())

        # User A mencoba hapus draf miliknya yang sudah DISETUJUI -> Ditolak (tidak terhapus)
        self.client.login(username='usera', password='password123')
        self.client.post(reverse('sustainableguides:delete_draft', args=[self.approved_a.id]))
        self.assertTrue(Guide.objects.filter(id=self.approved_a.id).exists())

        # User A menghapus draf miliknya yang masih PENDING -> Berhasil terhapus
        self.client.post(reverse('sustainableguides:delete_draft', args=[self.draft_a.id]))
        self.assertFalse(Guide.objects.filter(id=self.draft_a.id).exists())
