from datetime import datetime, timedelta, timezone

from django.contrib.auth.models import User
from django.test import TestCase

from listings.models import Listing
from listings.storefront import MAX_LOADED_PAGES, STOREFRONT_PAGE_SIZE
from listings.test_detail import create_listing, make_user
from profiles.models import Profile

# Tombol muat berbunyi "Muat 8 lagi" (angkanya berubah). Pola ini tidak ikut cocok dengan teks lain seperti "dipakai lagi".
LOAD_MORE = r"Muat \d+ lagi"


def make_listings(seller, count, prefix="Barang", **overrides):
    # Buat beberapa listing dengan judul berurutan: "Barang 01", "Barang 02", dst.
    listings = []
    for number in range(1, count + 1):
        title = f"{prefix} {number:02d}"
        listings.append(create_listing(seller, title=title, **overrides))
    return listings


def shown_titles(response):
    # Judul barang yang tampil di etalase (urutan di halaman), tanpa cuplikan Sold
    return [listing.title for listing in response.context["listings"]]


class StorefrontBase(TestCase):
    def setUp(self):
        self.seller = make_user("sari", "Sari Wulan")
        self.path = f"/profile/{self.seller.pk}/"

    def get(self, **params):
        return self.client.get(self.path, params)


class StorefrontCountTests(StorefrontBase):
    def test_counts_are_totals_per_status_and_exclude_hidden(self):
        make_listings(self.seller, 3)
        make_listings(self.seller, 2, status=Listing.Status.SOLD, prefix="Laku")
        make_listings(self.seller, 4, status=Listing.Status.HIDDEN, prefix="Disembunyikan")
        response = self.get()
        self.assertEqual((response.context["available_count"], response.context["sold_count"]), (3, 2))
        self.assertContains(response, "Dijual (3)")
        self.assertContains(response, "Terjual (2)")
        self.assertContains(response, "3 dijual")
        self.assertContains(response, "2 terjual")

    def test_hidden_listings_are_excluded_everywhere_even_for_the_owner(self):
        make_listings(self.seller, 2)
        make_listings(self.seller, 2, status=Listing.Status.HIDDEN, prefix="Disembunyikan")
        self.client.force_login(self.seller)
        for path in ("/profile/", self.path):
            for tab in ("dijual", "terjual"):
                with self.subTest(path=path, tab=tab):
                    response = self.client.get(path, {"tab": tab})
                    self.assertNotContains(response, "Disembunyikan 01")
                    self.assertEqual(response.context["available_count"], 2)
        self.assertEqual(len(self.client.get("/profile/").context["listings"]), 2)

    def test_counts_are_not_the_number_of_loaded_cards(self):
        make_listings(self.seller, 20)
        response = self.get()
        self.assertEqual(len(response.context["listings"]), STOREFRONT_PAGE_SIZE)
        self.assertContains(response, "Dijual (20)")
        self.assertContains(response, "20 pakaian menunggu dipakai lagi")

    def test_other_sellers_listings_never_leak_in(self):
        other = make_user("budi", "Budi")
        make_listings(self.seller, 1)
        make_listings(other, 3, prefix="Punya Budi")
        response = self.get()
        self.assertEqual(response.context["available_count"], 1)
        self.assertNotContains(response, "Punya Budi")

    def test_owner_and_visitor_see_the_same_listings(self):
        make_listings(self.seller, 3)
        visitor = self.get()
        self.client.force_login(self.seller)
        owner = self.client.get("/profile/")
        self.assertEqual(shown_titles(visitor), shown_titles(owner))

    def test_status_change_moves_the_listing_between_tabs(self):
        listing = create_listing(self.seller, title="Akan terjual")
        self.assertEqual(shown_titles(self.get()), ["Akan terjual"])
        listing.status = Listing.Status.SOLD
        listing.save()
        self.assertEqual(shown_titles(self.get()), [])
        self.assertEqual(shown_titles(self.get(tab="terjual")), ["Akan terjual"])


class StorefrontTabTests(StorefrontBase):
    def test_default_tab_is_for_sale_and_sold_has_its_own_tab(self):
        make_listings(self.seller, 2)
        make_listings(self.seller, 2, status=Listing.Status.SOLD, prefix="Laku")
        self.assertEqual(sorted(shown_titles(self.get())), ["Barang 01", "Barang 02"])
        self.assertEqual(sorted(shown_titles(self.get(tab="terjual"))), ["Laku 01", "Laku 02"])

    def test_sold_cards_carry_a_text_badge(self):
        create_listing(self.seller, title="Sudah laku", status=Listing.Status.SOLD)
        self.assertContains(self.get(tab="terjual"), 'tag tag-sold absolute top-3 left-3">Terjual</span>')

    def test_for_sale_cards_have_no_sold_badge(self):
        create_listing(self.seller, title="Masih dijual")
        self.assertNotContains(self.get(tab="dijual"), "tag-sold")

    def test_status_specific_empty_states(self):
        self.assertContains(self.get(), "Belum ada barang dijual")
        self.assertContains(self.get(tab="terjual"), "Belum ada barang terjual")
        create_listing(self.seller)
        self.assertNotContains(self.get(), "Belum ada barang dijual")
        self.assertContains(self.get(tab="terjual"), "Belum ada barang terjual")


class StorefrontCardTests(StorefrontBase):
    def test_card_shows_real_detail_link_and_listing_facts(self):
        listing = create_listing(
            self.seller, title="Wool-blend oversized coat", brand="COS", price=285000,
            size=Listing.Size.M, condition=Listing.Condition.LIKE_NEW, city="Bandung",
            image_url="https://example.com/coat.jpg",
        )
        response = self.get()
        self.assertContains(response, f'href="/listings/{listing.pk}/"')
        for text in ("Wool-blend oversized coat", "COS", "Rp 285.000", "Like New · Bandung"):
            with self.subTest(text=text):
                self.assertContains(response, text)
        self.assertContains(response, 'alt="Wool-blend oversized coat"')
        self.assertContains(response, 'onerror="this.remove()"')
        self.assertContains(response, "Foto tidak tersedia")

    def test_cards_do_not_link_to_the_seller_or_leak_private_contact(self):
        Profile.objects.filter(user=self.seller).update(
            contact_type="email", contact_value="rahasia@example.com", phone_number="+628123456789",
        )
        create_listing(self.seller)
        self.client.logout()
        # Potongan HTMX berisi hanya etalase (tanpa kotak kontak di sampingnya)
        section = self.client.get(self.path, HTTP_HX_REQUEST="true")
        self.assertNotContains(section, "rahasia@example.com")
        self.assertNotContains(section, "+628123456789")
        self.assertNotContains(section, f'href="/profile/{self.seller.pk}/"')
        full_page = self.get()
        self.assertNotContains(full_page, "rahasia@example.com")
        self.assertNotContains(full_page, "+628123456789")

    def test_listing_text_is_escaped(self):
        create_listing(self.seller, title="<script>alert(1)</script> blus", brand="<b>X</b>")
        response = self.get()
        self.assertNotContains(response, "<script>alert(1)</script>")
        self.assertContains(response, "&lt;script&gt;alert(1)&lt;/script&gt; blus")


class StorefrontLoadMoreTests(StorefrontBase):
    def test_load_more_counts_for_0_1_8_9_and_17_listings(self):
        # (jumlah barang, kartu di pemuatan pertama, tombol "Muat N lagi" atau None bila tidak ada)
        cases = [(0, 0, None), (1, 1, None), (8, 8, None), (9, 8, 1), (16, 8, 8), (17, 8, 8)]
        for total, expected_cards, expected_button in cases:
            with self.subTest(total=total):
                Listing.objects.filter(seller=self.seller).delete()
                make_listings(self.seller, total)
                response = self.get()
                self.assertEqual(len(response.context["listings"]), expected_cards)
                if expected_button is None:
                    self.assertNotRegex(response.content.decode(), LOAD_MORE)
                    self.assertFalse(response.context["has_more"])
                else:
                    self.assertContains(response, f"Muat {expected_button} lagi")

    def test_label_shows_the_exact_remainder_after_each_load(self):
        make_listings(self.seller, 17)
        expectations = [(1, 8, "Muat 8 lagi"), (2, 16, "Muat 1 lagi"), (3, 17, None)]
        for page, expected_cards, expected_label in expectations:
            with self.subTest(page=page):
                response = self.get(page=page)
                self.assertEqual(len(response.context["listings"]), expected_cards)
                if expected_label:
                    self.assertContains(response, expected_label)
                else:
                    self.assertNotRegex(response.content.decode(), LOAD_MORE)

    def test_loading_is_cumulative_so_any_page_url_restores_all_cards(self):
        make_listings(self.seller, 20)
        first = shown_titles(self.get())
        second = shown_titles(self.get(page=2))
        third = shown_titles(self.get(page=3))
        self.assertEqual(second[:8], first)           # kartu lama tetap ada dan urutannya sama
        self.assertEqual(third[:16], second)
        self.assertEqual((len(first), len(second), len(third)), (8, 16, 20))
        for titles in (first, second, third):
            self.assertEqual(len(titles), len(set(titles)))   # tidak ada kartu ganda

    def test_load_more_link_keeps_tab_and_sort_and_increments_the_page(self):
        make_listings(self.seller, 12, status=Listing.Status.SOLD)
        response = self.get(tab="terjual", sort="harga_terendah")
        self.assertEqual(response.context["more_query"], "tab=terjual&sort=harga_terendah&page=2")
        html = response.content.decode()
        self.assertIn('href="?tab=terjual&amp;sort=harga_terendah&amp;page=2"', html)
        self.assertIn('hx-get="?tab=terjual&amp;sort=harga_terendah&amp;page=2"', html)
        self.assertIn('hx-target="#storefront-listings"', html)
        self.assertIn('hx-swap="outerHTML"', html)
        self.assertIn('hx-push-url="true"', html)
        self.assertIn('hx-sync="this:drop"', html)   # klik berulang saat memuat diabaikan

    def test_error_message_is_ready_but_hidden_and_the_button_remains_a_plain_link(self):
        make_listings(self.seller, 9)
        html = self.get().content.decode()
        self.assertIn('id="storefront-error"', html)
        self.assertRegex(html, r'id="storefront-error" role="alert" hidden')
        self.assertIn("Barang yang sudah tampil tetap ada", html)
        self.assertIn("htmx:responseError", html)
        self.assertRegex(html, r'<a href="\?tab=dijual&amp;sort=terbaru&amp;page=2"')   # tetap bisa diklik tanpa JavaScript

    def test_switching_tab_or_sort_resets_the_loaded_position(self):
        make_listings(self.seller, 20)
        make_listings(self.seller, 3, status=Listing.Status.SOLD, prefix="Laku")
        response = self.get(page=3)
        self.assertEqual(response.context["available_tab_query"], "tab=dijual&sort=terbaru")
        self.assertEqual(response.context["sold_tab_query"], "tab=terjual&sort=terbaru")
        self.assertNotIn("page", response.context["sold_tab_query"])

    def test_huge_or_invalid_page_numbers_never_break_the_page(self):
        make_listings(self.seller, 17)
        for page in ("99999999999999999999", str(MAX_LOADED_PAGES + 1), "0", "-3", "abc", "", "1e3", "9" * 5000):
            with self.subTest(page=page[:20]):
                response = self.get(page=page)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(1 <= len(response.context["listings"]) <= 17)
        self.assertEqual(len(self.get(page="99999999999999999999").context["listings"]), 17)
        self.assertNotRegex(self.get(page="99999999999999999999").content.decode(), LOAD_MORE)


class StorefrontSortingTests(StorefrontBase):
    def test_newest_first_then_by_id(self):
        first, second, third = make_listings(self.seller, 3)
        self.assertEqual(shown_titles(self.get(sort="terbaru")), [third.title, second.title, first.title])

    def test_price_sorting_uses_id_as_a_stable_tiebreaker(self):
        prices = [50000, 30000, 50000, 10000, 30000]
        listings = [create_listing(self.seller, title=f"Barang {i}", price=price) for i, price in enumerate(prices)]
        expected_asc = [l.title for l in sorted(listings, key=lambda l: (l.price, l.pk))]
        expected_desc = [l.title for l in sorted(listings, key=lambda l: (-l.price, l.pk))]
        self.assertEqual(shown_titles(self.get(sort="harga_terendah")), expected_asc)
        self.assertEqual(shown_titles(self.get(sort="harga_tertinggi")), expected_desc)

    def test_sorting_is_consistent_across_loads_with_many_equal_prices(self):
        make_listings(self.seller, 20, price=75000)
        for sort in ("harga_terendah", "harga_tertinggi", "terbaru"):
            with self.subTest(sort=sort):
                full = shown_titles(self.get(sort=sort, page=3))
                self.assertEqual(shown_titles(self.get(sort=sort, page=1)), full[:8])
                self.assertEqual(shown_titles(self.get(sort=sort, page=2)), full[:16])
                self.assertEqual(len(set(full)), 20)

    def test_sold_tab_follows_the_same_sort_options(self):
        cheap = create_listing(self.seller, title="Laku murah", price=10000, status=Listing.Status.SOLD)
        pricey = create_listing(self.seller, title="Laku mahal", price=90000, status=Listing.Status.SOLD)
        self.assertEqual(shown_titles(self.get(tab="terjual", sort="harga_terendah")), [cheap.title, pricey.title])
        self.assertEqual(shown_titles(self.get(tab="terjual", sort="harga_tertinggi")), [pricey.title, cheap.title])

    def test_sort_choice_is_kept_in_the_dropdown_and_unknown_values_fall_back(self):
        self.assertContains(self.get(sort="harga_tertinggi"), 'value="harga_tertinggi" selected')
        self.assertContains(self.get(sort="ngawur"), 'value="terbaru" selected')


class StorefrontSoldPreviewTests(StorefrontBase):
    def make_sold(self, title, days_ago):
        listing = create_listing(self.seller, title=title, status=Listing.Status.SOLD)
        sold_at = datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc) - timedelta(days=days_ago)
        Listing.objects.filter(pk=listing.pk).update(sold_at=sold_at)
        return listing

    def preview_titles(self, response):
        return [listing.title for listing in response.context["sold_preview"]]

    def test_preview_has_at_most_four_latest_sold_by_sold_at(self):
        for number, days_ago in enumerate([5, 1, 9, 3, 7, 2], start=1):
            self.make_sold(f"Laku {number}", days_ago)
        response = self.get()
        self.assertEqual(self.preview_titles(response), ["Laku 2", "Laku 6", "Laku 4", "Laku 1"])

    def test_preview_orders_by_sold_at_and_not_by_creation_or_edit_time(self):
        old_but_sold_last = self.make_sold("Dibuat lebih dulu, terjual terakhir", days_ago=0)
        newer_but_sold_earlier = self.make_sold("Dibuat belakangan, terjual lebih dulu", days_ago=4)
        self.assertLess(old_but_sold_last.pk, newer_but_sold_earlier.pk)
        listing = Listing.objects.get(pk=newer_but_sold_earlier.pk)
        listing.title = "Judul diedit"      # mengedit tidak boleh menggeser urutan cuplikan
        listing.save()
        self.assertEqual(self.preview_titles(self.get())[0], "Dibuat lebih dulu, terjual terakhir")

    def test_ties_on_sold_at_are_broken_by_newest_id(self):
        first = self.make_sold("Kembar pertama", days_ago=2)
        second = self.make_sold("Kembar kedua", days_ago=2)
        self.assertEqual(self.preview_titles(self.get()), [second.title, first.title])

    def test_legacy_sold_listings_without_sold_at_go_last(self):
        no_date = create_listing(self.seller, title="Tanpa tanggal", status=Listing.Status.SOLD)
        Listing.objects.filter(pk=no_date.pk).update(sold_at=None)
        self.make_sold("Ada tanggal", days_ago=30)
        self.assertEqual(self.preview_titles(self.get()), ["Ada tanggal", "Tanpa tanggal"])

    def test_preview_exists_only_on_the_for_sale_tab_with_a_link_to_the_sold_tab(self):
        self.make_sold("Laku satu", 1)
        create_listing(self.seller, title="Masih dijual")
        on_sale = self.get()
        self.assertContains(on_sale, "Baru saja terjual")
        self.assertContains(on_sale, "Lihat semua terjual")
        self.assertContains(on_sale, 'href="?tab=terjual&amp;sort=terbaru"')
        sold_tab = self.get(tab="terjual")
        self.assertEqual(sold_tab.context["sold_preview"], [])
        self.assertNotContains(sold_tab, "Baru saja terjual")

    def test_no_preview_section_without_sold_listings(self):
        create_listing(self.seller)
        self.assertNotContains(self.get(), "Baru saja terjual")

    def test_preview_never_includes_hidden_or_available_or_other_sellers(self):
        other = make_user("budi", "Budi")
        create_listing(other, title="Laku milik Budi", status=Listing.Status.SOLD)
        create_listing(self.seller, title="Disembunyikan", status=Listing.Status.HIDDEN)
        create_listing(self.seller, title="Masih dijual")
        self.make_sold("Laku milikku", 1)
        self.assertEqual(self.preview_titles(self.get()), ["Laku milikku"])

    def test_preview_is_not_affected_by_the_sort_order(self):
        self.make_sold("Laku lama", 9)
        self.make_sold("Laku baru", 1)
        for sort in ("terbaru", "harga_terendah", "harga_tertinggi"):
            with self.subTest(sort=sort):
                self.assertEqual(self.preview_titles(self.get(sort=sort)), ["Laku baru", "Laku lama"])


class StorefrontHtmxTests(StorefrontBase):
    def test_htmx_request_returns_only_the_section_with_all_loaded_cards(self):
        make_listings(self.seller, 12)
        response = self.client.get(self.path, {"page": 2}, HTTP_HX_REQUEST="true")
        self.assertTemplateUsed(response, "profiles/listings.html")
        self.assertTemplateNotUsed(response, "profiles/detail.html")
        self.assertNotContains(response, "<!DOCTYPE html>")
        self.assertEqual(len(response.context["listings"]), 12)
        self.assertEqual(response.content.decode().count('id="storefront-listings"'), 1)
        self.assertNotRegex(response.content.decode(), LOAD_MORE)

    def test_history_restore_returns_the_full_document_with_every_loaded_card(self):
        make_listings(self.seller, 12)
        response = self.client.get(self.path, {"page": 2}, HTTP_HX_REQUEST="true", HTTP_HX_HISTORY_RESTORE_REQUEST="true")
        self.assertContains(response, "<!DOCTYPE html>")
        self.assertEqual(len(response.context["listings"]), 12)
        self.assertEqual(response.headers["Cache-Control"], "private, no-store")

    def test_plain_get_works_without_javascript_for_any_loaded_position(self):
        make_listings(self.seller, 20)
        response = self.get(tab="dijual", sort="harga_terendah", page=2)
        self.assertContains(response, "<!DOCTYPE html>")
        self.assertEqual(len(response.context["listings"]), 16)

    def test_missing_profile_is_still_not_found(self):
        self.assertEqual(self.client.get("/profile/99999/").status_code, 404)
