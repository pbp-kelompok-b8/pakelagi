from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Guide


class GuidePublicationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.member = get_user_model().objects.create_user(username='publication-author')
        cls.admin = get_user_model().objects.create_superuser(
            username='publication-admin', email='publication@example.com'
        )

    def setUp(self):
        self.now = timezone.now()
        self.future = self.now + timedelta(days=7)
        self.guide = Guide.objects.create(
            author=self.member,
            category='PERAWATAN',
            title='Panduan terjadwal',
            ringkasan='Ringkasan',
            konten='Isi panduan',
            status='DISETUJUI',
        )
        self.publish_url = reverse('moderations:jurnal_publish', args=[self.guide.id])
        self.detail_url = reverse('sustainableguides:detail', args=[self.guide.id])

    def schedule(self):
        self.client.force_login(self.admin)
        with patch('sustainableguides.models.timezone.now', return_value=self.now):
            response = self.client.post(self.publish_url, {
                'publish_type': 'schedule',
                'schedule_date': self.future.isoformat(),
            })
        self.assertEqual(response.status_code, 302)
        self.guide.refresh_from_db()
        self.client.logout()

    def assert_public_visibility(self, visible):
        listing = self.client.get(reverse('sustainableguides:list'))
        self.assertEqual(self.guide in listing.context['guides'], visible)
        self.assertEqual(listing.context['featured_guide'] == self.guide, visible)
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200 if visible else 404)

    def test_schedule_is_hidden_until_publication_time_then_appears_automatically(self):
        self.schedule()
        self.assertTrue(self.guide.is_published)
        self.assertTrue(timezone.is_aware(self.guide.date_published))
        self.assertEqual(self.guide.date_published, self.future)
        with patch('sustainableguides.models.timezone.now', return_value=self.now):
            self.assert_public_visibility(False)
        with patch('sustainableguides.models.timezone.now', return_value=self.future):
            self.assert_public_visibility(True)

    def test_future_guide_is_not_recommended_before_publication(self):
        self.schedule()
        published = Guide.objects.create(
            author=self.member, title='Sudah terbit', ringkasan='Ringkasan',
            konten='Konten', status='DISETUJUI', is_published=True,
            date_published=self.now - timedelta(days=1),
        )
        url = reverse('sustainableguides:detail', args=[published.id])
        with patch('sustainableguides.models.timezone.now', return_value=self.now):
            response = self.client.get(url)
            self.assertNotIn(self.guide, response.context['other_guides'])
        with patch('sustainableguides.models.timezone.now', return_value=self.future):
            response = self.client.get(url)
            self.assertIn(self.guide, response.context['other_guides'])

    def test_future_guide_stays_in_waiting_queue_not_published_tab(self):
        self.schedule()
        self.client.force_login(self.admin)
        with patch('sustainableguides.models.timezone.now', return_value=self.now):
            response = self.client.get(reverse('moderations:jurnal_list'), {'tab': 'pending'})
            self.assertIn(self.guide, response.context['waiting_publish_guides'])
            self.assertEqual(response.context['count_published'], 0)
            response = self.client.get(reverse('moderations:jurnal_list'), {'tab': 'published'})
            self.assertNotIn(self.guide, response.context['guides'])
        with patch('sustainableguides.models.timezone.now', return_value=self.future):
            response = self.client.get(reverse('moderations:jurnal_list'), {'tab': 'published'})
            self.assertIn(self.guide, response.context['guides'])
            self.assertEqual(response.context['count_published'], 1)

    def test_author_sees_schedule_without_a_premature_public_link(self):
        self.schedule()
        self.client.force_login(self.member)
        with patch('sustainableguides.models.timezone.now', return_value=self.now):
            response = self.client.get(reverse('sustainableguides:my_submissions'))
            self.assertContains(response, 'Dijadwalkan terbit')
            self.assertNotContains(response, f'href="{self.detail_url}"')
        with patch('sustainableguides.models.timezone.now', return_value=self.future):
            response = self.client.get(reverse('sustainableguides:my_submissions'))
            self.assertContains(response, f'href="{self.detail_url}"')

    def test_missing_invalid_and_past_dates_do_not_change_publication_state(self):
        self.client.force_login(self.admin)
        for value in ('', 'invalid', '2026-02-30T10:00', (self.now - timedelta(days=1)).isoformat()):
            with self.subTest(value=value):
                response = self.client.post(self.publish_url, {
                    'publish_type': 'schedule', 'schedule_date': value,
                })
                self.assertEqual(response.status_code, 302)
                self.guide.refresh_from_db()
                self.assertFalse(self.guide.is_published)
                self.assertIsNone(self.guide.date_published)

    def test_datetime_local_input_is_saved_with_timezone(self):
        self.client.force_login(self.admin)
        response = self.client.post(self.publish_url, {
            'publish_type': 'schedule',
            'schedule_date': timezone.localtime(self.future).strftime('%Y-%m-%dT%H:%M'),
        })
        self.assertEqual(response.status_code, 302)
        self.guide.refresh_from_db()
        self.assertTrue(timezone.is_aware(self.guide.date_published))
        self.assertEqual(self.guide.date_published, self.future.replace(second=0, microsecond=0))

    def test_publish_now_overrides_future_schedule(self):
        self.schedule()
        self.client.force_login(self.admin)
        with patch('sustainableguides.models.timezone.now', return_value=self.now):
            self.client.post(self.publish_url, {'publish_type': 'now'})
        self.guide.refresh_from_db()
        self.assertEqual(self.guide.date_published, self.now)
        self.client.logout()
        self.assert_public_visibility(True)

    def test_cancel_schedule_and_toggle_on_publishes_immediately(self):
        self.schedule()
        self.client.force_login(self.admin)
        url = reverse('moderations:jurnal_toggle_publish', args=[self.guide.id])
        self.client.post(url)
        self.guide.refresh_from_db()
        self.assertFalse(self.guide.is_published)
        with patch('sustainableguides.models.timezone.now', return_value=self.now):
            self.client.post(url)
        self.guide.refresh_from_db()
        self.assertEqual(self.guide.date_published, self.now)
        self.client.logout()
        self.assert_public_visibility(True)

    def test_publish_endpoint_rejects_unapproved_guides(self):
        self.client.force_login(self.admin)
        for status in ('PENDING', 'DITOLAK'):
            for publish_type in ('now', 'schedule'):
                with self.subTest(status=status, publish_type=publish_type):
                    self.guide.status = status
                    self.guide.save()
                    self.client.post(self.publish_url, {
                        'publish_type': publish_type, 'schedule_date': self.future.isoformat(),
                    })
                    self.guide.refresh_from_db()
                    self.assertFalse(self.guide.is_published)
                    self.assertIsNone(self.guide.date_published)

    def test_publication_actions_require_admin(self):
        for user in (None, self.member):
            for action in ('jurnal_publish', 'jurnal_toggle_publish'):
                with self.subTest(user=user, action=action):
                    if user:
                        self.client.force_login(user)
                    else:
                        self.client.logout()
                    response = self.client.post(reverse(f'moderations:{action}', args=[self.guide.id]), {
                        'publish_type': 'schedule', 'schedule_date': self.future.isoformat(),
                    })
                    self.assertEqual(response.status_code, 302)
                    self.guide.refresh_from_db()
                    self.assertFalse(self.guide.is_published)

    def test_missing_publication_date_does_not_expose_guide(self):
        self.guide.is_published = True
        self.guide.save()
        self.assert_public_visibility(False)
