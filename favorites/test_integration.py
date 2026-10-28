import json
from html.parser import HTMLParser

from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from favorites.models import Favorite
from favorites.test_views import FavoriteTestCase
from listings.models import Listing
from listings.test_detail import create_listing


class FormParser(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.forms = []
        self.inputs = []
        self.nested = False
        self.current = None
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "form":
            self.nested |= self.current is not None
            self.current = attrs
            self.forms.append(attrs)
        if tag in {"input", "select", "button"}:
            self.inputs.append((attrs, self.current))

    def handle_endtag(self, tag):
        if tag == "form":
            self.current = None


class FavoriteIntegrationTests(FavoriteTestCase):
    def test_catalog_has_separate_csrf_protected_favorite_forms(self):
        response = self.client.get(reverse("listings:list"), {"category": "Top"})
        parser = FormParser(response.content.decode())
        self.assertFalse(parser.nested)
        forms = [form for form in parser.forms if "data-favorite-action" in form]
        self.assertEqual(len(forms), 1)
        self.assertEqual(forms[0]["action"], self.action_url("add"))
        self.assertEqual(forms[0]["method"], "post")
        self.assertEqual(forms[0]["hx-push-url"], "false")
        self.assertEqual(forms[0]["hx-swap"], "outerHTML")
        self.assertTrue(any(attrs.get("name") == "csrfmiddlewaretoken" and owner == forms[0]
                            for attrs, owner in parser.inputs))
        for name in ("q", "category", "sort"):
            attrs, owner = next((attrs, owner) for attrs, owner in parser.inputs if attrs.get("name") == name)
            self.assertTrue(attrs.get("form") == "catalog-filters" or owner.get("id") == "catalog-filters")

    def test_saved_state_is_private_on_catalog_detail_and_storefront(self):
        self.save_favorite()
        urls = [reverse("listings:list"), reverse("listings:detail", args=[self.listing.pk]),
                reverse("profiles:profile_public", args=[self.seller.pk])]
        for url in urls:
            with self.subTest(url=url):
                self.client.force_login(self.member)
                response = self.client.get(url)
                self.assertContains(response, 'aria-pressed="true"')
                self.assertIn("private", response["Cache-Control"])
                self.assertIn("Cookie", response["Vary"])
                self.client.force_login(self.other)
                self.assertNotContains(self.client.get(url), 'aria-pressed="true"')

    def test_guest_and_incomplete_profiles_get_login_or_onboarding_invite(self):
        for user, text in ((None, "Masuk untuk menyimpan favorit"),
                           (self.incomplete, "Lengkapi profil untuk menyimpan favorit")):
            self.client.logout()
            if user:
                self.client.force_login(user)
            response = self.client.get(reverse("listings:list"))
            self.assertContains(response, text)
            self.assertFalse(any("data-favorite-action" in form
                                 for form in FormParser(response.content.decode()).forms))

    def test_owner_has_no_save_button_for_own_listing(self):
        self.client.force_login(self.seller)
        response = self.client.get(reverse("listings:detail", args=[self.listing.pk]))
        self.assertNotContains(response, self.action_url("add"))

    def test_sold_saved_item_can_be_removed_but_unsaved_sold_has_no_add_button(self):
        self.save_favorite()
        Listing.objects.filter(pk=self.listing.pk).update(status=Listing.Status.SOLD)
        url = reverse("listings:detail", args=[self.listing.pk])
        self.assertContains(self.client.get(url), self.action_url("remove"))
        self.client.force_login(self.other)
        self.assertNotContains(self.client.get(url), self.action_url("add"))

    def test_htmx_button_add_and_remove_return_authoritative_state_and_event(self):
        for action, saved in (("add", True), ("add", True), ("remove", False), ("remove", False)):
            with self.subTest(action=action, saved=saved):
                response = self.client.post(self.action_url(action), {
                    "slot": "detail", "next": reverse("listings:detail", args=[self.listing.pk]),
                }, HTTP_HX_REQUEST="true")
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, f'id="favorite-detail-{self.listing.pk}"')
                self.assertContains(response, 'aria-pressed="' + str(saved).lower() + '"')
                event = json.loads(response["HX-Trigger"])["favoriteChanged"]
                self.assertEqual(event, {"listingId": self.listing.pk, "saved": saved})
                self.assertNotIn("HX-Push-Url", response)
                self.assertTemplateNotUsed(response, "base.html")

    def test_personalized_partial_also_has_saved_state(self):
        self.save_favorite()
        response = self.client.get(reverse("listings:list"), {"category": "Top"}, HTTP_HX_REQUEST="true")
        self.assertContains(response, 'aria-pressed="true"')
        self.assertTemplateNotUsed(response, "base.html")

    def test_status_uses_one_query_regardless_of_number_of_cards(self):
        url = reverse("listings:list")
        self.save_favorite()
        with CaptureQueriesContext(connection) as small:
            self.client.get(url)
        for i in range(10):
            create_listing(self.seller, title=f"Pakaian tambahan {i}")
        with CaptureQueriesContext(connection) as large:
            self.client.get(url)
        self.assertEqual(len(small), len(large))
        favorite_queries = [q for q in large if "favorites_favorite" in q["sql"]]
        self.assertEqual(len(favorite_queries), 1)

    def test_guest_does_not_query_favorites(self):
        self.client.logout()
        with CaptureQueriesContext(connection) as queries:
            self.client.get(reverse("listings:list"))
        self.assertFalse(any("favorites_favorite" in q["sql"] for q in queries))

    def test_storefront_query_count_does_not_grow_per_card(self):
        url = reverse("profiles:profile_public", args=[self.seller.pk])
        self.save_favorite()
        with CaptureQueriesContext(connection) as small:
            self.client.get(url)
        for i in range(6):
            create_listing(self.seller, title=f"Etalase tambahan {i}")
        with CaptureQueriesContext(connection) as large:
            self.client.get(url)
        self.assertEqual(len(small), len(large))

    def test_duplicate_inline_editors_have_distinct_field_ids(self):
        first = self.save_favorite()
        second = Favorite.objects.create(user=self.member, listing=create_listing(self.seller))
        for favorite in (first, second):
            response = self.client.get(reverse("favorites:edit", args=[favorite.pk]), HTTP_HX_REQUEST="true")
            self.assertContains(response, f'id="favorite-{favorite.pk}-note"')

    def test_navbar_links_to_real_favorites_route(self):
        self.assertContains(self.client.get(reverse("main:show_main")), 'href="/favorites/"')
