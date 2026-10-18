from django.contrib.auth.models import User
from django.test import TestCase


class ProfileFieldsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="seller", password="test-password")
        self.client.force_login(self.user)

    def create_profile(self, **values):
        return self.client.post("/profile/create/", {"display_name": "Seller", **values})

    def test_other_contact_remains_escaped_plain_text_and_rejects_dangerous_schemes(self):
        response = self.create_profile(contact_type="other", contact_value='<b>Chat seller</b>')
        self.assertEqual(response.status_code, 302)
        response = self.client.get("/profile/edit/")
        self.assertContains(response, 'value="&lt;b&gt;Chat seller&lt;/b&gt;"')
        self.assertNotContains(response, '<b>Chat seller</b>')
        for value in ("javascript:alert(1)", "data:text/html,test", "vbscript:msgbox(1)"):
            with self.subTest(value=value):
                response = self.client.post("/profile/edit/", {"display_name": "Seller", "contact_type": "other", "contact_value": value})
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'id="id_contact_value_error"')

    def test_remove_image_actions_are_independent_and_only_apply_on_success(self):
        images = {"avatar_url": "https://example.com/avatar.jpg", "cover_url": "https://example.com/cover.jpg"}
        self.assertEqual(self.create_profile(**images).status_code, 302)
        response = self.client.post("/profile/edit/", {"display_name": "", **images, "remove_avatar": "on", "remove_cover": "on"})
        self.assertEqual(response.status_code, 200)
        response = self.client.get("/profile/edit/")
        for value in images.values():
            self.assertContains(response, f'value="{value}"')
        self.assertContains(response, 'name="remove_avatar"')
        self.assertContains(response, 'name="remove_cover"')
        response = self.client.post("/profile/edit/", {"display_name": "Seller", **images, "remove_avatar": "on"})
        self.assertEqual(response.status_code, 302)
        response = self.client.get("/profile/edit/")
        self.assertNotContains(response, 'value="https://example.com/avatar.jpg"')
        self.assertContains(response, 'value="https://example.com/cover.jpg"')
        response = self.client.post("/profile/edit/", {"display_name": "Seller", **images, "remove_cover": "on"})
        self.assertEqual(response.status_code, 302)
        response = self.client.get("/profile/edit/")
        self.assertContains(response, 'value="https://example.com/avatar.jpg"')
        self.assertNotContains(response, 'value="https://example.com/cover.jpg"')

    def test_instagram_rejects_non_profile_urls_and_invalid_handles(self):
        for value in ("https://evil.example/seller/", "https://instagram.com/p/ABC/", "https://instagram.com/reels/", "https://instagram.com/seller/?x=1", "https://instagram.com/seller/#bio", "https://user@instagram.com/seller/", "https://instagram.com:444/seller/", "https://instagram.com//seller//", "https://instagram.com/%73eller/", "bad..handle", ".seller", "seller.", "two words", "a" * 31):
            with self.subTest(value=value):
                response = self.create_profile(contact_type="instagram", contact_value=value)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'id="id_contact_value_error"')

    def test_instagram_handles_and_profile_urls_are_normalized(self):
        self.assertEqual(self.create_profile().status_code, 302)
        for value in ("@Seller.Shop", "Seller.Shop", "https://www.instagram.com/Seller.Shop/"):
            with self.subTest(value=value):
                response = self.client.post("/profile/edit/", {"display_name": "Seller", "contact_type": "instagram", "contact_value": value})
                self.assertEqual(response.status_code, 302)
                self.assertContains(self.client.get("/profile/edit/"), 'value="seller.shop"')

    def test_email_contact_requires_a_valid_email_address(self):
        response = self.create_profile(contact_type="email", contact_value="invalid")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="id_contact_value_error"')
        response = self.create_profile(contact_type="email", contact_value="seller@example.com")
        self.assertEqual(response.status_code, 302)
        self.assertContains(self.client.get("/profile/edit/"), 'value="seller@example.com"')

    def test_contact_method_and_value_must_be_paired(self):
        for values, field in (({"contact_type": "email"}, "contact_value"), ({"contact_value": "seller@example.com"}, "contact_type")):
            with self.subTest(values=values):
                response = self.create_profile(**values)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, f'id="id_{field}_error"')

    def test_profile_text_limits_are_enforced(self):
        for field, limit in (("display_name", 150), ("bio", 500), ("city", 100)):
            with self.subTest(field=field):
                response = self.create_profile(**{field: "x" * (limit + 1)})
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, f'id="id_{field}_error"')

    def test_invalid_phone_number_is_rejected(self):
        for value in ("12345", "+01234", "+1234567890123456", "+62abc", "08<script>"):
            with self.subTest(value=value):
                response = self.create_profile(phone_number=value)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'id="id_phone_number_error"')

    def test_phone_number_is_normalized_and_saved_as_optional_contact(self):
        response = self.create_profile(phone_number="081234567890")
        self.assertEqual(response.status_code, 302)
        self.assertContains(self.client.get("/profile/edit/"), 'value="+6281234567890"')
        response = self.client.post("/profile/edit/", {"display_name": "Seller", "phone_number": "+442079460123"})
        self.assertEqual(response.status_code, 302)
        self.assertContains(self.client.get("/profile/edit/"), 'value="+442079460123"')

    def test_images_reject_non_https_and_non_external_urls(self):
        for field in ("avatar_url", "cover_url"):
            for value in ("http://example.com/a.jpg", "javascript:alert(1)", "//example.com/a.jpg", "https://localhost/a", "https://127.0.0.1/a", "https://192.168.1.2/a", "https://user:pass@example.com/a"):
                with self.subTest(field=field, value=value):
                    response = self.create_profile(**{field: value})
                    self.assertEqual(response.status_code, 200)
                    self.assertContains(response, f'id="id_{field}_error"')

    def test_external_https_images_are_saved_and_shown_for_editing(self):
        response = self.create_profile(
            avatar_url="https://images.example.com/avatar.jpg",
            cover_url="https://images.example.com/cover.jpg",
        )
        self.assertEqual(response.status_code, 302)
        response = self.client.get("/profile/edit/")
        self.assertContains(response, 'value="https://images.example.com/avatar.jpg"')
        self.assertContains(response, 'value="https://images.example.com/cover.jpg"')
