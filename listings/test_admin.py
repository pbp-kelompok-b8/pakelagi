from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from listings.models import Listing
from listings.test_detail import create_listing, make_user


class ListingAdminTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("admin1", password="Strong!9382")
        self.client.force_login(self.admin)
        self.seller = make_user("sari", "Sari Wulan")
        self.changelist = reverse("admin:listings_listing_changelist")

    def test_changelist_opens_and_shows_listings(self):
        create_listing(self.seller, title="Kemeja flanel kotak")
        response = self.client.get(self.changelist)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Kemeja flanel kotak")

    def test_hide_action_hides_only_the_selected_listings(self):
        target = create_listing(self.seller, title="Barang yang dilaporkan")
        other = create_listing(self.seller, title="Barang yang aman")
        response = self.client.post(self.changelist, {
            "action": "hide_listings", "_selected_action": [target.pk],
        })
        self.assertEqual(response.status_code, 302)
        target.refresh_from_db()
        other.refresh_from_db()
        self.assertEqual(target.status, Listing.Status.HIDDEN)
        self.assertEqual(other.status, Listing.Status.AVAILABLE)

    def test_hidden_by_moderation_disappears_from_the_public_site_but_the_seller_still_sees_it(self):
        listing = create_listing(self.seller, title="Barang yang dilaporkan")
        self.client.post(self.changelist, {"action": "hide_listings", "_selected_action": [listing.pk]})
        self.client.logout()
        self.assertNotContains(self.client.get(reverse("listings:list")), "Barang yang dilaporkan")
        self.assertEqual(self.client.get(reverse("listings:detail", args=[listing.pk])).status_code, 404)
        self.client.force_login(self.seller)
        mine = self.client.get(reverse("listings:mine"), {"status": "disembunyikan"})
        self.assertContains(mine, "Barang yang dilaporkan")

    def test_regular_members_cannot_use_the_admin(self):
        self.client.force_login(self.seller)
        self.assertEqual(self.client.get(self.changelist).status_code, 302)
