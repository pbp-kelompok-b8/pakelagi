from django.contrib.auth import SESSION_KEY
from django.contrib.auth.models import User
from unittest.mock import patch
from datetime import timedelta

from django.db import DatabaseError
from django.test import Client, TestCase, override_settings
from django.utils import timezone
from django.urls import reverse

from accounts.testing import PASSWORD
from profiles.models import Profile


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class AccountDeletionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="pemilik", password=PASSWORD)
        self.url = "/accounts/delete/"
        self.client.force_login(self.user)

    def test_confirmation_requires_login_and_get_does_not_delete(self):
        response = self.client.get(self.url)
        self.assertContains(response, "Penghapusan ini permanen dan tidak dapat dibatalkan.")
        self.assertContains(response, 'type="password"')
        self.assertEqual(self.client.session[SESSION_KEY], str(self.user.pk))
        self.client.logout()
        self.assertRedirects(self.client.get(self.url), reverse("accounts:login") + "?next=" + self.url)

    def test_invalid_confirmation_keeps_account_and_session(self):
        for payload in (
            {"username": "someone-else", "password": PASSWORD},
            {"username": self.user.username, "password": "wrong-secret"},
            {},
        ):
            response = self.client.post(self.url, payload)
            self.assertContains(response, "Konfirmasi gagal. Periksa username dan password saat ini.")
            self.assertNotContains(response, 'value="wrong-secret"')
            self.assertEqual(self.client.session[SESSION_KEY], str(self.user.pk))
        other = Client()
        self.assertTrue(other.login(username=self.user.username, password=PASSWORD))

    def test_success_deletes_only_current_account_and_revokes_all_its_sessions(self):
        Profile.objects.create(user=self.user, display_name="Pemilik")
        other_device = Client()
        other_device.force_login(self.user)
        another_user = User.objects.create_user(username="tetangga", password=PASSWORD)
        unrelated_device = Client()
        unrelated_device.force_login(another_user)
        response = self.client.post(self.url, {
            "username": self.user.username, "password": PASSWORD, "user_id": another_user.pk,
        }, follow=True)
        self.assertRedirects(response, reverse("main:show_main"))
        self.assertContains(response, "Akun berhasil dihapus.")
        self.assertNotIn(SESSION_KEY, self.client.session)
        self.assertNotIn(SESSION_KEY, other_device.session)
        self.assertEqual(unrelated_device.session[SESSION_KEY], str(another_user.pk))
        self.assertFalse(Client().login(username=self.user.username, password=PASSWORD))
        self.assertEqual(self.client.get(reverse("profiles:profile_public", args=[self.user.pk])).status_code, 404)
        from accounts.testing import registration_data
        response = self.client.post(reverse("accounts:register"), registration_data(username=self.user.username))
        self.assertRedirects(response, reverse("profiles:profile_create"))
        self.assertNotEqual(self.client.session[SESSION_KEY], str(self.user.pk))

    def test_account_without_profile_can_be_deleted(self):
        response = self.client.post(self.url, {"username": self.user.username, "password": PASSWORD})
        self.assertRedirects(response, reverse("main:show_main"))
        self.assertFalse(Client().login(username=self.user.username, password=PASSWORD))

    def test_five_failures_block_confirmation_across_sessions_for_fifteen_minutes(self):
        for _ in range(5):
            self.client.post(self.url, {"username": self.user.username, "password": "wrong"})
        another_device = Client()
        another_device.force_login(self.user)
        payload = {"username": self.user.username, "password": PASSWORD}
        self.assertEqual(another_device.post(self.url, payload).status_code, 429)
        self.assertTrue(Client().login(username=self.user.username, password=PASSWORD))
        with patch("accounts.services.timezone.now", return_value=timezone.now() + timedelta(minutes=16)):
            self.assertRedirects(another_device.post(self.url, payload), reverse("main:show_main"))

    @override_settings(DEBUG=False)
    def test_unexpected_exception_report_redacts_credentials(self):
        from django.views.debug import ExceptionReporter

        secret = "distinctive-password-never-in-reports"
        self.user.set_password(secret)
        self.user.save()
        client = Client(raise_request_exception=False)
        client.force_login(self.user)

        def fail_delete(instance):
            raise RuntimeError("unexpected failure")

        with patch.object(User, "delete", fail_delete):
            response = client.post(self.url, {"username": self.user.username, "password": secret})
        self.assertEqual(response.status_code, 500)
        report = ExceptionReporter(response.wsgi_request, *response.exc_info).get_traceback_text()
        self.assertNotIn(secret, report)

    def test_empty_submissions_are_throttled_and_window_reset_persists(self):
        for _ in range(5):
            self.client.post(self.url, {})
        self.assertEqual(self.client.post(self.url, {}).status_code, 429)
        with patch("accounts.services.timezone.now", return_value=timezone.now() + timedelta(minutes=16)):
            for _ in range(5):
                self.assertEqual(self.client.post(self.url, {}).status_code, 200)
            self.assertEqual(self.client.post(self.url, {}).status_code, 429)

    def test_old_session_replay_cannot_delete_replacement_username(self):
        stale_device = Client()
        stale_device.force_login(self.user)
        payload = {"username": self.user.username, "password": PASSWORD}
        self.client.post(self.url, payload)
        replacement = User.objects.create_user(username=self.user.username, password=PASSWORD)
        response = stale_device.post(self.url, payload)
        self.assertRedirects(response, reverse("accounts:login") + "?next=" + self.url)
        self.assertTrue(Client().login(username=replacement.username, password=PASSWORD))

    def test_failure_rolls_back_profile_and_all_sessions(self):
        Profile.objects.create(user=self.user, display_name="Masih ada")
        other_device = Client()
        other_device.force_login(self.user)
        original_delete = User.delete

        def fail_after_delete(instance, *args, **kwargs):
            original_delete(instance, *args, **kwargs)
            raise DatabaseError("private database details")

        with patch.object(User, "delete", fail_after_delete):
            response = self.client.post(self.url, {"username": self.user.username, "password": PASSWORD})
        self.assertContains(response, "Penghapusan gagal. Akun tetap tersedia.")
        self.assertNotContains(response, "private database details")
        self.assertEqual(self.client.session[SESSION_KEY], str(self.user.pk))
        self.assertEqual(other_device.session[SESSION_KEY], str(self.user.pk))
        self.assertContains(self.client.get(reverse("profiles:profile_public", args=[self.user.pk])), "Masih ada")
        self.assertTrue(Client().login(username=self.user.username, password=PASSWORD))

    def test_csrf_is_required_and_valid_token_can_delete(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        payload = {"username": self.user.username, "password": PASSWORD}
        self.assertEqual(client.post(self.url, payload).status_code, 403)
        client.get(self.url)
        payload["csrfmiddlewaretoken"] = client.cookies["csrftoken"].value
        self.assertRedirects(client.post(self.url, payload), reverse("main:show_main"))

    def test_entry_link_is_available_on_onboarding_and_edit_but_not_for_staff(self):
        self.assertContains(self.client.get(reverse("profiles:profile_create")), 'href="/accounts/delete/"')
        Profile.objects.create(user=self.user, display_name="Pemilik")
        self.assertContains(self.client.get(reverse("profiles:profile_edit")), 'href="/accounts/delete/"')
        self.user.is_staff = True
        self.user.save()
        self.assertNotContains(self.client.get(reverse("profiles:profile_edit")), 'href="/accounts/delete/"')

    def test_privileged_accounts_cannot_use_self_deletion(self):
        for flag in ("is_staff", "is_superuser"):
            with self.subTest(flag=flag):
                setattr(self.user, flag, True)
                self.user.save()
                for method in (self.client.get, self.client.post):
                    self.assertEqual(method(self.url).status_code, 403)
                setattr(self.user, flag, False)
                self.user.save()
