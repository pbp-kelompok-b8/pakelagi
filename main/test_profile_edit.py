from django.contrib.auth.models import User
from django.test import TestCase

from main.models import Profile


class ProfileEditPageTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("nina", email="private@example.com")
        Profile.objects.create(
            user=self.user, display_name="Nina Arum", bio="Lemari kedua.", city="Depok",
            contact_type="instagram", contact_value="nina.lemari",
        )
        self.client.force_login(self.user)

    def test_edit_groups_fields_and_offers_public_profile_navigation(self):
        response = self.client.get("/profile/edit/")
        for text in ("Identitas", "Kontak", "Foto toko", "Pratinjau", "Simpan perubahan", "Batal", "Lihat profil publik"):
            self.assertContains(response, text)
        self.assertContains(response, f'href="/profile/{self.user.pk}/"')
        for field in ("display_name", "bio", "city", "contact_type", "contact_value", "phone_number", "email", "avatar_url", "cover_url", "remove_avatar", "remove_cover"):
            self.assertContains(response, f'name="{field}"')
        self.assertContains(response, "500 karakter")
        self.assertNotContains(response, "Terverifikasi")

    def test_invalid_edit_retains_fields_and_guest_preview_excludes_private_contacts(self):
        response = self.client.post("/profile/edit/", {
            "display_name": "Nina Baru", "city": "Bogor", "bio": "Bio baru.",
            "contact_type": "email", "contact_value": "bukan-email", "email": "private@example.com",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Masukkan alamat email kontak yang valid.")
        self.assertContains(response, 'value="Nina Baru"')
        self.assertContains(response, 'type="radio" name="contact_type" value="email" checked')
        html = response.content.decode()
        preview = html.split('aria-label="Pratinjau profil publik"', 1)[1]
        self.assertIn("Nina Baru", preview)
        self.assertIn("Bogor", preview)
        self.assertNotIn("private@example.com", preview)
        self.assertNotIn("bukan-email", preview)
        response = self.client.post("/profile/edit/", {"display_name": "Nina Baru"})
        self.assertRedirects(response, "/profile/")
        self.assertContains(self.client.get("/profile/"), "Nina Baru")
