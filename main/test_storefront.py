from django.contrib.auth.models import User
from django.test import TestCase

from main.models import Profile


class StorefrontTests(TestCase):
    def setUp(self):
        self.seller = User.objects.create_user("seller", email="private@example.com")
        Profile.objects.create(user=self.seller, display_name="Nina", bio="Lemari kedua", city="Depok")
        self.path = f"/profile/{self.seller.pk}/"

    def test_owner_and_public_share_storefront_without_account_email(self):
        self.client.force_login(self.seller)
        for path in ("/profile/", self.path):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertContains(response, "Belum ada barang dijual")
                self.assertContains(response, "0 dijual")
                self.assertContains(response, "0 terjual")
                self.assertNotContains(response, "private@example.com")
                self.assertContains(response, 'href="/profile/edit/"')

    def test_contacts_are_member_only_with_safe_return_invites(self):
        Profile.objects.filter(user=self.seller).update(contact_type="instagram", contact_value="nina.public")
        for authenticated in (False, True):
            if authenticated:
                self.client.force_login(User.objects.create_user("incomplete"))
            response = self.client.get(self.path + "?tab=terjual&sort=terbaru")
            self.assertNotContains(response, "nina.public")
            self.assertContains(response, "next=")
            self.assertContains(response, "Lengkapi profil" if authenticated else "Masuk untuk melihat kontak")
            partial = self.client.get(self.path, HTTP_HX_REQUEST="true")
            self.assertNotContains(partial, "nina.public")
        self.client.force_login(self.seller)
        response = self.client.get(self.path)
        self.assertContains(response, "@nina.public")
        self.assertContains(response, 'href="https://www.instagram.com/nina.public/"')
        self.assertContains(response, 'rel="noopener noreferrer"')

    def test_contact_email_other_and_empty_states_do_not_use_account_email(self):
        self.client.force_login(self.seller)
        for contact_type, value, expected in (
            ("email", "seller@example.com", 'href="mailto:seller@example.com"'),
            ("other", "https://example.com/contact", 'href="https://example.com/contact"'),
            ("other", '<script>alert("x")</script>', "&lt;script&gt;"),
            ("other", "javascript:alert(1)", "javascript:alert(1)"),
            ("", "", "Penjual belum menambahkan kontak."),
        ):
            with self.subTest(contact_type=contact_type, value=value):
                Profile.objects.filter(user=self.seller).update(contact_type=contact_type, contact_value=value)
                response = self.client.get(self.path)
                self.assertContains(response, expected)
                self.assertNotContains(response, 'href="javascript:')
                self.assertNotContains(response, "private@example.com")

    def test_public_blank_or_absent_profile_is_not_found(self):
        Profile.objects.filter(user=self.seller).update(display_name="   ")
        self.assertEqual(self.client.get(self.path).status_code, 404)
        Profile.objects.filter(user=self.seller).delete()
        self.assertEqual(self.client.get(self.path).status_code, 404)

    def test_images_and_phone_render_with_fallbacks_but_phone_never_reaches_nonmembers(self):
        self.client.force_login(self.seller)
        response = self.client.post("/profile/edit/", {
            "display_name": "Nina", "avatar_url": "https://images.example.com/avatar.jpg",
            "cover_url": "https://images.example.com/cover.jpg", "phone_number": "081234567890",
        }, follow=True)
        self.assertContains(response, 'alt="Avatar Nina"')
        self.assertContains(response, 'src="https://images.example.com/cover.jpg" alt=""')
        self.assertContains(response, 'onerror="this.remove()"')
        self.assertContains(response, "Telepon: +6281234567890")
        self.assertNotContains(response, "Penjual belum menambahkan kontak.")
        self.client.logout()
        response = self.client.get(self.path)
        self.assertNotContains(response, "+6281234567890")
        viewer = User.objects.create_user("onboarding-viewer")
        self.client.force_login(viewer)
        self.assertNotContains(self.client.get(self.path), "+6281234567890")

    def test_edit_rejects_credentials_in_contact_urls(self):
        self.client.force_login(self.seller)
        response = self.client.post("/profile/edit/", {
            "display_name": "Nina", "contact_type": "other",
            "contact_value": "https://user:secret@example.com/contact",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "URL kontak tidak boleh memuat kredensial.")
        self.assertNotContains(self.client.get(self.path), "user:secret")

    def test_history_restore_gets_full_document_and_private_cache_policy(self):
        response = self.client.get(self.path, HTTP_HX_REQUEST="true", HTTP_HX_HISTORY_RESTORE_REQUEST="true")
        self.assertContains(response, "<!DOCTYPE html>")
        self.assertEqual(response.headers["Cache-Control"], "private, no-store")

    def test_edit_explains_external_image_privacy_and_reports_success(self):
        self.client.force_login(self.seller)
        response = self.client.get("/profile/edit/")
        self.assertContains(response, "alamat IP")
        self.assertContains(response, "token rahasia")
        self.assertContains(response, "HTTPS")
        response = self.client.post("/profile/edit/", {"display_name": "Nina"}, follow=True)
        self.assertContains(response, "Profil berhasil disimpan.")

    def test_tabs_sort_and_htmx_use_shareable_urls_and_status_specific_empty_states(self):
        response = self.client.get(self.path, {"tab": "terjual", "sort": "harga_terendah", "page": "3"})
        self.assertContains(response, "Belum ada barang terjual")
        self.assertContains(response, 'value="harga_terendah" selected')
        self.assertContains(response, 'aria-current="page"')
        self.assertNotContains(response, "Sudah dipakai lagi")
        partial = self.client.get(self.path, {"tab": "terjual"}, HTTP_HX_REQUEST="true")
        self.assertContains(partial, "Belum ada barang terjual")
        self.assertNotContains(partial, "<!DOCTYPE html>")
        self.assertIn("HX-Request", partial.headers["Vary"])
        restored = self.client.get(self.path, {"tab": "unknown", "sort": "unknown", "page": "-2"})
        self.assertContains(restored, "Belum ada barang dijual")
        self.assertContains(restored, 'value="terbaru" selected')
