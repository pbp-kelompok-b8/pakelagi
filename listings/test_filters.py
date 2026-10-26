from django.http import QueryDict
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from listings.filters import (TAG_FIELDS, TAG_LABELS, build_querystring, get_catalog_filter, get_filter_chips,
                              is_filtered)
from listings.models import MAX_PRICE, Listing
from listings.test_detail import create_listing, make_user


def parse(qs=""):
    return get_catalog_filter(QueryDict(qs))


class CatalogFilterParsingTests(SimpleTestCase):
    def test_empty_query_is_default_and_not_filtered(self):
        catalog_filter = parse()
        self.assertEqual(catalog_filter, {
            "q": "", "category": "", "sizes": [], "conditions": [], "price_min": None, "price_max": None,
            "city": "", "tags": [], "sort": "terbaru",
        })
        self.assertFalse(is_filtered(catalog_filter))
        self.assertEqual(build_querystring(catalog_filter), "")

    def test_valid_values_are_parsed(self):
        f = parse("q=kemeja+flanel&category=Top&size=M&size=L&condition=Good&price_min=50000&price_max=200000"
                  "&city=Bandung&tag=local&tag=repairable&sort=harga_terendah")
        self.assertEqual(f["q"], "kemeja flanel")
        self.assertEqual(f["category"], "Top")
        self.assertEqual(f["sizes"], ["M", "L"])
        self.assertEqual(f["conditions"], ["Good"])
        self.assertEqual((f["price_min"], f["price_max"]), (50000, 200000))
        self.assertEqual(f["city"], "Bandung")
        self.assertEqual(f["tags"], ["repairable", "local"])
        self.assertEqual(f["sort"], "harga_terendah")
        self.assertTrue(is_filtered(f))

    def test_unknown_values_are_dropped(self):
        f = parse("category=Ngawur&size=XXXL&size=M&condition=Rusak&tag=hack&sort=acak")
        self.assertEqual(f["category"], "")
        self.assertEqual(f["sizes"], ["M"])
        self.assertEqual(f["conditions"], [])
        self.assertEqual(f["tags"], [])
        self.assertEqual(f["sort"], "terbaru")

    def test_sort_alone_does_not_count_as_a_filter(self):
        self.assertFalse(is_filtered(parse("sort=harga_tertinggi")))

    def test_every_single_filter_counts_as_a_filter(self):
        for qs in ("q=a", "category=Top", "size=M", "condition=Good", "price_min=0", "price_max=0", "city=Depok",
                   "tag=local"):
            with self.subTest(qs=qs):
                self.assertTrue(is_filtered(parse(qs)))

    def test_prices_are_clamped_and_garbage_is_ignored(self):
        for raw in ("abc", "", "1.5", "1e3", " ", "--5", "NaN"):
            with self.subTest(raw=raw):
                self.assertIsNone(parse(f"price_min={raw}")["price_min"])
        self.assertEqual(parse("price_min=-50")["price_min"], 0)
        self.assertEqual(parse("price_max=99999999999999999999")["price_max"], MAX_PRICE)

    def test_absurdly_long_number_does_not_crash(self):
        self.assertIsNone(parse("price_min=" + "9" * 5000)["price_min"])

    def test_reversed_price_range_is_swapped(self):
        f = parse("price_min=300000&price_max=100000")
        self.assertEqual((f["price_min"], f["price_max"]), (100000, 300000))

    def test_search_text_is_normalised_and_capped(self):
        self.assertEqual(parse("q=++kemeja+++flanel++")["q"], "kemeja flanel")
        self.assertEqual(len(parse("q=" + "a" * 500)["q"]), 100)

    def test_duplicate_values_are_collapsed_and_ordered_consistently(self):
        self.assertEqual(parse("size=L&size=M&size=L")["sizes"], ["M", "L"])
        self.assertEqual(build_querystring(parse("size=L&size=M")), build_querystring(parse("size=M&size=L")))

    def test_querystring_round_trips(self):
        original = parse("q=blazer&category=Outerwear&size=S&size=M&condition=Like+New&price_min=1000&city=Depok"
                         "&tag=upcycled&sort=harga_tertinggi")
        self.assertEqual(parse(build_querystring(original)), original)

    def test_querystring_adds_page_only_after_page_one(self):
        f = parse("size=M")
        self.assertEqual(build_querystring(f, page=1), "size=M")
        self.assertEqual(build_querystring(f, page=3), "size=M&page=3")

    def test_chips_remove_exactly_one_filter(self):
        f = parse("q=coat&size=M&size=L&price_max=200000&city=Bandung&tag=local")
        chips = get_filter_chips(f)
        self.assertEqual([label for label, _ in chips], ["“coat”", "M", "L", "Maks Rp 200.000", "Bandung", "Tersedia lokal"])
        without_m = dict(chips)["M"]
        self.assertEqual(without_m["sizes"], ["L"])
        self.assertEqual(without_m["city"], "Bandung")
        self.assertEqual(f["sizes"], ["M", "L"])   # filter aslinya tidak ikut berubah

    def test_tag_labels_match_the_model(self):
        # Label tag ditulis di dua tempat (filters.py dan models.py): keduanya harus selalu sama.
        for key, field in TAG_FIELDS.items():
            with self.subTest(tag=key):
                self.assertEqual(TAG_LABELS[key], Listing._meta.get_field(field).verbose_name)
        everything_on = Listing(is_repairable=True, is_upcycled=True, is_locally_available=True, extends_clothing_life=True)
        self.assertEqual(everything_on.sustainability_tags, [TAG_LABELS[key] for key in TAG_FIELDS])


class CatalogFilterBehaviourTests(TestCase):
    def setUp(self):
        self.seller = make_user("sari", "Sari")
        self.url = reverse("listings:list")

    def titles(self, qs=""):
        response = self.client.get(f"{self.url}?{qs}")
        self.assertEqual(response.status_code, 200)
        return [listing.title for listing in response.context["page"].object_list]

    def test_search_matches_title_or_brand_case_insensitively(self):
        create_listing(self.seller, title="Kemeja flanel kotak", brand="Zara")
        create_listing(self.seller, title="Celana panjang katun", brand="Uniqlo")
        self.assertEqual(self.titles("q=KEMEJA"), ["Kemeja flanel kotak"])
        self.assertEqual(self.titles("q=uniqlo"), ["Celana panjang katun"])
        self.assertEqual(self.titles("q=tidak+ada"), [])

    def test_every_search_word_must_match_title_or_brand(self):
        create_listing(self.seller, title="Kemeja flanel kotak", brand="Zara")
        create_listing(self.seller, title="Kemeja linen polos", brand="Zara")
        self.assertEqual(self.titles("q=zara+flanel"), ["Kemeja flanel kotak"])
        self.assertEqual(sorted(self.titles("q=kemeja+zara")), ["Kemeja flanel kotak", "Kemeja linen polos"])

    def test_search_treats_special_characters_as_plain_text(self):
        create_listing(self.seller, title="Diskon 50% kemeja baru")
        create_listing(self.seller, title="Kemeja_biasa tanpa diskon")
        self.assertEqual(self.titles("q=50%25"), ["Diskon 50% kemeja baru"])
        self.assertEqual(self.titles("q=%25"), ["Diskon 50% kemeja baru"])
        # "_" dan "%" bukan wildcard: "k_meja" tidak boleh cocok dengan "Kemeja", tetapi "a_b" cocok secara harfiah.
        self.assertEqual(self.titles("q=k_meja"), [])
        self.assertEqual(self.titles("q=a_b"), ["Kemeja_biasa tanpa diskon"])

    def test_category_filter(self):
        create_listing(self.seller, title="Atasan putih polos", category=Listing.Category.TOP)
        create_listing(self.seller, title="Rok plisket panjang", category=Listing.Category.BOTTOM)
        self.assertEqual(self.titles("category=Top"), ["Atasan putih polos"])
        self.assertEqual(self.titles("category=Modest+Wear"), [])

    def test_size_and_condition_accept_several_values(self):
        create_listing(self.seller, title="Barang ukuran M", size=Listing.Size.M, condition=Listing.Condition.GOOD)
        create_listing(self.seller, title="Barang ukuran L", size=Listing.Size.L, condition=Listing.Condition.FAIR)
        create_listing(self.seller, title="Barang ukuran XL", size=Listing.Size.XL, condition=Listing.Condition.LIKE_NEW)
        self.assertEqual(sorted(self.titles("size=M&size=L")), ["Barang ukuran L", "Barang ukuran M"])
        self.assertEqual(sorted(self.titles("condition=Good&condition=Like+New")), ["Barang ukuran M", "Barang ukuran XL"])
        self.assertEqual(self.titles("size=M&condition=Fair"), [])

    def test_price_range_is_inclusive(self):
        for price in (50000, 100000, 150000, 250000):
            create_listing(self.seller, title=f"Barang harga {price}", price=price)
        self.assertEqual(sorted(self.titles("price_min=100000&price_max=150000")),
                         ["Barang harga 100000", "Barang harga 150000"])
        self.assertEqual(self.titles("price_min=200000"), ["Barang harga 250000"])
        self.assertEqual(self.titles("price_max=50000"), ["Barang harga 50000"])

    def test_free_items_are_found_with_zero_minimum(self):
        create_listing(self.seller, title="Barang gratis", price=0)
        self.assertEqual(self.titles("price_min=0&price_max=0"), ["Barang gratis"])

    def test_city_filter_ignores_letter_case(self):
        create_listing(self.seller, title="Dari Bandung", city="Bandung")
        create_listing(self.seller, title="Dari Depok", city="Depok")
        self.assertEqual(self.titles("city=bandung"), ["Dari Bandung"])

    def test_sustainability_tags_must_all_match(self):
        create_listing(self.seller, title="Bisa diperbaiki saja", is_repairable=True, is_upcycled=False)
        create_listing(self.seller, title="Perbaiki dan upcycled", is_repairable=True, is_upcycled=True)
        self.assertEqual(sorted(self.titles("tag=repairable")), ["Bisa diperbaiki saja", "Perbaiki dan upcycled"])
        self.assertEqual(self.titles("tag=repairable&tag=upcycled"), ["Perbaiki dan upcycled"])

    def test_combined_filters(self):
        create_listing(self.seller, title="Cocok semua", category=Listing.Category.DRESS, size=Listing.Size.M,
                       condition=Listing.Condition.GOOD, price=120000, city="Bandung", is_locally_available=True)
        create_listing(self.seller, title="Salah ukuran", category=Listing.Category.DRESS, size=Listing.Size.S,
                       condition=Listing.Condition.GOOD, price=120000, city="Bandung")
        create_listing(self.seller, title="Terlalu mahal", category=Listing.Category.DRESS, size=Listing.Size.M,
                       condition=Listing.Condition.GOOD, price=900000, city="Bandung")
        create_listing(self.seller, title="Kota lain", category=Listing.Category.DRESS, size=Listing.Size.M,
                       condition=Listing.Condition.GOOD, price=120000, city="Depok")
        qs = "category=Dress&size=M&condition=Good&price_max=200000&city=Bandung&tag=local&q=cocok"
        self.assertEqual(self.titles(qs), ["Cocok semua"])

    def test_filters_never_expose_sold_or_hidden_listings(self):
        create_listing(self.seller, title="Masih dijual")
        create_listing(self.seller, title="Sudah laku", status=Listing.Status.SOLD)
        create_listing(self.seller, title="Disembunyikan", status=Listing.Status.HIDDEN)
        for qs in ("", "q=laku", "q=disembunyikan", "category=Top", "price_min=0"):
            with self.subTest(qs=qs):
                self.assertNotIn("Sudah laku", self.titles(qs))
                self.assertNotIn("Disembunyikan", self.titles(qs))

    def test_sorting(self):
        create_listing(self.seller, title="Tengah", price=100000)
        create_listing(self.seller, title="Murah", price=50000)
        create_listing(self.seller, title="Mahal", price=300000)
        self.assertEqual(self.titles("sort=harga_terendah"), ["Murah", "Tengah", "Mahal"])
        self.assertEqual(self.titles("sort=harga_tertinggi"), ["Mahal", "Tengah", "Murah"])
        self.assertEqual(self.titles("sort=terbaru"), ["Mahal", "Murah", "Tengah"])
        self.assertEqual(self.titles("sort=ngawur"), ["Mahal", "Murah", "Tengah"])

    def test_equal_prices_have_a_stable_order(self):
        first = create_listing(self.seller, title="Harga sama pertama", price=70000)
        second = create_listing(self.seller, title="Harga sama kedua", price=70000)
        # Pembeda tetap memakai ID naik pada kedua arah, jadi barang sama harga tidak pernah bertukar tempat antar halaman.
        self.assertEqual(self.titles("sort=harga_terendah"), [first.title, second.title])
        self.assertEqual(self.titles("sort=harga_tertinggi"), [first.title, second.title])

    def test_garbage_input_never_causes_a_server_error(self):
        create_listing(self.seller)
        garbage = [
            "q=%00", "q=%27%3B+DROP+TABLE+listings_listing%3B--", "price_min=99999999999999999999999",
            "price_max=-99999999999999999999999", "page=abc", "page=-5", "page=99999999999999999999",
            "size=%00", "city=%00", "category[]=Top", "tag=" + "x" * 5000, "q=" + "%E2%82%AC" * 500,
            "size=M&" * 200,
        ]
        for qs in garbage:
            with self.subTest(qs=qs[:60]):
                self.assertEqual(self.client.get(f"{self.url}?{qs}").status_code, 200)


class CatalogPaginationTests(TestCase):
    def setUp(self):
        self.seller = make_user("sari", "Sari")
        self.url = reverse("listings:list")
        for i in range(30):
            create_listing(self.seller, title=f"Barang nomor {i:02d}", price=1000 * (i + 1))

    def test_twelve_per_page(self):
        first = self.client.get(self.url)
        self.assertEqual(len(first.context["page"].object_list), 12)
        self.assertContains(first, "Menampilkan 1–12 dari 30")
        last = self.client.get(self.url + "?page=3")
        self.assertEqual(len(last.context["page"].object_list), 6)
        self.assertContains(last, "Menampilkan 25–30 dari 30")

    def test_pages_do_not_overlap_and_cover_everything(self):
        seen = []
        for number in (1, 2, 3):
            seen += [l.pk for l in self.client.get(f"{self.url}?page={number}").context["page"].object_list]
        self.assertEqual(len(seen), 30)
        self.assertEqual(len(set(seen)), 30)

    def test_out_of_range_and_invalid_pages_fall_back_gracefully(self):
        self.assertEqual(self.client.get(self.url + "?page=999").context["page"].number, 3)
        for bad in ("abc", "0", "-1", ""):
            with self.subTest(page=bad):
                self.assertEqual(self.client.get(f"{self.url}?page={bad}").context["page"].number, 1)

    def test_pagination_links_keep_search_and_filters(self):
        response = self.client.get(self.url + "?q=barang&sort=harga_tertinggi")
        self.assertContains(response, "q=barang&amp;sort=harga_tertinggi&amp;page=2")
        self.assertEqual(response.context["next_href"], "/listings/?q=barang&sort=harga_tertinggi&page=2")
        self.assertEqual(response.context["prev_href"], "")

    def test_pagination_is_hidden_when_one_page_is_enough(self):
        response = self.client.get(self.url + "?q=nomor+00")
        self.assertNotContains(response, 'aria-label="Halaman"')

    def test_filtered_results_are_counted_across_all_pages(self):
        response = self.client.get(self.url + "?price_max=20000")
        self.assertEqual(response.context["results_count"], 20)
        self.assertContains(response, "20 dari 30 pakaian")


class CatalogPageContentTests(TestCase):
    def setUp(self):
        self.seller = make_user("sari", "Sari")
        self.url = reverse("listings:list")

    def test_count_shows_only_total_when_not_filtered(self):
        create_listing(self.seller)
        create_listing(self.seller, title="Barang kedua yang tersedia")
        self.assertContains(self.client.get(self.url), "2 pakaian")
        self.assertNotContains(self.client.get(self.url), "dari 2 pakaian")

    def test_count_shows_filtered_of_total_when_filtered(self):
        create_listing(self.seller, title="Kemeja biru muda")
        create_listing(self.seller, title="Celana hitam polos")
        self.assertContains(self.client.get(self.url + "?q=kemeja"), "1 dari 2 pakaian")

    def test_active_filters_are_shown_as_removable_chips_and_inputs_are_prefilled(self):
        create_listing(self.seller, size=Listing.Size.M, condition=Listing.Condition.GOOD, city="Bandung")
        response = self.client.get(self.url + "?size=M&condition=Good&city=Bandung&price_max=200000&q=kemeja")
        self.assertContains(response, 'aria-label="Hapus filter M"')
        self.assertContains(response, 'aria-label="Hapus filter Maks Rp 200.000"')
        self.assertContains(response, 'name="size" value="M" checked')
        self.assertContains(response, 'name="condition" value="Good" checked')
        self.assertContains(response, 'value="200000"')
        self.assertContains(response, 'value="kemeja"')
        self.assertContains(response, "Hapus semua")

    def test_removing_a_chip_link_drops_only_that_filter(self):
        create_listing(self.seller, size=Listing.Size.M, city="Bandung")
        chips = dict(self.client.get(self.url + "?size=M&city=Bandung").context["chips"])
        self.assertEqual(chips["M"], "/listings/?city=Bandung")
        self.assertEqual(chips["Bandung"], "/listings/?size=M")

    def test_tabs_keep_other_filters_and_mark_the_active_category(self):
        create_listing(self.seller)
        response = self.client.get(self.url + "?category=Dress&size=M")
        tabs = {tab["label"]: tab for tab in response.context["tabs"]}
        self.assertTrue(tabs["Dress"]["active"])
        self.assertFalse(tabs["Semua"]["active"])
        self.assertEqual(tabs["Top"]["href"], "/listings/?category=Top&size=M")
        self.assertEqual(tabs["Semua"]["href"], "/listings/?size=M")
        self.assertContains(response, '<input type="hidden" name="category" value="Dress">')

    def test_city_options_come_from_available_listings_without_duplicates(self):
        create_listing(self.seller, city="Bandung")
        create_listing(self.seller, city="bandung")
        create_listing(self.seller, city="Depok")
        create_listing(self.seller, city="Kota rahasia hidden", status=Listing.Status.HIDDEN)
        create_listing(self.seller, city="Kota sold", status=Listing.Status.SOLD)
        cities = self.client.get(self.url).context["city_choices"]
        self.assertEqual(len(cities), 2)
        self.assertEqual(sorted(c.casefold() for c in cities), ["bandung", "depok"])

    def test_selected_city_is_marked_in_the_dropdown(self):
        create_listing(self.seller, city="Bandung")
        self.assertContains(self.client.get(self.url + "?city=bandung"), 'value="Bandung" selected')

    def test_price_presets_keep_other_filters(self):
        presets = dict(self.client.get(self.url + "?size=M").context["price_presets"])
        self.assertEqual(presets["< 100rb"], "/listings/?size=M&price_max=100000")
        self.assertEqual(presets["100–250rb"], "/listings/?size=M&price_min=100000&price_max=250000")
        self.assertEqual(presets["> 250rb"], "/listings/?size=M&price_min=250000")

    def test_empty_states_differ_for_empty_catalog_and_no_match(self):
        self.assertContains(self.client.get(self.url), "Belum ada pakaian di katalog")
        create_listing(self.seller)
        response = self.client.get(self.url + "?q=tidak+ada+yang+cocok")
        self.assertContains(response, "Tidak ada pakaian yang cocok")
        self.assertContains(response, "Hapus semua filter")
        self.assertNotContains(response, "Belum ada pakaian di katalog")

    def test_search_text_is_escaped_when_echoed_back(self):
        response = self.client.get(self.url, {"q": '"><script>alert(1)</script>'})
        self.assertNotContains(response, "<script>alert(1)</script>")
        self.assertContains(response, "&lt;script&gt;alert(1)&lt;/script&gt;")

    def test_filter_form_works_without_javascript(self):
        response = self.client.get(self.url)
        self.assertContains(response, '<form id="catalog-filters" method="get" action="/listings/"')
        self.assertContains(response, "Terapkan filter")


class CatalogHtmxTests(TestCase):
    def setUp(self):
        self.seller = make_user("sari", "Sari")
        self.url = reverse("listings:list")
        create_listing(self.seller, title="Kemeja flanel kotak")
        create_listing(self.seller, title="Celana panjang katun")

    def test_normal_request_returns_the_full_page(self):
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, "listings/list.html")
        self.assertContains(response, "<html")

    def test_htmx_request_returns_only_the_results_partial(self):
        response = self.client.get(self.url + "?q=kemeja", HTTP_HX_REQUEST="true")
        self.assertTemplateUsed(response, "listings/components/results.html")
        self.assertTemplateNotUsed(response, "listings/list.html")
        self.assertTemplateNotUsed(response, "base.html")
        self.assertContains(response, "Kemeja flanel kotak")
        self.assertNotContains(response, "Celana panjang katun")
        self.assertNotContains(response, "<html")
        self.assertNotContains(response, 'id="catalog-filters"')

    def test_htmx_response_updates_the_count_out_of_band(self):
        response = self.client.get(self.url + "?q=kemeja", HTTP_HX_REQUEST="true")
        self.assertContains(response, '<p id="catalog-count"')
        self.assertContains(response, 'hx-swap-oob="true">1 dari 2 pakaian</p>')

    def test_full_page_does_not_duplicate_the_count_element(self):
        self.assertEqual(self.client.get(self.url).content.decode().count('id="catalog-count"'), 1)

    def test_history_restore_gets_the_full_page(self):
        response = self.client.get(self.url, HTTP_HX_REQUEST="true", HTTP_HX_HISTORY_RESTORE_REQUEST="true")
        self.assertTemplateUsed(response, "listings/list.html")

    def test_response_varies_on_htmx_headers_so_caches_do_not_mix_them_up(self):
        vary = self.client.get(self.url)["Vary"]
        for header in ("HX-Request", "HX-History-Restore-Request"):
            self.assertIn(header, vary)

    def test_form_and_links_declare_htmx_behaviour(self):
        html = self.client.get(self.url).content.decode()
        self.assertIn('hx-get="/listings/"', html)
        self.assertIn('hx-target="#listing-results"', html)
        self.assertIn('hx-push-url="true"', html)
        self.assertIn('hx-trigger="change, submit, input changed delay:500ms from:#catalog-q"', html)
        self.assertIn('id="listing-results"', html)

    def test_partial_pagination_links_are_htmx_and_plain_links_at_once(self):
        for i in range(14):
            create_listing(self.seller, title=f"Barang tambahan {i:02d}")
        html = self.client.get(self.url, HTTP_HX_REQUEST="true").content.decode()
        self.assertIn('href="/listings/?page=2" hx-get="/listings/?page=2"', html)

    def test_htmx_catalog_is_still_get_only(self):
        self.assertEqual(self.client.post(self.url, HTTP_HX_REQUEST="true").status_code, 405)
