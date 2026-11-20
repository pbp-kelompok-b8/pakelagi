from django.contrib.staticfiles import finders
from django.test import TestCase

from listings.models import Listing
from listings.test_detail import create_listing, make_user


class CategoryAPITests(TestCase):
    url = "/api/v1/categories/"

    def test_public_categories_count_only_available_listings(self):
        seller = make_user("seller")
        for status in Listing.Status.values:
            create_listing(seller, category=Listing.Category.MODEST_WEAR, status=status)

        with self.assertNumQueries(1):
            response = self.client.get(self.url, {"category": "Top"}, HTTP_ACCEPT="application/json")

        self.assertEqual(response.status_code, 200)
        categories = response.json()
        self.assertEqual([(item["value"], item["label"]) for item in categories], list(Listing.Category.choices))
        self.assertEqual([item["count"] for item in categories], [0, 0, 0, 0, 1])
        self.assertEqual(categories[-1], {
            "value": "Modest Wear",
            "label": "Modest Wear",
            "slug": "modest-wear",
            "count": 1,
            "image_url": "http://testserver/static/images/categories/modest-wear.svg",
            "image_mobile_url": "http://testserver/static/images/categories/modest-wear-mobile.svg",
        })

    def test_all_artwork_urls_resolve_to_local_assets(self):
        for category in self.client.get(self.url).json():
            for field in ("image_url", "image_mobile_url"):
                path = category[field].removeprefix("http://testserver/static/")
                self.assertIsNotNone(finders.find(path), category[field])

    def test_category_api_is_read_only(self):
        for method in ("post", "put", "patch", "delete"):
            self.assertEqual(getattr(self.client, method)(self.url).status_code, 405)
