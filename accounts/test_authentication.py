from django.contrib.auth import SESSION_KEY
from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from profiles.models import Profile
from accounts.testing import PASSWORD, registration_data


class LoginLogoutTests(TestCase):
    """Spesifikasi 5.2, 6, dan 10: sesi, pesan generik, redirect aman."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            "nina.arum", email="private@example.com", password=PASSWORD
        )
        Profile.objects.create(user=cls.user, display_name="Nina")

    def setUp(self):
        self.login_url = reverse("accounts:login")
        self.logout_url = reverse("accounts:logout")
        self.credentials = {"username": self.user.username, "password": PASSWORD}

    def test_guest_can_open_login_form(self):
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/login.html")
        self.assertTemplateUsed(response, "base.html")
        self.assertContains(response, 'name="csrfmiddlewaretoken"')

    def test_valid_credentials_start_session_and_redirect_home(self):
        response = self.client.post(self.login_url, self.credentials)
        self.assertRedirects(response, reverse("main:show_main"))
        self.assertEqual(self.client.session[SESSION_KEY], str(self.user.pk))

    def test_unknown_username_and_wrong_password_have_identical_errors(self):
        errors = []
        for username in (self.user.username, "unknown-user"):
            with self.subTest(username=username):
                response = self.client.post(
                    self.login_url, {"username": username, "password": "wrong"}
                )
                self.assertEqual(response.status_code, 200)
                errors.append(list(response.context["form"].non_field_errors()))
                self.assertContains(response, "Username atau kata sandi salah.")
                self.assertNotContains(response, "Username tidak terdaftar")
                self.assertNotContains(response, "Password salah")
                self.assertNotIn(SESSION_KEY, self.client.session)
        self.assertEqual(errors[0], ["Username atau kata sandi salah."])
        self.assertEqual(errors[0], errors[1])

    def test_inactive_account_cannot_login(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])
        response = self.client.post(self.login_url, self.credentials)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            list(response.context["form"].non_field_errors()),
            ["Username atau kata sandi salah."],
        )
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_missing_login_credentials_are_rejected(self):
        for field in ("username", "password"):
            with self.subTest(field=field):
                response = self.client.post(
                    self.login_url, {**self.credentials, field: ""}
                )
                self.assertEqual(response.status_code, 200)
                self.assertIn(field, response.context["form"].errors)
                self.assertNotIn(SESSION_KEY, self.client.session)

    def test_safe_next_is_preserved_in_form_and_used_after_login(self):
        target = reverse("main:show_main") + "?source=login"
        response = self.client.get(self.login_url, {"next": target})
        self.assertEqual(response.context["next"], target)
        self.assertContains(response, f'name="next" value="{target}"')
        response = self.client.post(
            self.login_url, {**self.credentials, "next": target}
        )
        self.assertRedirects(response, target)

    def test_unsafe_next_redirects_home_instead(self):
        for target in (
            "https://evil.example/", "//evil.example/", "javascript:alert(1)",
        ):
            with self.subTest(target=target):
                self.client.logout()
                response = self.client.post(
                    self.login_url, {**self.credentials, "next": target}
                )
                self.assertRedirects(response, reverse("main:show_main"))
                self.assertEqual(self.client.session[SESSION_KEY], str(self.user.pk))

    def test_authenticated_user_is_redirected_from_login_without_loop(self):
        self.client.force_login(self.user)
        response = self.client.get(self.login_url, follow=True)
        self.assertRedirects(response, reverse("main:show_main"))
        self.assertEqual(len(response.redirect_chain), 1)

    def test_post_logout_clears_session_and_shows_feedback(self):
        self.client.force_login(self.user)
        session = self.client.session
        session["private_state"] = "must-be-cleared"
        session.save()
        response = self.client.post(self.logout_url, follow=True)
        self.assertRedirects(response, reverse("main:show_main"))
        self.assertNotIn(SESSION_KEY, self.client.session)
        self.assertNotIn("private_state", self.client.session)
        self.assertContains(response, "Kamu berhasil keluar dari akun.")
        self.assertFalse(response.context["user"].is_authenticated)
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())

    def test_get_logout_is_rejected_and_keeps_session(self):
        self.client.force_login(self.user)
        response = self.client.get(self.logout_url)
        self.assertEqual(response.status_code, 405)
        self.assertEqual(self.client.session[SESSION_KEY], str(self.user.pk))

    def test_guest_header_links_to_login_and_registration_without_private_email(self):
        response = self.client.get(reverse("main:show_main"))
        self.assertContains(response, f'href="{self.login_url}"')
        self.assertContains(response, f'href="{reverse("accounts:register")}"')
        self.assertNotContains(response, self.user.email)

    def test_authenticated_header_uses_post_logout_forms(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("main:show_main"))
        self.assertContains(
            response, f'<form method="post" action="{self.logout_url}">'
        )
        self.assertNotContains(response, f'href="{self.logout_url}"')


class AuthenticationCsrfTests(TestCase):
    """Client biasa melewati CSRF; kelas ini mengaktifkan pemeriksaan nyata."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("nina.arum", password=PASSWORD)

    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)

    def test_registration_without_csrf_is_rejected_without_creating_account(self):
        response = self.client.post(
            reverse("accounts:register"), registration_data(username="new-user")
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(User.objects.count(), 1)
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_login_without_csrf_is_rejected_without_starting_session(self):
        response = self.client.post(
            reverse("accounts:login"),
            {"username": self.user.username, "password": PASSWORD},
        )
        self.assertEqual(response.status_code, 403)
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_logout_without_csrf_is_rejected_and_keeps_session(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("accounts:logout"))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.client.session[SESSION_KEY], str(self.user.pk))

    def test_registration_login_and_logout_accept_valid_csrf_tokens(self):
        self.client.get(reverse("accounts:register"))
        response = self.client.post(
            reverse("accounts:register"),
            {
                **registration_data(username="new-user"),
                "csrfmiddlewaretoken": self.client.cookies["csrftoken"].value,
            },
        )
        self.assertRedirects(response, reverse("profiles:profile_create"))
        new_user = User.objects.get(username="new-user")
        self.assertEqual(self.client.session[SESSION_KEY], str(new_user.pk))
        # Django merotasi CSRF token saat login; selalu gunakan token terbaru.
        response = self.client.post(
            reverse("accounts:logout"),
            {"csrfmiddlewaretoken": self.client.cookies["csrftoken"].value},
        )
        self.assertRedirects(response, reverse("main:show_main"))
        self.assertNotIn(SESSION_KEY, self.client.session)
        self.client.get(reverse("accounts:login"))
        response = self.client.post(
            reverse("accounts:login"),
            {
                "username": new_user.username,
                "password": PASSWORD,
                "csrfmiddlewaretoken": self.client.cookies["csrftoken"].value,
            },
        )
        self.assertRedirects(response, reverse("profiles:profile_create"))
        self.assertEqual(self.client.session[SESSION_KEY], str(new_user.pk))
