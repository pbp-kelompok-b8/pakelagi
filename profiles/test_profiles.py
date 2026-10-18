from django.contrib.auth.models import User
from django.test import TestCase


class ProfileTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("nina", password="Strong!9382")
        self.client.force_login(self.user)

    def test_member_pages_require_login_and_completed_profile(self):
        for path in ("/profile/", "/profile/edit/"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertRedirects(response, "/profile/create/?next=" + path, fetch_redirect_response=False)
        self.assertEqual(self.client.get("/").status_code, 200)
        self.assertEqual(self.client.get("/profile/create/").status_code, 200)
        self.client.logout()
        self.assertRedirects(self.client.get("/profile/"), "/accounts/login/?next=/profile/", fetch_redirect_response=False)

    def test_login_onboards_before_safe_return_and_rejects_unsafe_targets(self):
        for target in ("/?source=onboarding", "https://evil.example/", "//evil.example/", "/accounts/login/", "/profile/create/"):
            with self.subTest(target=target):
                self.client.logout()
                response = self.client.post("/accounts/login/", {
                    "username": "nina", "password": "Strong!9382", "next": target,
                })
                self.assertTrue(response.url.startswith("/profile/create/"))
                response = self.client.get(response.url)
                response = self.client.post(response.request["PATH_INFO"], {
                    "display_name": "Nina", "next": response.context["next"],
                })
                expected = target if target == "/?source=onboarding" else "/profile/"
                self.assertRedirects(response, expected)
                from profiles.models import Profile
                Profile.objects.filter(user=self.user).delete()

    def test_public_profile_keeps_account_email_private_and_contact_member_only(self):
        self.client.post("/profile/create/", {
            "display_name": "<script>Nina</script>", "email": "private@example.com",
            "contact_type": "instagram", "contact_value": "@nina.public",
        })
        path = f"/profile/{self.user.pk}/"
        self.assertNotContains(self.client.get("/profile/"), "private@example.com")
        self.client.logout()
        response = self.client.get(path)
        self.assertContains(response, "&lt;script&gt;Nina&lt;/script&gt;")
        self.assertNotContains(response, "private@example.com")
        self.assertNotContains(response, "@nina.public")
        viewer = User.objects.create_user("viewer")
        self.client.force_login(viewer)
        self.assertNotContains(self.client.get(path), "@nina.public")
        self.client.post("/profile/create/", {"display_name": "Viewer"})
        self.assertContains(self.client.get(path), "@nina.public")
        self.assertNotContains(self.client.get(path), "private@example.com")
        self.assertEqual(self.client.get("/profile/999999/").status_code, 404)

    def test_invalid_profile_does_not_complete_onboarding_or_change_email(self):
        cases = [
            ({"display_name": "   "}, "display_name"),
            ({"city": "Jl. Mawar No. 12"}, "city"),
            ({"contact_value": "Jalan Melati nomor 4"}, "contact_value"),
            ({"contact_type": "phone"}, "contact_type"),
            ({"email": "invalid"}, "email"),
            ({"contact_value": "javascript:alert(1)"}, "contact_value"),
            ({"contact_value": "https://[broken"}, "contact_value"),
        ]
        for fields, field in cases:
            with self.subTest(field=field):
                response = self.client.post("/profile/create/", {
                    "display_name": "Nina", "email": "new@example.com", **fields,
                })
                self.assertEqual(response.status_code, 200)
                self.assertIn(field, response.context["form"].errors)
                self.user.refresh_from_db()
                self.assertEqual(self.user.email, "")
                self.assertRedirects(self.client.get("/profile/"), "/profile/create/?next=/profile/", fetch_redirect_response=False)

    def test_edit_is_owner_scoped_and_create_cannot_duplicate_profile(self):
        other = User.objects.create_user("other", email="other@example.com")
        from profiles.models import Profile
        Profile.objects.create(user=other, display_name="Other")
        self.client.post("/profile/create/", {"display_name": "Nina"})
        response = self.client.post("/profile/edit/", {
            "display_name": "Nina Baru", "user": other.pk, "email": "nina@example.com",
            "bio": "Bio baru", "city": "Depok", "contact_type": "email",
            "contact_value": "public@example.com",
        }, follow=True)
        self.assertContains(response, "Nina Baru")
        self.assertNotContains(response, "nina@example.com")
        self.assertContains(self.client.get("/profile/edit/"), "nina@example.com")
        self.assertContains(response, "public@example.com")
        self.assertEqual(other.profile.display_name, "Other")
        other.refresh_from_db()
        self.assertEqual(other.email, "other@example.com")
        self.assertEqual(self.client.post(f"/profile/{other.pk}/", {"display_name": "Hacked"}).status_code, 405)
        self.assertRedirects(self.client.post("/profile/create/", {"display_name": "Duplicate"}), "/profile/")
        self.assertEqual(Profile.objects.filter(user=self.user).count(), 1)
        self.assertContains(self.client.get("/profile/"), "Nina Baru")
        # Legacy blank profiles must also complete onboarding.
        Profile.objects.filter(user=self.user).update(display_name="  ")
        self.assertRedirects(self.client.get("/profile/"), "/profile/create/?next=/profile/", fetch_redirect_response=False)
        self.assertRedirects(self.client.post("/profile/create/", {"display_name": "Restored"}), "/profile/")
        self.assertEqual(Profile.objects.filter(user=self.user).count(), 1)

    def test_profile_mutations_require_real_csrf_tokens(self):
        from django.test import Client
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(client.post("/profile/create/", {"display_name": "Nina"}).status_code, 403)
        client.get("/profile/create/")
        self.assertRedirects(client.post("/profile/create/", {
            "display_name": "Nina", "csrfmiddlewaretoken": client.cookies["csrftoken"].value,
        }), "/profile/")
        self.assertEqual(client.post("/profile/edit/", {"display_name": "Changed"}).status_code, 403)
        self.assertContains(client.get("/profile/"), "Nina")
        self.assertRedirects(client.post("/profile/edit/", {
            "display_name": "Changed", "csrfmiddlewaretoken": client.cookies["csrftoken"].value,
        }), "/profile/")
        self.assertContains(client.get("/profile/"), "Changed")

    def test_display_name_alone_completes_onboarding(self):
        response = self.client.post("/profile/create/", {"display_name": "Nina"}, follow=True)
        self.assertRedirects(response, "/profile/")
        self.assertContains(response, "Nina")
        self.assertContains(self.client.get("/profile/edit/"), 'value="Nina"')
