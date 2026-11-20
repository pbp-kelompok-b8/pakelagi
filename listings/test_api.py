from unittest import mock

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from favorites.models import Favorite
from listings.models import Listing
from listings.test_detail import create_listing, make_user
from profiles.models import Profile

LIST_URL = reverse("listings_api:list")
MINE_URL = reverse("listings_api:mine")
LOCATIONS_URL = reverse("listings_api:locations")


def detail_url(listing):
    return reverse("listings_api:detail", args=[listing.pk])


def status_url(listing):
    return reverse("listings_api:status", args=[listing.pk])


def valid_payload(**overrides):
    data = {
        "title": "Kemeja linen putih",
        "description": "Dipakai dua kali, tidak ada noda.",
        "category": "Top",
        "size": "M",
        "condition": "Good",
        "price": 120000,
        "image_url": "https://example.com/linen.jpg",
        "city": "Depok",
        "is_repairable": True,
        "is_upcycled": False,
    }
    data.update(overrides)
    return data


class CatalogAPITests(TestCase):
    def setUp(self):
        self.seller = make_user("sari", "Sari Wulan", contact_type="email", contact_value="sari@example.com")

    def test_guest_gets_only_available_listings_as_json(self):
        create_listing(self.seller, title="Masih dijual")
        create_listing(self.seller, title="Sudah laku", status=Listing.Status.SOLD)
        create_listing(self.seller, title="Disembunyikan", status=Listing.Status.HIDDEN)
        response = self.client.get(LIST_URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual([item["title"] for item in data["results"]], ["Masih dijual"])

    def test_card_has_public_fields_only(self):
        create_listing(self.seller, latitude="-6.40", longitude="106.82")
        item = self.client.get(LIST_URL).json()["results"][0]
        self.assertEqual(set(item), {
            "id", "title", "brand", "category", "size", "condition", "price", "image_url", "city",
            "status", "sustainability_tags", "is_favorited", "created_at",
        })
        self.assertNotIn("sari@example.com", self.client.get(LIST_URL).content.decode())

    def test_uses_the_same_filters_as_the_web_catalog(self):
        create_listing(self.seller, title="Kemeja M murah", size="M", price=50000)
        create_listing(self.seller, title="Kemeja L", size="L", price=50000)
        create_listing(self.seller, title="Kemeja M mahal", size="M", price=500000)
        data = self.client.get(LIST_URL, {"size": "M", "price_max": "100000"}).json()
        self.assertEqual([item["title"] for item in data["results"]], ["Kemeja M murah"])

    def test_sort_by_lowest_price(self):
        create_listing(self.seller, title="Mahal", price=300000)
        create_listing(self.seller, title="Murah", price=10000)
        data = self.client.get(LIST_URL, {"sort": "harga_terendah"}).json()
        self.assertEqual([item["title"] for item in data["results"]], ["Murah", "Mahal"])

    def test_paginates_twelve_per_page(self):
        for number in range(13):
            create_listing(self.seller, title=f"Pakaian nomor {number}")
        first = self.client.get(LIST_URL).json()
        self.assertEqual((first["count"], len(first["results"])), (13, 12))
        self.assertIsNotNone(first["next"])
        second = self.client.get(LIST_URL, {"page": 2}).json()
        self.assertEqual(len(second["results"]), 1)

    def test_page_out_of_range_is_404(self):
        self.assertEqual(self.client.get(LIST_URL, {"page": 5}).status_code, 404)

    def test_is_favorited_follows_the_logged_in_member(self):
        listing = create_listing(self.seller)
        buyer = make_user("budi", "Budi")
        Favorite.objects.create(user=buyer, listing=listing)
        self.assertFalse(self.client.get(LIST_URL).json()["results"][0]["is_favorited"])
        self.client.force_login(buyer)
        self.assertTrue(self.client.get(LIST_URL).json()["results"][0]["is_favorited"])

    def test_put_is_not_allowed(self):
        self.client.force_login(self.seller)
        self.assertEqual(self.client.put(LIST_URL, {}, content_type="application/json").status_code, 405)


class DetailAPITests(TestCase):
    def setUp(self):
        self.seller = make_user("sari", "Sari Wulan")
        self.listing = create_listing(self.seller, description="Kain adem", latitude="-6.40", longitude="106.82")

    def test_guest_sees_detail_with_seller_name(self):
        data = self.client.get(detail_url(self.listing)).json()
        self.assertEqual(data["description"], "Kain adem")
        self.assertEqual(data["seller"], {"id": self.seller.pk, "display_name": "Sari Wulan", "active_listings": 1})
        self.assertFalse(data["is_owner"])

    def test_seller_without_profile_gets_default_name(self):
        listing = create_listing(make_user("tanpa-profil"))
        self.assertEqual(self.client.get(detail_url(listing)).json()["seller"]["display_name"], "Penjual Pakelagi")

    def test_coordinates_are_only_shown_to_the_owner(self):
        guest = self.client.get(detail_url(self.listing)).json()
        self.assertIsNone(guest["latitude"])
        self.client.force_login(self.seller)
        owner = self.client.get(detail_url(self.listing)).json()
        self.assertEqual((owner["latitude"], owner["longitude"]), ("-6.400000", "106.820000"))
        self.assertTrue(owner["is_owner"])

    def test_unknown_listing_is_404(self):
        self.assertEqual(self.client.get(reverse("listings_api:detail", args=[999999])).status_code, 404)

    def test_hidden_listing_is_404_except_for_owner_and_staff(self):
        self.listing.status = Listing.Status.HIDDEN
        self.listing.save()
        self.assertEqual(self.client.get(detail_url(self.listing)).status_code, 404)
        self.client.force_login(make_user("budi", "Budi"))
        self.assertEqual(self.client.get(detail_url(self.listing)).status_code, 404)
        self.client.force_login(self.seller)
        self.assertEqual(self.client.get(detail_url(self.listing)).status_code, 200)
        self.client.force_login(User.objects.create_superuser("admin1", password="Strong!9382"))
        self.assertEqual(self.client.get(detail_url(self.listing)).status_code, 200)

    def test_sold_listing_is_still_readable(self):
        self.listing.status = Listing.Status.SOLD
        self.listing.save()
        self.assertEqual(self.client.get(detail_url(self.listing)).json()["status"], "Sold")


class CreateAPITests(TestCase):
    def setUp(self):
        self.member = make_user("sari", "Sari Wulan")

    def test_guest_and_incomplete_profile_cannot_create(self):
        self.assertEqual(self.client.post(LIST_URL, valid_payload(), content_type="application/json").status_code, 403)
        self.client.force_login(make_user("belum-lengkap"))
        self.assertEqual(self.client.post(LIST_URL, valid_payload(), content_type="application/json").status_code, 403)
        self.assertFalse(Listing.objects.exists())

    def test_member_creates_listing_and_seller_comes_from_the_session(self):
        other = make_user("budi", "Budi")
        self.client.force_login(self.member)
        payload = valid_payload(seller=other.pk, status="Hidden")
        response = self.client.post(LIST_URL, payload, content_type="application/json")
        self.assertEqual(response.status_code, 201)
        listing = Listing.objects.get()
        self.assertEqual(listing.seller, self.member)
        self.assertEqual(listing.status, Listing.Status.AVAILABLE)
        self.assertTrue(listing.is_repairable)
        self.assertEqual(response.json()["id"], listing.pk)
        self.assertTrue(response.json()["is_owner"])

    def test_form_encoded_body_is_accepted_too(self):
        self.client.force_login(self.member)
        response = self.client.post(LIST_URL, valid_payload(is_repairable="true"))
        self.assertEqual(response.status_code, 201)

    def test_uses_the_web_form_validation(self):
        self.client.force_login(self.member)
        response = self.client.post(
            LIST_URL, valid_payload(title="Abc", price=-5, city="Jl. Melati No. 5", category="Sepatu"),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(response.json()), {"title", "price", "city", "category"})
        self.assertFalse(Listing.objects.exists())

    def test_missing_required_fields(self):
        self.client.force_login(self.member)
        response = self.client.post(LIST_URL, {}, content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("title", response.json())

    def test_rejects_non_object_body_and_nested_values(self):
        self.client.force_login(self.member)
        self.assertEqual(self.client.post(LIST_URL, [1, 2], content_type="application/json").status_code, 400)
        response = self.client.post(LIST_URL, valid_payload(title=["a"]), content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("title", response.json())

    def test_coordinates_outside_indonesia_are_dropped(self):
        self.client.force_login(self.member)
        payload = valid_payload(latitude="51.5", longitude="-0.12")
        self.assertEqual(self.client.post(LIST_URL, payload, content_type="application/json").status_code, 201)
        self.assertIsNone(Listing.objects.get().latitude)

    def test_session_post_requires_csrf_token(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.member)
        response = client.post(LIST_URL, valid_payload(), content_type="application/json")
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Listing.objects.exists())


class UpdateDeleteAPITests(TestCase):
    def setUp(self):
        self.seller = make_user("sari", "Sari Wulan")
        self.listing = create_listing(self.seller, title="Judul lama", price=100000, is_upcycled=True)

    def patch(self, data):
        return self.client.patch(detail_url(self.listing), data, content_type="application/json")

    def test_owner_updates_only_the_sent_fields(self):
        self.client.force_login(self.seller)
        response = self.patch({"price": 75000})
        self.assertEqual(response.status_code, 200)
        self.listing.refresh_from_db()
        self.assertEqual((self.listing.price, self.listing.title, self.listing.is_upcycled), (75000, "Judul lama", True))
        self.assertEqual(response.json()["price"], 75000)

    def test_status_and_seller_cannot_be_changed_through_patch(self):
        self.client.force_login(self.seller)
        self.patch({"status": "Hidden", "seller": make_user("budi").pk})
        self.listing.refresh_from_db()
        self.assertEqual((self.listing.status, self.listing.seller), (Listing.Status.AVAILABLE, self.seller))

    def test_invalid_patch_changes_nothing(self):
        self.client.force_login(self.seller)
        response = self.patch({"title": "Ab"})
        self.assertEqual(response.status_code, 400)
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.title, "Judul lama")

    def test_other_member_gets_404_and_guest_gets_403(self):
        self.assertEqual(self.patch({"price": 1}).status_code, 403)
        self.client.force_login(make_user("budi", "Budi"))
        self.assertEqual(self.patch({"price": 1}).status_code, 404)
        self.assertEqual(self.client.delete(detail_url(self.listing)).status_code, 404)
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.price, 100000)

    def test_staff_can_edit_and_delete_like_on_the_web(self):
        admin = User.objects.create_superuser("admin1", password="Strong!9382")
        # API tetap meminta profil lengkap, jadi admin juga diberi profil
        Profile.objects.create(user=admin, display_name="Admin")
        self.client.force_login(admin)
        self.assertEqual(self.patch({"price": 90000}).status_code, 200)
        self.assertEqual(self.client.delete(detail_url(self.listing)).status_code, 204)

    def test_owner_deletes_listing(self):
        self.client.force_login(self.seller)
        response = self.client.delete(detail_url(self.listing))
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Listing.objects.filter(pk=self.listing.pk).exists())


class StatusAPITests(TestCase):
    def setUp(self):
        self.seller = make_user("sari", "Sari Wulan")
        self.listing = create_listing(self.seller)

    def post_status(self, value):
        return self.client.post(status_url(self.listing), {"status": value}, content_type="application/json")

    def test_owner_marks_sold_and_available_again(self):
        self.client.force_login(self.seller)
        response = self.post_status("Sold")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "Sold")
        self.listing.refresh_from_db()
        self.assertIsNotNone(self.listing.sold_at)
        self.assertEqual(self.post_status("Available").json()["status"], "Available")

    def test_invalid_status_is_400(self):
        self.client.force_login(self.seller)
        for value in ("Hidden", "", None, "sold"):
            with self.subTest(value=value):
                self.assertEqual(self.post_status(value).status_code, 400)

    def test_hidden_listing_cannot_be_reopened(self):
        self.listing.status = Listing.Status.HIDDEN
        self.listing.save()
        self.client.force_login(self.seller)
        self.assertEqual(self.post_status("Available").status_code, 409)
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.status, Listing.Status.HIDDEN)

    def test_only_the_owner_can_change_status(self):
        admin = User.objects.create_superuser("admin1", password="Strong!9382")
        Profile.objects.create(user=admin, display_name="Admin")
        self.client.force_login(admin)
        self.assertEqual(self.post_status("Sold").status_code, 404)

    def test_get_is_not_allowed(self):
        self.client.force_login(self.seller)
        self.assertEqual(self.client.get(status_url(self.listing)).status_code, 405)


class MineAPITests(TestCase):
    def setUp(self):
        self.seller = make_user("sari", "Sari Wulan")
        create_listing(self.seller, title="Tersedia")
        create_listing(self.seller, title="Terjual", status=Listing.Status.SOLD)
        create_listing(self.seller, title="Disembunyikan", status=Listing.Status.HIDDEN)
        create_listing(make_user("budi", "Budi"), title="Milik orang lain")

    def test_requires_complete_profile(self):
        self.assertEqual(self.client.get(MINE_URL).status_code, 403)

    def test_lists_only_own_listings_with_counts(self):
        self.client.force_login(self.seller)
        data = self.client.get(MINE_URL).json()
        self.assertEqual({item["title"] for item in data["results"]}, {"Tersedia", "Terjual", "Disembunyikan"})
        self.assertEqual(data["counts"], {"all": 3, "tersedia": 1, "terjual": 1, "disembunyikan": 1})
        self.assertEqual(data["status"], "")

    def test_status_tab_filters_but_counts_stay_complete(self):
        self.client.force_login(self.seller)
        data = self.client.get(MINE_URL, {"status": "terjual"}).json()
        self.assertEqual([item["title"] for item in data["results"]], ["Terjual"])
        self.assertEqual(data["counts"]["all"], 3)
        self.assertEqual(self.client.get(MINE_URL, {"status": "aneh"}).json()["count"], 3)


class LocationAPITests(TestCase):
    def test_requires_complete_profile(self):
        self.assertEqual(self.client.get(LOCATIONS_URL, {"city": "Depok"}).status_code, 403)

    def test_returns_nominatim_results(self):
        self.client.force_login(make_user("sari", "Sari Wulan"))
        result = {"title": "Depok", "subtitle": "Jawa Barat", "city": "Depok", "lat": "-6.40", "lon": "106.82"}
        with mock.patch("listings.nominatim.search", return_value=([result], "ok")) as search:
            data = self.client.get(LOCATIONS_URL, {"city": "  Depok   "}).json()
        search.assert_called_once_with("Depok")
        self.assertEqual((data["query"], data["status"], data["results"]), ("Depok", "ok", [result]))
        self.assertIn("OpenStreetMap", data["attribution"])
