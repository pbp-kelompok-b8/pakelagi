from django.urls import reverse

from favorites.test_views import FavoriteTestCase
from listings.models import Listing


class FavoriteHtmxTests(FavoriteTestCase):
    def test_htmx_list_returns_partial_and_history_restore_returns_page(self):
        self.save_favorite()
        response = self.client.get(self.list_url, HTTP_HX_REQUEST="true")
        self.assertTemplateUsed(response, "favorites/components/results.html")
        self.assertTemplateNotUsed(response, "base.html")
        response = self.client.get(self.list_url, HTTP_HX_REQUEST="true", HTTP_HX_HISTORY_RESTORE_REQUEST="true")
        self.assertTemplateUsed(response, "favorites/list.html")

    def test_htmx_remove_last_item_updates_count_and_empty_state(self):
        self.save_favorite()
        response = self.client.post(self.action_url("remove"), {"surface": "list"}, HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "0 dari 0 favorit")
        self.assertContains(response, "Belum ada favorit")
        self.assertTemplateNotUsed(response, "base.html")

    def test_htmx_remove_keeps_selected_category(self):
        self.save_favorite()
        response = self.client.post(self.action_url("remove"), {
            "surface": "list", "category": "Top",
        }, HTTP_HX_REQUEST="true")
        self.assertContains(response, 'aria-current="page">Top</a>')
        self.assertNotIn("HX-Push-Url", response)

    def test_htmx_hidden_removal_never_returns_listing_details(self):
        self.save_favorite(note="Catatan rahasia")
        Listing.objects.filter(pk=self.listing.pk).update(status=Listing.Status.HIDDEN)
        response = self.client.post(self.action_url("remove"), {"slot": "card"}, HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.listing.title)
        self.assertNotContains(response, self.listing.image_url)

    def test_htmx_note_editor_and_save_are_inline(self):
        favorite = self.save_favorite()
        url = reverse("favorites:edit", args=[favorite.pk])
        response = self.client.get(url, HTTP_HX_REQUEST="true")
        self.assertTemplateNotUsed(response, "base.html")
        self.assertContains(response, 'name="note"')
        response = self.client.post(url, {"note": "Baru"}, HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Baru")
        self.assertTemplateNotUsed(response, "base.html")
        self.assertContains(response, "Catatan disimpan")

    def test_note_return_url_with_spaces_round_trips_and_can_be_cleared(self):
        favorite = self.save_favorite(note="Awal")
        url = reverse("favorites:edit", args=[favorite.pk])
        target = self.list_url + "?category=Modest+Wear"
        response = self.client.get(url, {"next": target}, HTTP_HX_REQUEST="true")
        self.assertContains(response, 'value="/favorites/?category=Modest+Wear"')
        response = self.client.post(url, {"note": "", "next": target}, HTTP_HX_REQUEST="true")
        self.assertContains(response, "Belum ada catatan.")
        self.assertContains(response, "next=/favorites/%3Fcategory%3DModest%2BWear")
        favorite.refresh_from_db()
        self.assertEqual(favorite.note, "")

    def test_htmx_invalid_note_keeps_errors_and_existing_value(self):
        favorite = self.save_favorite(note="Awal")
        response = self.client.post(reverse("favorites:edit", args=[favorite.pk]), {
            "note": "a" * 1001,
        }, HTTP_HX_REQUEST="true")
        self.assertContains(response, "errorlist")
        self.assertTemplateNotUsed(response, "base.html")
        favorite.refresh_from_db()
        self.assertEqual(favorite.note, "Awal")

    def test_htmx_expired_session_uses_full_page_redirect(self):
        self.client.logout()
        response = self.client.post(self.action_url("add"), {"next": "/listings/?category=Top"},
                                    HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response["HX-Redirect"].startswith(reverse("accounts:login")))
        self.assertNotIn("Location", response)

    def test_htmx_incomplete_profile_uses_full_page_onboarding(self):
        self.client.force_login(self.incomplete)
        response = self.client.get(self.list_url, HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response["HX-Redirect"].startswith(reverse("profiles:profile_create")))

    def test_favorite_responses_are_private_and_vary_on_session_and_htmx(self):
        for headers in ({}, {"HTTP_HX_REQUEST": "true"}):
            response = self.client.get(self.list_url, **headers)
            self.assertIn("private", response["Cache-Control"])
            self.assertIn("no-store", response["Cache-Control"])
            for name in ("Cookie", "HX-Request", "HX-History-Restore-Request"):
                self.assertIn(name, response["Vary"])
