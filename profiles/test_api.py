import json

from django.contrib.auth.models import User
from django.db import DatabaseError, connection
from django.test import Client, TestCase, override_settings


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class ProfilesAPITests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("nina", email="private@example.com")
        self.client = self.browser(self.user)

    def browser(self, user=None):
        client = Client(enforce_csrf_checks=True)
        client.get("/accounts/login/")
        if user:
            client.force_login(user)
        return client

    def send(self, method, path="", data=None, client=None):
        client = client or self.client
        return client.generic(
            method, "/api/v1/profiles/" + path,
            json.dumps(data if data is not None else {}), content_type="application/json",
            HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value,
        )

    def test_onboarding_creates_profile_and_returns_owner_data(self):
        response = self.send("POST", data={"display_name": "  Nina Arum  "})
        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["profile"]["display_name"], "Nina Arum")
        self.assertEqual(body["profile"]["user_id"], self.user.pk)
        self.assertEqual(body["account"], {"username": "nina", "email": ""})
        self.assertEqual(set(body["profile"]), {
            "user_id", "display_name", "bio", "city", "avatar_url", "cover_url",
            "phone_number", "contact_type", "contact_value", "created_at", "updated_at",
        })
        self.assertTrue(body["profile"]["created_at"].endswith("Z"))

    def test_database_failure_rolls_back_profile_and_email(self):
        self.send("POST", data={"display_name": "Nina", "email": "old@example.com"})
        before = self.client.get("/api/v1/profiles/me/").json()

        def fail_email_update(execute, sql, params, many, context):
            if sql.startswith('UPDATE "auth_user"'):
                raise DatabaseError("private database details")
            return execute(sql, params, many, context)

        with connection.execute_wrapper(fail_email_update):
            response = self.send("PATCH", "me/", {"bio": "changed", "email": "new@example.com"})
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["error"]["code"], "server_error")
        self.assertNotIn("private database details", response.content.decode())
        self.assertEqual(self.client.get("/api/v1/profiles/me/").json(), before)

    def test_malformed_json_is_safe_and_does_not_change_profile(self):
        self.send("POST", data={"display_name": "Nina"})
        before = self.client.get("/api/v1/profiles/me/").json()
        for method, path in (("PATCH", "me/"),):
            response = self.client.generic(method, "/api/v1/profiles/" + path, b"{",
                                           content_type="application/json",
                                           HTTP_X_CSRFTOKEN=self.client.cookies["csrftoken"].value)
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json()["error"]["code"], "parse_error")
        self.assertEqual(self.client.get("/api/v1/profiles/me/").json(), before)

    def test_authentication_incomplete_profile_csrf_and_methods(self):
        guest = self.browser()
        for method, path in (("POST", ""), ("GET", "me/"), ("PATCH", "me/")):
            response = self.send(method, path, {"display_name": "Nina"}, guest)
            self.assertEqual(response.status_code, 401)
            self.assertNotIn("Location", response)
        for method in ("GET", "PATCH"):
            response = self.send(method, "me/")
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.json()["error"]["code"], "profile_incomplete")
            self.assertEqual(response.json()["next"], "/api/v1/profiles/")
        for browser in (guest, self.client):
            for method, path in (("POST", ""), ("PATCH", "me/")):
                response = browser.generic(method, "/api/v1/profiles/" + path,
                                           b"{}", content_type="application/json")
                self.assertEqual(response.status_code, 403)
                self.assertEqual(response.json()["error"]["code"], "csrf_failed")
        for method, path in (("GET", ""), ("POST", "me/"), ("DELETE", "me/"),
                             ("PATCH", f"{self.user.pk}/")):
            response = self.send(method, path)
            self.assertEqual(response.status_code, 405)
            self.assertEqual(response.json()["error"]["code"], "method_not_allowed")

    def test_missing_and_blank_public_profiles_share_same_404(self):
        from profiles.models import Profile
        Profile.objects.create(user=self.user, display_name="  ")
        blank = self.client.get(f"/api/v1/profiles/{self.user.pk}/")
        missing = self.client.get("/api/v1/profiles/999999/")
        self.assertEqual(blank.status_code, 404)
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(blank.json(), missing.json())

    def test_invalid_patch_preserves_all_fields_and_account_email(self):
        self.send("POST", data={"display_name": "Nina", "bio": "Original", "email": "old@example.com",
                                "avatar_url": "https://images.example.com/a.jpg"})
        before = self.client.get("/api/v1/profiles/me/").json()
        response = self.send("PATCH", "me/", {"display_name": "  ", "email": "new@example.com",
                                               "bio": "changed", "remove_avatar": True})
        self.assertEqual(response.status_code, 400)
        self.assertIn("display_name", response.json()["error"]["fields"])
        self.assertEqual(self.client.get("/api/v1/profiles/me/").json(), before)

    def test_profile_validation_matches_existing_rules(self):
        cases = [
            ({"display_name": " "}, "display_name"),
            ({"display_name": "x" * 151}, "display_name"),
            ({"bio": "x" * 501}, "bio"), ({"city": "x" * 101}, "city"),
            ({"city": "Jl. Melati nomor 4"}, "city"),
            ({"email": "invalid"}, "email"),
            ({"phone_number": "+01234"}, "phone_number"),
            ({"phone_number": "+1234567890123456"}, "phone_number"),
            ({"avatar_url": "http://images.example.com/a.jpg"}, "avatar_url"),
            ({"cover_url": "https://localhost/a.jpg"}, "cover_url"),
            ({"avatar_url": "https://127.0.0.1/a.jpg"}, "avatar_url"),
            ({"avatar_url": "https://user:pass@images.example.com/a.jpg"}, "avatar_url"),
            ({"contact_type": "unknown"}, "contact_type"),
            ({"contact_type": "email"}, "contact_value"),
            ({"contact_value": "value"}, "contact_type"),
            ({"contact_type": "email", "contact_value": "invalid"}, "contact_value"),
            ({"contact_type": "instagram", "contact_value": "https://instagram.com/p/123/"}, "contact_value"),
            ({"contact_type": "other", "contact_value": "javascript:alert(1)"}, "contact_value"),
            ({"contact_type": "other", "contact_value": "https://u:p@example.com/"}, "contact_value"),
            ({"contact_type": "other", "contact_value": "Jl. Melati 4"}, "contact_value"),
        ]
        for values, field in cases:
            with self.subTest(values=values):
                response = self.send("POST", data={"display_name": "Nina", **values})
                self.assertEqual(response.status_code, 400)
                self.assertIn(field, response.json()["error"]["fields"])
        self.assertEqual(self.client.get("/api/v1/profiles/me/").status_code, 403)
        self.assertEqual(self.send("POST", data={"display_name": "Nina"}).status_code, 201)

    def test_contact_variants_and_optional_field_clearing(self):
        self.send("POST", data={"display_name": "Nina"})
        url = f"/api/v1/profiles/{self.user.pk}/"
        self.assertIsNone(self.client.get(url).json()["contact"])
        cases = [
            ({"phone_number": "081234567890"},
             {"type": None, "value": None, "url": None, "phone_number": "+6281234567890"}),
            ({"phone_number": "", "contact_type": "email", "contact_value": "seller@example.com"},
             {"type": "email", "value": "seller@example.com", "url": "mailto:seller@example.com", "phone_number": None}),
            ({"contact_type": "other", "contact_value": "Contact by appointment"},
             {"type": "other", "value": "Contact by appointment", "url": None, "phone_number": None}),
            ({"contact_value": "https://example.com/contact"},
             {"type": "other", "value": "https://example.com/contact", "url": "https://example.com/contact", "phone_number": None}),
            ({"contact_type": "instagram", "contact_value": "https://www.instagram.com/Nina.Arum/"},
             {"type": "instagram", "value": "nina.arum", "url": "https://www.instagram.com/nina.arum/", "phone_number": None}),
        ]
        for payload, expected in cases:
            with self.subTest(payload=payload):
                self.assertEqual(self.send("PATCH", "me/", payload).status_code, 200)
                self.assertEqual(self.client.get(url).json()["contact"], expected)
        self.assertEqual(self.send("PATCH", "me/", {"contact_type": "", "contact_value": ""}).status_code, 200)
        self.assertIsNone(self.client.get(url).json()["contact"])

    def test_non_object_json_and_wrong_field_types_are_validation_errors(self):
        for data in ([], False, "text", 5, {"display_name": 123}, {"display_name": "Nina", "bio": []}):
            with self.subTest(data=data):
                response = self.send("POST", data=data)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()["error"]["code"], "validation_error")
        self.send("POST", data={"display_name": "Nina"})
        for data in ([], False, "text", {"remove_avatar": "true"}, {"city": None}):
            with self.subTest(data=data):
                response = self.send("PATCH", "me/", data)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()["error"]["code"], "validation_error")

    def test_patch_removal_wins_over_invalid_url_and_preserves_omitted_fields(self):
        self.send("POST", data={"display_name": "Nina", "avatar_url": "https://images.example.com/a.jpg",
                                "cover_url": "https://images.example.com/c.jpg", "email": "old@example.com"})
        response = self.send("PATCH", "me/", {"remove_avatar": True, "avatar_url": "http://localhost/bad"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["profile"]["avatar_url"], "")
        self.assertEqual(response.json()["profile"]["cover_url"], "https://images.example.com/c.jpg")
        self.assertEqual(response.json()["account"]["email"], "old@example.com")
        response = self.send("PATCH", "me/", {"remove_cover": True, "email": ""})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["profile"]["cover_url"], "")
        self.assertEqual(response.json()["account"]["email"], "")
        self.assertNotIn("remove_avatar", response.json()["profile"])

    def test_public_profile_redacts_contacts_by_viewer_and_never_exposes_account_email(self):
        self.send("POST", data={"display_name": "Nina", "email": "secret@example.com",
                                "contact_type": "instagram", "contact_value": "@Nina.Arum",
                                "phone_number": "081234567890"})
        url = f"/api/v1/profiles/{self.user.pk}/"
        guest = self.browser()
        incomplete = self.browser(User.objects.create_user("incomplete"))
        for browser in (guest, incomplete):
            response = browser.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertIsNone(response.json()["contact"])
            self.assertNotIn("secret@example.com", response.content.decode())
            self.assertNotIn("+6281234567890", response.content.decode())
            self.assertEqual(set(response.json()["profile"]), {
                "user_id", "display_name", "bio", "city", "avatar_url", "cover_url"})
            self.assertEqual(response["Cache-Control"], "private, no-store")
        expected = {"type": "instagram", "value": "nina.arum",
                    "url": "https://www.instagram.com/nina.arum/", "phone_number": "+6281234567890"}
        self.assertEqual(self.client.get(url).json()["contact"], expected)
        self.send("POST", data={"display_name": "Viewer"}, client=incomplete)
        self.assertEqual(incomplete.get(url).json()["contact"], expected)

    def test_owner_reads_and_partially_edits_only_own_profile(self):
        self.send("POST", data={"display_name": "Nina", "bio": "original",
                                "email": "private@example.com", "city": "Depok"})
        before = self.client.get("/api/v1/profiles/me/")
        self.assertEqual(before.status_code, 200)
        response = self.send("PATCH", "me/", {"bio": "changed", "user_id": 999,
                                               "username": "attacker", "created_at": "fake"})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["profile"]["bio"], "changed")
        self.assertEqual(body["profile"]["city"], "Depok")
        self.assertEqual(body["profile"]["user_id"], self.user.pk)
        self.assertEqual(body["account"], {"username": "nina", "email": "private@example.com"})
        self.assertEqual(body["profile"]["created_at"], before.json()["profile"]["created_at"])
        self.assertEqual(self.client.get("/api/v1/profiles/me/").json(), body)

    def test_incomplete_profile_is_completed_and_complete_profile_conflicts(self):
        from profiles.models import Profile
        Profile.objects.create(user=self.user, display_name="   ", bio="old")
        response = self.send("POST", data={"display_name": "Nina"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["profile"]["bio"], "")
        response = self.send("POST", data={"display_name": "Replacement"})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error"]["code"], "profile_already_complete")
