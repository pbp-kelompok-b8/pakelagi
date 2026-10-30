from urllib.parse import parse_qs, urlsplit

from django.test import TestCase
from django.urls import reverse

from listings.models import Listing
from listings.test_detail import create_listing, make_user


class CatalogCategoryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        seller = make_user("category-seller", "Penjual")
        cls.listings = {
            category: create_listing(seller, title=f"Pakaian {category}", category=category)
            for category in Listing.Category.values
        }
        create_listing(seller, title="Kategori terjual", status=Listing.Status.SOLD)
        create_listing(seller, title="Kategori tersembunyi", status=Listing.Status.HIDDEN)
        cls.url = reverse("listings:list")

    def test_all_and_unknown_categories_only_show_available_items(self):
        for category in ("", "unknown"):
            with self.subTest(category=category):
                response = self.client.get(self.url, {"category": category})
                self.assertSetEqual(
                    {item.pk for item in response.context["page"]},
                    {item.pk for item in self.listings.values()},
                )
                self.assertTrue(response.context["tabs"][0]["active"])

    def test_every_official_category_filters_and_marks_one_active_tab(self):
        for category, listing in self.listings.items():
            for headers in ({}, {"HTTP_HX_REQUEST": "true"}):
                with self.subTest(category=category, headers=headers):
                    response = self.client.get(self.url, {"category": category}, **headers)
                    self.assertEqual(list(response.context["page"]), [listing])
                    active = [tab["label"] for tab in response.context["tabs"] if tab["active"]]
                    self.assertEqual(active, [category])
                    self.assertContains(response, 'aria-current="page">' + category + "</a>")
                    self.assertNotContains(response, "Kategori tersembunyi")
                    self.assertNotContains(response, "Kategori terjual")

    def test_category_links_keep_all_other_filters_but_reset_page(self):
        params = {
            "category": "Top", "q": "pakaian", "size": ["M", "L"], "condition": "Good",
            "price_min": "100", "price_max": "200000", "city": "Depok", "tag": "local",
            "sort": "harga_terendah", "page": "3",
        }
        response = self.client.get(self.url, params)
        expected = {key: value if isinstance(value, list) else [value] for key, value in params.items()
                    if key not in {"page", "category"}}
        for tab in response.context["tabs"]:
            with self.subTest(tab=tab["label"]):
                query = parse_qs(urlsplit(tab["href"]).query)
                category = [] if tab["label"] == "Semua" else [tab["label"]]
                self.assertEqual(query.pop("category", []), category)
                self.assertEqual(query, expected)
                self.assertContains(response, f'href="{tab["href"].replace("&", "&amp;")}"')

    def test_modest_wear_link_round_trips_with_and_without_htmx(self):
        tabs = self.client.get(self.url).context["tabs"]
        href = next(tab["href"] for tab in tabs if tab["label"] == "Modest Wear")
        self.assertIn("category=Modest+Wear", href)
        for headers in ({}, {"HTTP_HX_REQUEST": "true"}, {
            "HTTP_HX_REQUEST": "true", "HTTP_HX_HISTORY_RESTORE_REQUEST": "true",
        }):
            with self.subTest(headers=headers):
                response = self.client.get(href, **headers)
                self.assertEqual(list(response.context["page"]), [self.listings["Modest Wear"]])
                template = "listings/components/results.html" if len(headers) == 1 else "listings/list.html"
                self.assertTemplateUsed(response, template)
                for header in ("HX-Request", "HX-History-Restore-Request", "Cookie"):
                    self.assertIn(header, response["Vary"])

    def test_empty_category_keeps_tabs_and_explains_no_matches(self):
        self.listings[Listing.Category.DRESS].delete()
        response = self.client.get(self.url, {"category": "Dress"}, HTTP_HX_REQUEST="true")
        self.assertContains(response, "Tidak ada pakaian yang cocok")
        self.assertContains(response, 'aria-label="Kategori"')
        self.assertContains(response, 'aria-current="page">Dress</a>')
        self.assertEqual(response.context["results_count"], 0)
