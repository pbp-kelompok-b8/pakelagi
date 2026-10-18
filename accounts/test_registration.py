from django.contrib.auth import SESSION_KEY
from django.contrib.auth.hashers import identify_hasher
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


from accounts.testing import PASSWORD, registration_data


class RegistrationTests(TestCase):
    """Spesifikasi 4.1, 5.1 langkah 1-4, dan 11: registrasi akun."""

    def setUp(self):
        self.url = reverse("accounts:register")

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
        self.assertRedirects(response, "/profile/create/")
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
