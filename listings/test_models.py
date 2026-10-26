from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase

from listings.models import Listing


def make_listing(seller, **overrides):
    data = {
        "seller": seller,
        "title": "Kemeja flanel kotak",
        "description": "Dipakai beberapa kali, masih rapi.",
        "category": Listing.Category.TOP,
        "size": Listing.Size.M,
        "condition": Listing.Condition.GOOD,
        "price": 85000,
        "image_url": "https://example.com/kemeja.jpg",
        "city": "Depok",
    }
    data.update(overrides)
    return Listing(**data)


class ListingModelTests(TestCase):
    def setUp(self):
        self.seller = User.objects.create_user("sari", password="Strong!9382")

    def test_valid_listing_is_saved_with_defaults(self):
        listing = make_listing(self.seller)
        listing.full_clean()
        listing.save()
        self.assertEqual(listing.status, Listing.Status.AVAILABLE)
        self.assertIsNone(listing.sold_at)
        self.assertFalse(listing.is_repairable)
        self.assertFalse(listing.is_upcycled)
        self.assertTrue(listing.is_locally_available)
        self.assertTrue(listing.extends_clothing_life)
        self.assertEqual(str(listing), "Kemeja flanel kotak")

    def test_negative_price_is_rejected(self):
        with self.assertRaises(ValidationError) as ctx:
            make_listing(self.seller, price=-1).full_clean()
        self.assertIn("price", ctx.exception.message_dict)

    def test_free_listing_with_zero_price_is_allowed(self):
        make_listing(self.seller, price=0).full_clean()

    def test_title_must_be_between_5_and_120_characters(self):
        for title in ("abcd", "x" * 121):
            with self.subTest(length=len(title)):
                with self.assertRaises(ValidationError) as ctx:
                    make_listing(self.seller, title=title).full_clean()
                self.assertIn("title", ctx.exception.message_dict)
        make_listing(self.seller, title="abcde").full_clean()
        make_listing(self.seller, title="x" * 120).full_clean()

    def test_image_url_only_accepts_http_and_https(self):
        for url in ("ftp://example.com/a.jpg", "javascript:alert(1)", "bukan-url", ""):
            with self.subTest(url=url):
                with self.assertRaises(ValidationError) as ctx:
                    make_listing(self.seller, image_url=url).full_clean()
                self.assertIn("image_url", ctx.exception.message_dict)
        for url in ("http://example.com/a.jpg", "https://example.com/a.jpg"):
            with self.subTest(url=url):
                make_listing(self.seller, image_url=url).full_clean()

    def test_choice_fields_reject_unknown_values(self):
        for field in ("category", "size", "condition", "status"):
            with self.subTest(field=field):
                with self.assertRaises(ValidationError) as ctx:
                    make_listing(self.seller, **{field: "Ngawur"}).full_clean()
                self.assertIn(field, ctx.exception.message_dict)

    def test_city_description_and_brand_rules(self):
        make_listing(self.seller, brand="").full_clean()
        for field in ("city", "description"):
            with self.subTest(field=field):
                with self.assertRaises(ValidationError) as ctx:
                    make_listing(self.seller, **{field: ""}).full_clean()
                self.assertIn(field, ctx.exception.message_dict)

    def test_coordinates_are_optional(self):
        listing = make_listing(self.seller)
        listing.full_clean()
        self.assertIsNone(listing.latitude)
        self.assertIsNone(listing.longitude)


class ListingSoldAtTests(TestCase):
    def setUp(self):
        self.seller = User.objects.create_user("sari", password="Strong!9382")

    def test_sold_at_is_set_when_status_changes_to_sold(self):
        listing = make_listing(self.seller)
        listing.save()
        listing.status = Listing.Status.SOLD
        listing.save()
        listing.refresh_from_db()
        self.assertIsNotNone(listing.sold_at)

    def test_sold_at_is_set_when_created_as_sold(self):
        listing = make_listing(self.seller, status=Listing.Status.SOLD)
        listing.save()
        self.assertIsNotNone(listing.sold_at)

    def test_editing_a_sold_listing_does_not_change_sold_at(self):
        listing = make_listing(self.seller)
        listing.save()
        listing.status = Listing.Status.SOLD
        listing.save()
        first = Listing.objects.get(pk=listing.pk).sold_at
        listing.title = "Judul baru yang lebih jelas"
        listing.save()
        self.assertEqual(Listing.objects.get(pk=listing.pk).sold_at, first)

    def test_selling_again_after_relisting_updates_sold_at(self):
        listing = make_listing(self.seller)
        listing.save()
        listing.status = Listing.Status.SOLD
        listing.save()
        first = Listing.objects.get(pk=listing.pk).sold_at
        listing.status = Listing.Status.AVAILABLE
        listing.save()
        listing.status = Listing.Status.SOLD
        listing.save()
        self.assertGreater(Listing.objects.get(pk=listing.pk).sold_at, first)

    def test_hidden_or_available_listing_has_no_sold_at(self):
        for status in (Listing.Status.AVAILABLE, Listing.Status.HIDDEN):
            with self.subTest(status=status):
                listing = make_listing(self.seller, status=status)
                listing.save()
                self.assertIsNone(listing.sold_at)

    def test_update_fields_save_still_records_sold_at(self):
        listing = make_listing(self.seller)
        listing.save()
        listing.status = Listing.Status.SOLD
        listing.save(update_fields=["status"])
        self.assertIsNotNone(Listing.objects.get(pk=listing.pk).sold_at)


class ListingRelationTests(TestCase):
    def test_default_ordering_is_newest_first_then_id(self):
        seller = User.objects.create_user("sari", password="Strong!9382")
        first = make_listing(seller, title="Listing pertama")
        first.save()
        second = make_listing(seller, title="Listing kedua")
        second.save()
        self.assertEqual(list(Listing.objects.all()), [second, first])

    def test_deleting_seller_removes_listings_and_related_name_works(self):
        seller = User.objects.create_user("sari", password="Strong!9382")
        make_listing(seller).save()
        self.assertEqual(seller.listings.count(), 1)
        seller.delete()
        self.assertEqual(Listing.objects.count(), 0)
