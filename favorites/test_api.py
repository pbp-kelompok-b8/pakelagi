from django.test import Client, TestCase

from favorites.models import Favorite
from listings.models import Listing
from listings.test_detail import create_listing, make_user


class FavoriteAPITests(TestCase):
    url = "/api/v1/favorites/"

    @classmethod
    def setUpTestData(cls):
        cls.member = make_user("member", "Member")
        cls.seller = make_user("seller", "Penjual")
        cls.listing = create_listing(cls.seller)

    def test_list_contains_only_my_visible_favorites(self):
        mine = Favorite.objects.create(user=self.member, listing=self.listing, note="Catatan saya")
        sold = Favorite.objects.create(user=self.member, listing=create_listing(self.seller, status=Listing.Status.SOLD))
        Favorite.objects.create(user=self.member, listing=create_listing(self.seller, status=Listing.Status.HIDDEN))
        Favorite.objects.create(user=self.seller, listing=self.listing, note="Catatan pengguna lain")
        self.client.force_login(self.member)

        response = self.client.get(self.url, HTTP_ACCEPT="application/json")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 2)
        self.assertEqual([item["id"] for item in data["results"]], [sold.pk, mine.pk])
        item = data["results"][1]
        self.assertEqual(item["note"], "Catatan saya")
        self.assertEqual(item["listing"], {
            "id": self.listing.pk, "title": self.listing.title, "price": self.listing.price,
            "category": self.listing.category, "image_url": self.listing.image_url, "status": Listing.Status.AVAILABLE,
        })
        self.assertNotIn("user", item)

    def test_api_requires_a_complete_profile_and_does_not_cache_private_data(self):
        guest = self.client.get(self.url)
        self.assertEqual(guest.status_code, 403)
        self.assertIn("detail", guest.json())
        self.client.force_login(make_user("incomplete"))
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.client.force_login(self.member)
        self.assertIn("no-store", self.client.get(self.url)["Cache-Control"])

    def test_filter_uses_category_value_and_paginates(self):
        for _ in range(21):
            listing = create_listing(self.seller, category=Listing.Category.MODEST_WEAR)
            Favorite.objects.create(user=self.member, listing=listing)
        Favorite.objects.create(user=self.member, listing=self.listing)
        self.client.force_login(self.member)

        first = self.client.get(self.url, {"category": "Modest Wear"}).json()
        self.assertEqual(first["count"], 21)
        self.assertEqual(len(first["results"]), 20)
        self.assertTrue(all(item["listing"]["category"] == "Modest Wear" for item in first["results"]))
        self.assertEqual(len(self.client.get(first["next"]).json()["results"]), 1)
        self.assertEqual(self.client.get(self.url, {"category": "not-a-category"}).status_code, 400)

    def test_create_is_idempotent_and_takes_owner_from_session(self):
        self.client.force_login(self.member)
        data = {"listing_id": self.listing.pk, "user": self.seller.pk}
        first = self.client.post(self.url, data, content_type="application/json")
        self.assertEqual(first.status_code, 201)
        favorite = Favorite.objects.get(user=self.member, listing=self.listing)
        self.assertEqual(first.json()["id"], favorite.pk)
        favorite.note = "Jangan timpa catatan ini"
        favorite.save()

        second = self.client.post(self.url, data, content_type="application/json")
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.json()["id"], favorite.pk)
        self.assertEqual(second.json()["note"], favorite.note)
        self.assertEqual(Favorite.objects.count(), 1)

    def test_create_rejects_unavailable_and_own_listings(self):
        self.client.force_login(self.member)
        sold = create_listing(self.seller, status=Listing.Status.SOLD)
        hidden = create_listing(self.seller, status=Listing.Status.HIDDEN)
        own = create_listing(self.member)
        for listing_id in (sold.pk, hidden.pk, own.pk, 99999):
            response = self.client.post(self.url, {"listing_id": listing_id}, content_type="application/json")
            self.assertEqual(response.status_code, 404)
        for data in ({}, {"listing_id": "invalid"}, {"listing_id": True}, {"listing_id": 0}):
            response = self.client.post(self.url, data, content_type="application/json")
            self.assertEqual(response.status_code, 400)
        self.assertFalse(Favorite.objects.exists())

    def test_post_metadata_describes_listing_id_input(self):
        self.client.force_login(self.member)
        response = self.client.options(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.json()["actions"]["POST"]), {"listing_id"})

    def test_detail_only_exposes_the_owners_visible_favorites(self):
        other = Favorite.objects.create(user=self.seller, listing=self.listing)
        hidden = Favorite.objects.create(user=self.member, listing=create_listing(self.seller, status=Listing.Status.HIDDEN))
        mine = Favorite.objects.create(user=self.member, listing=self.listing)
        self.client.force_login(self.member)

        response = self.client.get(f"{self.url}{mine.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], mine.pk)
        for favorite in (other, hidden):
            detail = f"{self.url}{favorite.pk}/"
            self.assertEqual(self.client.get(detail).status_code, 404)
            self.assertEqual(self.client.patch(detail, {"note": "other"}, content_type="application/json").status_code, 404)
        self.assertEqual(self.client.delete(f"{self.url}{other.pk}/").status_code, 404)

    def test_patch_validates_note_and_does_not_reassign_listing(self):
        favorite = Favorite.objects.create(user=self.member, listing=self.listing)
        other_listing = create_listing(self.seller)
        detail = f"{self.url}{favorite.pk}/"
        self.client.force_login(self.member)

        for note in ("x" * 1000, ""):
            response = self.client.patch(detail, {"note": note, "listing": other_listing.pk}, content_type="application/json")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["note"], note)
        too_long = self.client.patch(detail, {"note": "x" * 1001}, content_type="application/json")
        self.assertEqual(too_long.status_code, 400)
        favorite.refresh_from_db()
        self.assertEqual(favorite.note, "")
        self.assertEqual(favorite.listing_id, self.listing.pk)

    def test_owner_can_remove_a_favorite_even_after_listing_is_hidden(self):
        favorite = Favorite.objects.create(user=self.member, listing=self.listing)
        Listing.objects.filter(pk=self.listing.pk).update(status=Listing.Status.HIDDEN)
        self.client.force_login(self.member)

        response = self.client.delete(f"{self.url}{favorite.pk}/")
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Favorite.objects.filter(pk=favorite.pk).exists())

    def test_web_login_session_can_write_json_only_with_csrf(self):
        password = "local-test-password"
        self.member.set_password(password)
        self.member.save()
        client = Client(enforce_csrf_checks=True)
        login = "/accounts/login/"
        self.assertEqual(client.get(login).status_code, 200)
        response = client.post(login, {
            "username": self.member.username, "password": password,
            "csrfmiddlewaretoken": client.cookies["csrftoken"].value,
        })
        self.assertEqual(response.status_code, 302)
        data = {"listing_id": self.listing.pk}
        self.assertEqual(client.post(self.url, data, content_type="application/json").status_code, 403)
        response = client.post(self.url, data, content_type="application/json", HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value)
        self.assertEqual(response.status_code, 201)
