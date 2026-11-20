from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from profiles.access import onboarding_url
from profiles.models import Profile
from sustainableguides.models import Guide


class GuideOnboardingTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="guide-author")
        self.guide = Guide.objects.create(
            author=self.user, category="PERAWATAN", title="Draf awal",
            ringkasan="Ringkasan awal", konten="Konten awal", status="PENDING",
        )
        self.urls = [
            reverse("sustainableguides:my_submissions"),
            reverse("sustainableguides:submit_draft"),
            reverse("sustainableguides:edit_draft", args=[self.guide.pk]),
            reverse("sustainableguides:delete_draft", args=[self.guide.pk]),
        ]
        self.data = {
            "category": "REUSE", "title": "Draf baru",
            "ringkasan": "Ringkasan baru", "konten": "Konten baru",
            "image_url": "",
        }

    def assert_management_blocked(self):
        for url in self.urls:
            for method in ("get", "post"):
                with self.subTest(url=url, method=method):
                    response = getattr(self.client, method)(url, self.data if method == "post" else {})
                    self.assertRedirects(response, onboarding_url(url), fetch_redirect_response=False)
        self.assertEqual(Guide.objects.count(), 1)
        self.guide.refresh_from_db()
        self.assertEqual(self.guide.title, "Draf awal")

    def test_account_without_profile_cannot_manage_guides(self):
        self.client.force_login(self.user)
        self.assert_management_blocked()

    def test_blank_display_name_cannot_manage_guides(self):
        Profile.objects.create(user=self.user, display_name="   ")
        self.client.force_login(self.user)
        self.assert_management_blocked()

    def test_profile_deletion_revokes_guide_management_access(self):
        profile = Profile.objects.create(user=self.user, display_name="Penulis")
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(self.urls[0]).status_code, 200)
        profile.delete()
        self.assert_management_blocked()

    def test_guest_is_redirected_to_login(self):
        for url in self.urls:
            for method in ("get", "post"):
                with self.subTest(url=url, method=method):
                    response = getattr(self.client, method)(url)
                    self.assertRedirects(
                        response, reverse("accounts:login") + "?next=" + url,
                        fetch_redirect_response=False,
                    )

    def test_incomplete_account_can_still_read_public_guides(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("sustainableguides:list")).status_code, 200)
