from django.contrib.auth import SESSION_KEY
from django.contrib.auth.hashers import identify_hasher
from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse


PASSWORD = "Preloved!Strong9382"


def registration_data(**overrides):
    data = {
        "username": "nina.arum",
        "password1": PASSWORD,
        "password2": PASSWORD,
    }
    data.update(overrides)
    return data


class RegistrationTests(TestCase):
    """Spesifikasi 4.1, 5.1 langkah 1-4, dan 11: registrasi akun."""

    def setUp(self):
        self.url = reverse("main:register")

    def assert_registration_rejected(self, data, field, code):
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        errors = response.context["form"].errors.as_data()
        self.assertIn(code, [error.code for error in errors[field]])
        self.assertFalse(User.objects.filter(username=data.get("username", "")).exists())
        self.assertNotIn(SESSION_KEY, self.client.session)
        return response

    def test_guest_can_open_registration_form(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/register.html")
        self.assertTemplateUsed(response, "base.html")
        self.assertEqual(
            list(response.context["form"].fields),
            ["username", "email", "password1", "password2"],
        )
        self.assertContains(response, 'name="csrfmiddlewaretoken"')

    def test_valid_registration_hashes_password_and_starts_session(self):
        response = self.client.post(self.url, registration_data(), follow=True)
        # Fallback tahap auth: beranda, bukan bukti onboarding sudah tersedia.
        self.assertRedirects(response, reverse("main:show_main"))
        user = User.objects.get(username="nina.arum")
        self.assertEqual(user.email, "")
        self.assertNotEqual(user.password, PASSWORD)
        self.assertTrue(user.check_password(PASSWORD))
        self.assertIsNotNone(identify_hasher(user.password))
        self.assertEqual(self.client.session[SESSION_KEY], str(user.pk))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertContains(response, "Akun berhasil dibuat.")

    def test_optional_email_is_saved_on_django_user(self):
        response = self.client.post(
            self.url, registration_data(email="nina@example.com")
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(User.objects.get().email, "nina@example.com")

    def test_email_help_explicitly_states_private_and_unverified(self):
        response = self.client.get(self.url)
        self.assertContains(
            response,
            "Email ini bersifat privat dan belum diverifikasi, bukan kontak publik.",
        )
        self.assertFalse(response.context["form"].fields["email"].required)

    def test_invalid_email_is_rejected(self):
        self.assert_registration_rejected(
            registration_data(email="not-an-email"), "email", "invalid"
        )

    def test_duplicate_username_is_rejected_without_changing_existing_account(self):
        existing = User.objects.create_user("nina.arum", password=PASSWORD)
        original_hash = existing.password
        response = self.client.post(self.url, registration_data())
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"], "username",
            "Username ini sudah digunakan. Silakan pilih username lain.",
        )
        self.assertContains(
            response, "Username ini sudah digunakan. Silakan pilih username lain."
        )
        self.assertEqual(User.objects.count(), 1)
        existing.refresh_from_db()
        self.assertEqual(existing.password, original_hash)
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_required_fields_cannot_be_empty(self):
        for field in ("username", "password1", "password2"):
            with self.subTest(field=field):
                self.assert_registration_rejected(
                    registration_data(**{field: ""}), field, "required"
                )

    def test_invalid_username_is_rejected(self):
        self.assert_registration_rejected(
            registration_data(username="invalid username!"), "username", "invalid"
        )

    def test_password_confirmation_must_match(self):
        response = self.assert_registration_rejected(
            registration_data(password2="Different!Password9382"),
            "password2", "password_mismatch",
        )
        self.assertContains(response, "Konfirmasi kata sandi tidak sama.")

    def test_all_configured_django_password_validators_are_applied(self):
        cases = (
            ("Ab!9x", "password_too_short"),
            ("password", "password_too_common"),
            ("938271645012", "password_entirely_numeric"),
            ("nina.arum", "password_too_similar"),
        )
        for password, code in cases:
            with self.subTest(code=code):
                self.assert_registration_rejected(
                    registration_data(password1=password, password2=password),
                    "password2", code,
                )

    def test_authenticated_user_cannot_create_another_account(self):
        user = User.objects.create_user("existing", password=PASSWORD)
        self.client.force_login(user)
        for method in (self.client.get, self.client.post):
            with self.subTest(method=method.__name__):
                response = method(self.url, registration_data())
                self.assertRedirects(response, reverse("main:show_main"))
                self.assertEqual(User.objects.count(), 1)
                self.assertEqual(self.client.session[SESSION_KEY], str(user.pk))


class LoginLogoutTests(TestCase):
    """Spesifikasi 5.2, 6, dan 10: sesi, pesan generik, redirect aman."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            "nina.arum", email="private@example.com", password=PASSWORD
        )

    def setUp(self):
        self.login_url = reverse("main:login")
        self.logout_url = reverse("main:logout")
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
        self.assertContains(response, f'href="{reverse("main:register")}"')
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
            reverse("main:register"), registration_data(username="new-user")
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(User.objects.count(), 1)
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_login_without_csrf_is_rejected_without_starting_session(self):
        response = self.client.post(
            reverse("main:login"),
            {"username": self.user.username, "password": PASSWORD},
        )
        self.assertEqual(response.status_code, 403)
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_logout_without_csrf_is_rejected_and_keeps_session(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("main:logout"))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.client.session[SESSION_KEY], str(self.user.pk))

    def test_registration_login_and_logout_accept_valid_csrf_tokens(self):
        self.client.get(reverse("main:register"))
        response = self.client.post(
            reverse("main:register"),
            {
                **registration_data(username="new-user"),
                "csrfmiddlewaretoken": self.client.cookies["csrftoken"].value,
            },
        )
        self.assertRedirects(response, reverse("main:show_main"))
        new_user = User.objects.get(username="new-user")
        self.assertEqual(self.client.session[SESSION_KEY], str(new_user.pk))
        # Django merotasi CSRF token saat login; selalu gunakan token terbaru.
        response = self.client.post(
            reverse("main:logout"),
            {"csrfmiddlewaretoken": self.client.cookies["csrftoken"].value},
        )
        self.assertRedirects(response, reverse("main:show_main"))
        self.assertNotIn(SESSION_KEY, self.client.session)
        self.client.get(reverse("main:login"))
        response = self.client.post(
            reverse("main:login"),
            {
                "username": new_user.username,
                "password": PASSWORD,
                "csrfmiddlewaretoken": self.client.cookies["csrftoken"].value,
            },
        )
        self.assertRedirects(response, reverse("main:show_main"))
        self.assertEqual(self.client.session[SESSION_KEY], str(new_user.pk))
