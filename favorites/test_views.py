from django.test import Client, TestCase
from django.urls import reverse

from favorites.models import Favorite
from listings.models import Listing
from listings.test_detail import create_listing, make_user


class FavoriteTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.seller = make_user("seller", "Penjual")
        cls.member = make_user("member", "Member")
        cls.other = make_user("other", "Lain")
        cls.incomplete = make_user("incomplete")
        cls.listing = create_listing(cls.seller)
        cls.list_url = reverse("favorites:list")

    def setUp(self):
        self.client.force_login(self.member)

    def action_url(self, action, listing=None):
        return reverse("favorites:" + action, args=[(listing or self.listing).pk])

    def save_favorite(self, **kwargs):
        return Favorite.objects.create(user=self.member, listing=self.listing, **kwargs)


class FavoriteViewTests(FavoriteTestCase):
    def test_add_is_idempotent_and_ignores_submitted_owner(self):
        for _ in range(2):
            response = self.client.post(self.action_url("add"), {"user": self.other.pk})
            self.assertRedirects(response, reverse("listings:detail", args=[self.listing.pk]))
        self.assertEqual(Favorite.objects.count(), 1)
        self.assertEqual(Favorite.objects.get().user_id, self.member.pk)

    def test_cannot_add_own_sold_hidden_or_missing_listing(self):
        own = create_listing(self.member)
        sold = create_listing(self.seller, status=Listing.Status.SOLD)
        hidden = create_listing(self.seller, status=Listing.Status.HIDDEN)
        for listing in (own, sold, hidden):
            with self.subTest(listing=listing.pk):
                self.assertEqual(self.client.post(self.action_url("add", listing)).status_code, 404)
        self.assertEqual(self.client.post(reverse("favorites:add", args=[99999])).status_code, 404)
        self.assertFalse(Favorite.objects.exists())

    def test_remove_is_idempotent_and_scoped_to_current_user(self):
        self.save_favorite()
        other = Favorite.objects.create(user=self.other, listing=self.listing)
        for _ in range(2):
            self.assertEqual(self.client.post(self.action_url("remove")).status_code, 302)
        self.assertQuerySetEqual(Favorite.objects.all(), [other])

    def test_remove_still_works_after_status_changes(self):
        for status in (Listing.Status.SOLD, Listing.Status.HIDDEN):
            with self.subTest(status=status):
                self.save_favorite()
                Listing.objects.filter(pk=self.listing.pk).update(status=status)
                self.assertEqual(self.client.post(self.action_url("remove")).status_code, 302)
                self.assertFalse(Favorite.objects.exists())

    def test_mutations_require_post(self):
        self.save_favorite()
        for action in ("add", "remove"):
            self.assertEqual(self.client.get(self.action_url(action)).status_code, 405)
        self.assertEqual(Favorite.objects.count(), 1)

    def test_mutations_require_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.member)
        favorite = self.save_favorite()
        for url in (self.action_url("add"), self.action_url("remove"),
                    reverse("favorites:edit", args=[favorite.pk])):
            self.assertEqual(client.post(url, {"note": "changed"}).status_code, 403)
        self.assertEqual(Favorite.objects.get().note, "")

    def test_guest_and_incomplete_profile_cannot_access_any_endpoint(self):
        favorite = self.save_favorite(note="Rahasia member")
        urls = [("get", self.list_url), ("get", reverse("favorites:edit", args=[favorite.pk])),
                ("post", self.action_url("add")), ("post", self.action_url("remove")),
                ("post", reverse("favorites:edit", args=[favorite.pk]))]
        for user, destination in ((None, reverse("accounts:login")),
                                  (self.incomplete, reverse("profiles:profile_create"))):
            self.client.logout()
            if user:
                self.client.force_login(user)
            for method, url in urls:
                with self.subTest(user=user, method=method, url=url):
                    response = getattr(self.client, method)(url)
                    self.assertEqual(response.status_code, 302)
                    self.assertTrue(response.url.startswith(destination + "?next="))
        self.assertEqual(Favorite.objects.get().note, "Rahasia member")

    def test_return_destination_rejects_external_and_auth_urls(self):
        for target in ("https://evil.example/", "//evil.example/", "javascript:alert(1)",
                       reverse("accounts:login")):
            with self.subTest(target=target):
                response = self.client.post(self.action_url("add"), {"next": target})
                self.assertRedirects(response, reverse("listings:detail", args=[self.listing.pk]))

    def test_safe_return_destination_preserves_category(self):
        target = reverse("listings:list") + "?category=Modest+Wear&size=M"
        self.assertRedirects(self.client.post(self.action_url("add"), {"next": target}), target)

    def test_list_is_private_and_sold_favorites_remain_visible(self):
        mine = self.save_favorite(note="Rahasia milik member")
        sold = create_listing(self.seller, title="Pakaian sudah terjual", status=Listing.Status.SOLD)
        saved_sold = Favorite.objects.create(user=self.member, listing=sold)
        other_listing = create_listing(self.seller, title="Hanya akun lain")
        Favorite.objects.create(user=self.other, listing=other_listing, note="Catatan akun lain")
        response = self.client.get(self.list_url)
        self.assertEqual(list(response.context["favorites"]), [saved_sold, mine])
        self.assertContains(response, "Rahasia milik member")
        self.assertContains(response, "Terjual")
        self.assertNotContains(response, "Catatan akun lain")
        self.assertNotContains(response, "Hanya akun lain")
        self.client.force_login(self.other)
        self.assertNotContains(self.client.get(self.list_url), "Rahasia milik member")

    def test_hidden_favorites_do_not_leak_details_or_counts(self):
        self.save_favorite(note="Catatan tersembunyi")
        Listing.objects.filter(pk=self.listing.pk).update(status=Listing.Status.HIDDEN)
        response = self.client.get(self.list_url)
        self.assertEqual(response.context["total_count"], 0)
        self.assertNotContains(response, self.listing.title)
        self.assertNotContains(response, self.listing.image_url)
        self.assertNotContains(response, "Catatan tersembunyi")
        self.assertContains(response, "Belum ada favorit")

    def test_hidden_partial_never_exposes_title_image_or_note(self):
        self.save_favorite(note="Catatan tersembunyi")
        Listing.objects.filter(pk=self.listing.pk).update(status=Listing.Status.HIDDEN)
        response = self.client.get(self.list_url, HTTP_HX_REQUEST="true")
        self.assertEqual(response.context["total_count"], 0)
        for secret in (self.listing.title, self.listing.image_url, "Catatan tersembunyi"):
            self.assertNotContains(response, secret)

    def test_category_filters_use_official_choices_and_unknown_means_all(self):
        top = self.save_favorite()
        dress = create_listing(self.seller, category=Listing.Category.DRESS)
        saved_dress = Favorite.objects.create(user=self.member, listing=dress)
        response = self.client.get(self.list_url, {"category": "Dress"})
        self.assertEqual(list(response.context["favorites"]), [saved_dress])
        self.assertEqual(response.context["total_count"], 2)
        self.assertContains(response, 'aria-current="page">Dress</a>')
        response = self.client.get(self.list_url, {"category": "unknown"})
        self.assertEqual(list(response.context["favorites"]), [saved_dress, top])

    def test_empty_states_distinguish_empty_list_and_empty_category(self):
        self.assertContains(self.client.get(self.list_url), "Belum ada favorit")
        self.save_favorite()
        response = self.client.get(self.list_url, {"category": "Dress"})
        self.assertContains(response, "Belum ada favorit di kategori ini")
        self.assertNotContains(response, "Belum ada favorit</")

    def test_every_category_works_on_full_and_partial_favorites_pages(self):
        expected = {}
        for category in Listing.Category.values:
            listing = create_listing(self.seller, category=category)
            expected[category] = Favorite.objects.create(user=self.member, listing=listing)
        for category, favorite in expected.items():
            for headers in ({}, {"HTTP_HX_REQUEST": "true"}):
                with self.subTest(category=category, headers=headers):
                    response = self.client.get(self.list_url, {"category": category}, **headers)
                    self.assertEqual(list(response.context["favorites"]), [favorite])
                    self.assertContains(response, 'aria-current="page">' + category + "</a>")

    def test_list_is_get_only(self):
        self.assertEqual(self.client.post(self.list_url).status_code, 405)

    def test_note_can_be_created_edited_and_cleared(self):
        favorite = self.save_favorite()
        url = reverse("favorites:edit", args=[favorite.pk])
        for note in ("Cek ukuran", "Tanyakan kondisi", ""):
            self.assertEqual(self.client.post(url, {"note": note}).status_code, 302)
            favorite.refresh_from_db()
            self.assertEqual(favorite.note, note)
            self.assertEqual(favorite.user_id, self.member.pk)
            self.assertEqual(favorite.listing_id, self.listing.pk)

    def test_note_form_only_allows_note_and_validates_length(self):
        favorite = self.save_favorite(note="Catatan awal")
        url = reverse("favorites:edit", args=[favorite.pk])
        response = self.client.post(url, {"note": "a" * 1001})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)
        favorite.refresh_from_db()
        self.assertEqual(favorite.note, "Catatan awal")
        self.client.post(url, {"note": "Baru", "user": self.other.pk, "listing": 99999})
        favorite.refresh_from_db()
        self.assertEqual(favorite.user_id, self.member.pk)
        self.assertEqual(favorite.listing_id, self.listing.pk)

    def test_other_user_cannot_read_or_edit_note_by_id(self):
        favorite = self.save_favorite(note="Rahasia member")
        self.client.force_login(self.other)
        url = reverse("favorites:edit", args=[favorite.pk])
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.post(url, {"note": "Dicuri"}).status_code, 404)
        favorite.refresh_from_db()
        self.assertEqual(favorite.note, "Rahasia member")

    def test_hidden_note_editor_does_not_expose_listing(self):
        favorite = self.save_favorite()
        Listing.objects.filter(pk=self.listing.pk).update(status=Listing.Status.HIDDEN)
        self.assertEqual(self.client.get(reverse("favorites:edit", args=[favorite.pk])).status_code, 404)

    def test_notes_are_escaped_on_list_and_editor(self):
        favorite = self.save_favorite(note="<script>alert(1)</script>")
        for url in (self.list_url, reverse("favorites:edit", args=[favorite.pk])):
            response = self.client.get(url)
            self.assertContains(response, "&lt;script&gt;alert(1)&lt;/script&gt;")
            self.assertNotContains(response, "<script>alert(1)</script>")
