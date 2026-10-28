from urllib.parse import parse_qs, urlsplit

from django.contrib.staticfiles import finders
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from listings.models import Listing
from listings.test_detail import create_listing, make_user


class CategoryPageTests(TestCase):
    def test_guest_can_open_dedicated_category_page(self):
        response = self.client.get("/categories/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "categories/index.html")

    def test_named_route_and_read_only_methods(self):
        url = reverse("main:category_index")
        self.assertEqual(url, "/categories/")
        for method in ("post", "put", "patch", "delete"):
            self.assertEqual(getattr(self.client, method)(url).status_code, 405)

    def test_member_and_incomplete_account_can_open_without_onboarding(self):
        for user in (make_user("member", "Member"), make_user("unfinished")):
            self.client.force_login(user)
            self.assertEqual(self.client.get("/categories/").status_code, 200)

    def test_empty_database_still_shows_five_official_categories_in_order(self):
        response = self.client.get("/categories/")
        cards = response.context["categories"]
        self.assertEqual([(card["value"], card["label"]) for card in cards], list(Listing.Category.choices))
        self.assertEqual([card["count"] for card in cards], [0] * 5)
        self.assertContains(response, "0 item", count=5)
        self.assertNotIn("Semua", [card["label"] for card in cards])

    def test_cards_count_only_available_listings(self):
        seller = make_user("seller", "Penjual")
        for index, category in enumerate(Listing.Category.values, start=1):
            for _ in range(index):
                create_listing(seller, category=category)
            for status in (Listing.Status.SOLD, Listing.Status.HIDDEN):
                create_listing(seller, category=category, status=status)
        cards = self.client.get("/categories/").context["categories"]
        self.assertEqual([card["count"] for card in cards], [1, 2, 3, 4, 5])

    def test_counts_refresh_after_status_changes_creation_and_deletion(self):
        listing = create_listing(make_user("seller"))

        def top_count():
            cards = self.client.get("/categories/").context["categories"]
            return next(card["count"] for card in cards if card["value"] == Listing.Category.TOP)

        self.assertEqual(top_count(), 1)
        for status, count in ((Listing.Status.SOLD, 0), (Listing.Status.HIDDEN, 0), (Listing.Status.AVAILABLE, 1)):
            Listing.objects.filter(pk=listing.pk).update(status=status)
            self.assertEqual(top_count(), count)
        listing.delete()
        self.assertEqual(top_count(), 0)

    def test_counts_match_full_catalog_not_one_page_or_previous_filters(self):
        seller = make_user("seller", "Penjual")
        for i in range(15):
            create_listing(seller, title=f"Atasan nomor {i}")
        cards = self.client.get("/categories/?category=Dress&size=XS&price_max=0&page=2").context["categories"]
        top = next(card for card in cards if card["value"] == Listing.Category.TOP)
        self.assertEqual(top["count"], 15)
        self.assertEqual(parse_qs(urlsplit(top["href"]).query), {"category": ["Top"]})
        response = self.client.get(top["href"])
        self.assertEqual(top["count"], response.context["results_count"])
        self.assertEqual(len(response.context["page"]), 12)

    def test_card_links_round_trip_all_categories_including_modest_wear(self):
        seller = make_user("seller", "Penjual")
        listings = {value: create_listing(seller, category=value) for value in Listing.Category.values}
        response = self.client.get("/categories/")
        for card in response.context["categories"]:
            with self.subTest(category=card["value"]):
                self.assertEqual(urlsplit(card["href"]).path, reverse("listings:list"))
                self.assertEqual(parse_qs(urlsplit(card["href"]).query), {"category": [card["value"]]})
                catalog = self.client.get(card["href"])
                self.assertEqual(list(catalog.context["page"]), [listings[card["value"]]])
                self.assertEqual([tab["label"] for tab in catalog.context["tabs"] if tab["active"]], [card["label"]])
        self.assertContains(response, "category=Modest+Wear")

    def test_empty_category_card_remains_linked_to_catalog_empty_state(self):
        response = self.client.get("/categories/")
        card = response.context["categories"][0]
        self.assertContains(response, f'href="{card["href"]}"')
        self.assertContains(self.client.get(card["href"]), "Tidak ada pakaian yang cocok")

    def test_one_grouped_count_query_instead_of_query_per_category(self):
        with CaptureQueriesContext(connection) as queries:
            self.client.get("/categories/")
        listing_queries = [query["sql"] for query in queries if "listings_listing" in query["sql"]]
        self.assertEqual(len(listing_queries), 1)
        self.assertIn("GROUP BY", listing_queries[0])

    def test_artwork_is_local_and_cards_are_plain_navigation_links(self):
        response = self.client.get("/categories/")
        for card in response.context["categories"]:
            self.assertTrue(card["image"].startswith("images/categories/"))
            self.assertIsNotNone(finders.find(card["image"]))
            self.assertContains(response, f'data-category="{card["value"]}"')
        self.assertNotContains(response, 'hx-target="#listing-results"')
        self.assertContains(response, '<a href="/listings/" class="btn btn-secondary">Lihat seluruh katalog')

    def test_category_page_does_not_expose_listing_details(self):
        create_listing(make_user("seller"), title="Judul privat yang tidak perlu", city="Kota rahasia",
                       description="Deskripsi bukan isi kartu kategori")
        response = self.client.get("/categories/")
        for text in ("Judul privat yang tidak perlu", "Kota rahasia", "Deskripsi bukan isi kartu kategori"):
            self.assertNotContains(response, text)

    def test_header_and_footer_link_to_category_page_instead_of_catalog_anchor(self):
        response = self.client.get(reverse("main:show_main"))
        self.assertContains(response, 'href="/categories/"', count=3)
        self.assertNotContains(response, 'href="/listings/#kategori"')

    def test_desktop_and_mobile_navigation_mark_only_category_route_active(self):
        active = 'href="/categories/" class="nav-link" aria-current="page">Kategori</a>'
        self.assertContains(self.client.get("/categories/"), active, count=2)
        self.assertNotContains(self.client.get(reverse("main:show_main")), active)
        self.assertNotContains(self.client.get(reverse("listings:list")), active)
