from django.contrib.auth.models import User
from django.test import TestCase, override_settings


@override_settings(DEBUG=False)
class NotFoundTests(TestCase):
    def test_unknown_url_shows_branded_generic_not_found_page(self):
        response = self.client.get("/halaman-tidak-ada/")

        self.assertContains(response, "Halaman tidak ditemukan", status_code=404)
        self.assertContains(response, "Pakelagi", status_code=404)
        self.assertTemplateUsed(response, "base.html")
        self.assertTemplateUsed(response, "components/header.html")
        self.assertTemplateUsed(response, "components/footer.html")

    def test_not_found_page_has_working_home_navigation(self):
        response = self.client.get("/halaman-tidak-ada/")

        self.assertContains(
            response, '<a href="/" class="btn btn-primary">Kembali ke beranda</a>',
            status_code=404, html=True,
        )
        self.assertEqual(self.client.get("/").status_code, 200)

    def test_missing_resources_are_generic_and_do_not_echo_request_details(self):
        for path in ("/rahasia-internal/", "/profile/999999/"):
            with self.subTest(path=path):
                response = self.client.get(path, {"token": "private-query-sentinel"})

                self.assertContains(response, "Halaman tidak ditemukan", status_code=404)
                for detail in (
                    path, "private-query-sentinel", "Traceback", "URLconf", "pakelagi.urls",
                    "No Profile matches", "sudah terjual",
                ):
                    self.assertNotContains(response, detail, status_code=404)

    def test_not_found_page_remains_public_regardless_of_onboarding(self):
        user = User.objects.create_user("pengunjung")
        self.client.force_login(user)
        for completed in (False, True):
            with self.subTest(completed_profile=completed):
                if completed:
                    self.client.post("/profile/create/", {"display_name": "Pengunjung"})
                for path in ("/halaman-tidak-ada/", "/profile/999999/"):
                    with self.subTest(path=path):
                        response = self.client.get(path)

                        self.assertContains(response, "Halaman tidak ditemukan", status_code=404)
                        self.assertContains(response, "Keluar", status_code=404)
