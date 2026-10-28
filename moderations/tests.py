from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from sustainableguides.models import Guide

User = get_user_model()
# Create your tests here.

class ModerationAuthorizationTests(TestCase):
    # Memastikan hanya admin/superuser yang dapat mengakses dan mengeksekusi fitur moderasi.
    def setUp(self):
        self.member = User.objects.create_user(username='Ichika39', password='MikuFan123')
        self.admin = User.objects.create_superuser(username='Miku39', email='hatsune.miku@sekai.com', password='World1sM1ne')
        self.guide = Guide.objects.create(
            author=self.member,
            category='PERAWATAN',
            title='Draf Uji Otorisasi',
            ringkasan='Ringkasan',
            konten='Konten',
            status='PENDING'
        )
    
    def testAnonimusdanmemberblockdarimoderation(self):
        # Pengunjung belum login -> Redirect ke halaman login
        res_anon = self.client.get(reverse('moderations:jurnal_list'))
        self.assertEqual(res_anon.status_code, 302)
        
        # Member di redirect/tolak
        self.client.login(username='Ichika39', password='MikuFan123')
        res_member_get = self.client.get(reverse('moderations:jurnal_list'))
        self.assertEqual(res_member_get.status_code, 302)
        
        res_member_post = self.client.post(reverse('moderations:jurnal_review', args=[self.guide.id]), {
            'action': 'approve'
        })
        self.assertEqual(res_member_post.status_code, 302)
        self.guide.refresh_from_db()
        self.assertEqual(self.guide.status, 'PENDING')
    
    def testAdminCanAccessModeration(self):
        self.client.login(username='Miku39', password='World1sM1ne')
        response = self.client.get(reverse('moderations:jurnal_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Draf Uji Otorisasi')
    
class ModerationWorkflowAndSecurityTests(TestCase):
    # Menguji alur kerja moderasi (Approve, Direct Publish, Reject, Toggle Switch, Delete, & XSS).
     
    def setUp(self):
        self.member = User.objects.create_user(username='Ichika39', password='MikuFan123')
        self.admin = User.objects.create_superuser(username='Miku39', email='hatsune.miku@sekai.com', password='World1sM1ne')
        self.client.login(username='Miku39', password='World1sM1ne')
        
        self.pending_guide = Guide.objects.create(
            author=self.member,
            category='PERAWATAN',
            title='Draf Menunggu Tinjauan',
            ringkasan='Ringkasan pending',
            konten='Isi konten pending',
            status='PENDING',
            is_published=False
        )
        self.waiting_publish_guide = Guide.objects.create(
            author=self.member,
            category='REUSE',
            title='Draf Disetujui Menunggu Terbit',
            ringkasan='Ringkasan waiting',
            konten='Isi konten waiting',
            status='DISETUJUI',
            is_published=False
        )
    
    def testPendingTabShowBothPendingandWaitingList(self):
        # Tab Pending menunjukan daftar draft pendinf dan approved but not published
        response = self.client.get(reverse('moderations:jurnal_list') + '?tab=pending')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Draf Menunggu Tinjauan')
        self.assertContains(response, 'Draf Disetujui Menunggu Terbit')
        self.assertIn('waiting_publish_guides', response.context)
        
    def testApproveDraftWithoutDirectPublish(self):
        # Approve draf switch off masuk ke status disetujui tapi is_published=false
        response = self.client.post(reverse('moderations:jurnal_review', args=[self.pending_guide.id]), {
            'action': 'approve',
            'direct_publish': 'false',
            'rejected_notes': ''
        })
        self.assertEqual(response.status_code, 302)
        self.pending_guide.refresh_from_db()
        self.assertEqual(self.pending_guide.status, 'DISETUJUI')
        self.assertFalse(self.pending_guide.is_published)
        
    def testApproveDraftWithDirectPublish(self):
        # Approve draf switch on masuk ke status disetujui dan is_published=true
        response = self.client.post(reverse('moderations:jurnal_review', args=[self.pending_guide.id]), {
            'action': 'approve',
            'direct_publish': 'true',
            'rejected_notes': ''
        })
        self.assertEqual(response.status_code, 302)
        self.pending_guide.refresh_from_db()
        self.assertEqual(self.pending_guide.status, 'DISETUJUI')
        self.assertTrue(self.pending_guide.is_published)
        self.assertIsNotNone(self.pending_guide.date_published)
        
    def testRejectDraftRequiresNOtesandStripsXSS(self):
        # Reject kalau gaada notes, dan draf tetap pending
        self.client.post(reverse('moderations:jurnal_review', args=[self.pending_guide.id]), {
            'action': 'reject',
            'rejected_notes': '   '
        })
        self.pending_guide.refresh_from_db()
        self.assertEqual(self.pending_guide.status, 'PENDING')
        
        # Reject tapi ada script xss, success dan tag html dibersihkan
        self.client.post(reverse('moderations:jurnal_review', args=[self.pending_guide.id]), {
            'action': 'reject',
            'rejected_notes': 'Kurang lengkap <script>alert("XSS")</script> silakan revisi.'
        })
        self.pending_guide.refresh_from_db()
        self.assertEqual(self.pending_guide.status, 'DITOLAK')
        self.assertFalse(self.pending_guide.is_published)
        self.assertNotIn('<script>', self.pending_guide.rejected_notes)
        self.assertIn('Kurang lengkap', self.pending_guide.rejected_notes)
    
    def testTogglePublishActionSwitchesState(self):
        # Menguji saklar HTMX untuk menerbitkan dan menarik kembali panduan yang sudah DISETUJUI.
        # Klik pertama: False -> True
        self.client.post(reverse('moderations:jurnal_toggle_publish', args=[self.waiting_publish_guide.id]))
        self.waiting_publish_guide.refresh_from_db()
        self.assertTrue(self.waiting_publish_guide.is_published)
        self.assertIsNotNone(self.waiting_publish_guide.date_published)

        # Klik kedua: True -> False (ditarik kembali dari publik)
        self.client.post(reverse('moderations:jurnal_toggle_publish', args=[self.waiting_publish_guide.id]))
        self.waiting_publish_guide.refresh_from_db()
        self.assertFalse(self.waiting_publish_guide.is_published)
        
    def testTogglePublishIgnoredbyPendingGuide(self):
        # untuk pending guide toggle switch publish di ignore
        self.client.post(reverse('moderations:jurnal_toggle_publish', args=[self.pending_guide.id]))
        self.pending_guide.refresh_from_db()
        self.assertFalse(self.pending_guide.is_published)
        
    def testModerationPreviewEscapesStoredXSSInMarkdown(self):
        # Memastikan panel preview admin aman dari XSS meskipun draf mengandung tag <script>.
        xss_guide = Guide.objects.create(
            author=self.member,
            category='PERAWATAN',
            title='Draf Berbahaya',
            ringkasan='Ringkasan',
            konten='<img src="x" onerror="alert(1)">\n[Link](javascript:evil())',
            status='PENDING'
        )
        url = reverse('moderations:jurnal_list') + f'?tab=pending&id={xss_guide.id}'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, '<img src="x" onerror="alert(1)">')
        self.assertContains(response, '&lt;img src=&quot;x&quot; onerror=&quot;alert(1)&quot;&gt;')
    
    def testAdminDelete(self):
        self.client.post(reverse('moderations:jurnal_delete', args=[self.pending_guide.id]))
        self.assertFalse(Guide.objects.filter(id=self.pending_guide.id).exists())
