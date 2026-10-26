from decimal import Decimal
from unittest import mock

import requests
from django.core.cache import cache
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from listings import nominatim
from listings.forms import ListingForm
from listings.models import Listing
from listings.test_detail import create_listing, make_user
from listings.test_manage import valid_data

GET = "listings.nominatim.requests.get"


def results_of(query):
    # nominatim.search mengembalikan (results, status); helper ini mengambil salah satunya saja
    return nominatim.search(query)[0]


def status_of(query):
    return nominatim.search(query)[1]

COBLONG = {
    "category": "boundary", "type": "administrative", "name": "Coblong",
    "display_name": "Coblong, Kota Bandung, Jawa Barat, Indonesia", "lat": "-6.8848474", "lon": "107.6152496",
    "address": {"district": "Coblong", "city": "Kota Bandung", "state": "Jawa Barat", "country": "Indonesia"},
}
COBLONG_HAMLET = {
    "category": "place", "type": "hamlet", "name": "Coblong",
    "display_name": "Coblong, Sidomukti, Kabupaten Semarang, Jawa Tengah, 50665, Indonesia",
    "lat": "-7.2026623", "lon": "110.3854000",
    "address": {"hamlet": "Coblong", "village": "Sidomukti", "county": "Kabupaten Semarang",
                "state": "Jawa Tengah", "postcode": "50665", "country": "Indonesia"},
}


def reply(payload, status=200):
    response = mock.Mock()
    response.status_code = status
    response.json.return_value = payload
    return response


class NoRealNetworkMixin:
    """Setiap test mem-patch requests.get; test yang lupa akan gagal keras, bukan menghubungi Nominatim sungguhan."""

    def setUp(self):
        super().setUp()
        cache.clear()
        patcher = mock.patch(GET, side_effect=AssertionError("Test tidak boleh menghubungi internet"))
        self.get = patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(cache.clear)

    def expire_throttle(self):
        """Seolah satu detik sudah berlalu."""
        cache.delete(nominatim.THROTTLE_KEY)


class ParsingTests(NoRealNetworkMixin, SimpleTestCase):
    def test_district_result_gets_title_subtitle_and_rounded_coordinates(self):
        self.get.side_effect = None
        self.get.return_value = reply([COBLONG])
        results, status = nominatim.search("Coblong")
        self.assertEqual(status, nominatim.OK)
        self.assertEqual(results, [{
            "title": "Coblong, Kota Bandung", "subtitle": "Jawa Barat, Indonesia", "city": "Coblong, Kota Bandung",
            "lat": "-6.88", "lon": "107.62",
        }])

    def test_same_name_in_another_region_is_told_apart(self):
        self.get.side_effect = None
        self.get.return_value = reply([COBLONG, COBLONG_HAMLET])
        titles = [r["title"] for r in results_of("Coblong")]
        self.assertEqual(titles, ["Coblong, Kota Bandung", "Coblong, Kabupaten Semarang"])
        self.assertEqual(results_of("Coblong")[1]["subtitle"], "Jawa Tengah, Indonesia")

    def test_name_contained_in_region_is_not_repeated(self):
        self.get.side_effect = None
        item = {**COBLONG, "name": "Bandung", "address": {"city": "Kota Bandung", "state": "Jawa Barat"}}
        self.get.return_value = reply([item])
        self.assertEqual(results_of("Bandung")[0]["title"], "Kota Bandung")

    def test_missing_state_falls_back_to_country_only(self):
        self.get.side_effect = None
        item = {**COBLONG, "address": {"city": "Kota Bandung"}}
        self.get.return_value = reply([item])
        self.assertEqual(results_of("Coblong")[0]["subtitle"], "Indonesia")

    def test_streets_buildings_shops_and_houses_are_dropped(self):
        self.get.side_effect = None
        unwanted = [
            {**COBLONG, "category": "highway", "type": "residential"},
            {**COBLONG, "category": "building", "type": "house"},
            {**COBLONG, "category": "shop", "type": "clothes"},
            {**COBLONG, "category": "place", "type": "house"},
            {**COBLONG, "category": "amenity", "type": "restaurant"},
            {**COBLONG, "category": "place", "type": "isolated_dwelling"},
        ]
        self.get.return_value = reply(unwanted + [COBLONG])
        self.assertEqual([r["title"] for r in results_of("Coblong")], ["Coblong, Kota Bandung"])

    def test_coordinates_outside_indonesia_or_malformed_are_dropped(self):
        self.get.side_effect = None
        bad = [
            {**COBLONG, "lat": "51.5", "lon": "-0.12"},          # London
            {**COBLONG, "lat": "abc", "lon": "107.6"},
            {**COBLONG, "lat": "NaN", "lon": "107.6"},
            {**COBLONG, "lat": "Infinity", "lon": "107.6"},
            {**COBLONG, "lat": None, "lon": None},
            {k: v for k, v in COBLONG.items() if k != "lat"},
        ]
        self.get.return_value = reply(bad)
        self.assertEqual(results_of("Coblong"), [])

    def test_garbage_items_do_not_crash_the_parser(self):
        self.get.side_effect = None
        self.get.return_value = reply(["teks", 5, None, [], {}, {"category": "place"}, {**COBLONG, "address": "bukan dict"}])
        results, status = nominatim.search("Coblong")
        self.assertEqual(status, nominatim.OK)
        self.assertEqual(len(results), 1)  # hanya item terakhir yang masih valid (tanpa alamat)

    def test_duplicates_are_collapsed_and_results_capped_at_five(self):
        self.get.side_effect = None
        many = [
            {**COBLONG, "name": f"Tempat {i}", "address": {"city": f"Kota {i}", "state": "Jawa Barat"}}
            for i in range(8)
        ]
        self.get.return_value = reply([COBLONG, COBLONG] + many)
        results = results_of("Tempat")
        self.assertEqual(len(results), 5)
        self.assertEqual(len({r["title"] for r in results}), 5)

    def test_title_longer_than_the_city_column_is_cut_to_fit(self):
        self.get.side_effect = None
        item = {**COBLONG, "name": "N" * 150, "address": {"state": "Jawa Barat"}}
        self.get.return_value = reply([item])
        self.assertLessEqual(len(results_of("NNN")[0]["city"]), 100)

    def test_coordinate_helpers(self):
        self.assertEqual(nominatim.round_coordinate(Decimal("-6.8848474")), Decimal("-6.88"))
        self.assertIsNone(nominatim.parse_coordinate("NaN"))
        self.assertIsNone(nominatim.parse_coordinate("Infinity"))
        self.assertIsNone(nominatim.parse_coordinate(None))
        self.assertEqual(nominatim.parse_coordinate(" -6.9 "), Decimal("-6.9"))
        self.assertTrue(nominatim.is_in_indonesia(Decimal("-6.9"), Decimal("107.6")))
        self.assertTrue(nominatim.is_in_indonesia(Decimal("-8.65"), Decimal("115.22")))   # Denpasar
        self.assertTrue(nominatim.is_in_indonesia(Decimal("-2.53"), Decimal("140.72")))   # Jayapura
        self.assertFalse(nominatim.is_in_indonesia(Decimal("51.5"), Decimal("-0.12")))    # London
        self.assertFalse(nominatim.is_in_indonesia(Decimal("40.7"), Decimal("-74.0")))    # New York
        self.assertFalse(nominatim.is_in_indonesia(Decimal("-33.9"), Decimal("151.2")))   # Sydney
        self.assertFalse(nominatim.is_in_indonesia(Decimal("0"), Decimal("0")))           # titik (0, 0) = data kosong


class RequestTests(NoRealNetworkMixin, SimpleTestCase):
    def test_request_follows_the_usage_policy_and_the_spec(self):
        self.get.side_effect = None
        self.get.return_value = reply([COBLONG])
        nominatim.search("  Coblong   Bandung ")
        self.get.assert_called_once()
        args, kwargs = self.get.call_args
        self.assertEqual(args[0], "https://nominatim.openstreetmap.org/search")
        params = kwargs["params"]
        self.assertEqual(params["q"], "Coblong Bandung")
        self.assertEqual(params["format"], "jsonv2")
        self.assertEqual(params["countrycodes"], "id")
        self.assertEqual(params["limit"], nominatim.FETCH_LIMIT)
        self.assertIn("Pakelagi", kwargs["headers"]["User-Agent"])
        self.assertIn("github.com/pbp-kelompok-b8/pakelagi", kwargs["headers"]["User-Agent"])
        self.assertEqual(kwargs["timeout"], nominatim.REQUEST_TIMEOUT)

    @override_settings(NOMINATIM_URL="https://nominatim.example/search", NOMINATIM_USER_AGENT="Tes/1.0")
    def test_url_and_user_agent_can_be_configured(self):
        self.get.side_effect = None
        self.get.return_value = reply([])
        nominatim.search("Bandung")
        args, kwargs = self.get.call_args
        self.assertEqual(args[0], "https://nominatim.example/search")
        self.assertEqual(kwargs["headers"]["User-Agent"], "Tes/1.0")

    def test_query_is_capped_at_100_characters(self):
        self.get.side_effect = None
        self.get.return_value = reply([])
        nominatim.search("a" * 500)
        self.assertEqual(len(self.get.call_args.kwargs["params"]["q"]), 100)

    def test_unicode_query_is_sent_intact(self):
        self.get.side_effect = None
        self.get.return_value = reply([])
        nominatim.search("Yogyakarta — Kotagede ☕")
        self.assertEqual(self.get.call_args.kwargs["params"]["q"], "Yogyakarta — Kotagede ☕")

    def test_too_short_queries_make_no_request(self):
        for text in (None, "", " ", "a", "ab", "  a  b  "):
            with self.subTest(text=text):
                self.assertEqual(status_of(text), nominatim.SHORT)
        self.get.assert_not_called()


class CacheAndThrottleTests(NoRealNetworkMixin, SimpleTestCase):
    def test_same_query_is_served_from_cache_regardless_of_case_and_spacing(self):
        self.get.side_effect = None
        self.get.return_value = reply([COBLONG])
        first = nominatim.search("Coblong Bandung")
        second = nominatim.search("  coblong   BANDUNG ")
        self.assertEqual(first[0], second[0])   # first dan second berupa (results, status)
        self.assertEqual(self.get.call_count, 1)

    def test_empty_results_are_cached_too(self):
        self.get.side_effect = None
        self.get.return_value = reply([])
        nominatim.search("tidak ada tempat ini")
        self.expire_throttle()
        self.assertEqual(results_of("tidak ada tempat ini"), [])
        self.assertEqual(self.get.call_count, 1)

    def test_second_different_query_within_a_second_is_throttled_without_a_request(self):
        self.get.side_effect = None
        self.get.return_value = reply([COBLONG])
        nominatim.search("Coblong")
        results, status = nominatim.search("Dago")
        self.assertEqual(status, nominatim.THROTTLED)
        self.assertEqual(results, [])
        self.assertEqual(self.get.call_count, 1)

    def test_request_is_allowed_again_after_the_throttle_window(self):
        self.get.side_effect = None
        self.get.return_value = reply([COBLONG])
        nominatim.search("Coblong")
        self.expire_throttle()
        self.assertEqual(status_of("Dago"), nominatim.OK)
        self.assertEqual(self.get.call_count, 2)

    def test_throttled_query_is_not_cached_as_empty(self):
        self.get.side_effect = None
        self.get.return_value = reply([COBLONG])
        nominatim.search("Coblong")
        nominatim.search("Dago")  # throttled
        self.expire_throttle()
        self.assertEqual(len(results_of("Dago")), 1)


class FailureTests(NoRealNetworkMixin, SimpleTestCase):
    def test_network_errors_become_unavailable_and_are_not_cached(self):
        for error in (requests.ConnectionError(), requests.Timeout(), requests.RequestException("x")):
            with self.subTest(error=type(error).__name__):
                cache.clear()
                self.get.reset_mock()
                self.get.side_effect = error
                results, status = nominatim.search("Bandung")
                self.assertEqual((status, results), (nominatim.UNAVAILABLE, []))
                self.expire_throttle()
                self.get.side_effect = None
                self.get.return_value = reply([COBLONG])
                self.assertEqual(status_of("Bandung"), nominatim.OK)  # pulih setelah gangguan
                self.assertEqual(self.get.call_count, 2)

    def test_server_errors_are_unavailable_without_a_cooldown(self):
        self.get.side_effect = None
        self.get.return_value = reply([], status=500)
        self.assertEqual(status_of("Bandung"), nominatim.UNAVAILABLE)
        self.expire_throttle()
        self.get.return_value = reply([COBLONG])
        self.assertEqual(status_of("Dago"), nominatim.OK)

    def test_rate_limit_or_ban_response_starts_a_cooldown(self):
        for status in (429, 403):
            with self.subTest(status=status):
                cache.clear()
                self.get.reset_mock()
                self.get.side_effect = None
                self.get.return_value = reply([], status=status)
                self.assertEqual(status_of("Bandung"), nominatim.UNAVAILABLE)
                self.expire_throttle()
                self.assertEqual(status_of("Dago"), nominatim.UNAVAILABLE)
                self.assertEqual(self.get.call_count, 1)  # tidak ada permintaan lagi selama cooldown

    def test_cached_results_still_work_during_a_cooldown(self):
        self.get.side_effect = None
        self.get.return_value = reply([COBLONG])
        nominatim.search("Coblong")
        cache.set(nominatim.COOLDOWN_KEY, True, 60)
        self.assertEqual(status_of("Coblong"), nominatim.OK)

    def test_invalid_json_and_unexpected_payloads_are_unavailable(self):
        self.get.side_effect = None
        broken = reply(None)
        broken.json.side_effect = ValueError("bukan json")
        for response in (broken, reply({"error": "x"}), reply("teks"), reply(None)):
            with self.subTest():
                cache.clear()
                self.get.return_value = response
                self.assertEqual(status_of("Bandung"), nominatim.UNAVAILABLE)


class LocationSearchViewTests(NoRealNetworkMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse("listings:location_search")
        self.member = make_user("sari", "Sari")
        self.client.force_login(self.member)

    def ok(self, payload):
        self.get.side_effect = None
        self.get.return_value = reply(payload)

    def test_url_pattern(self):
        self.assertEqual(self.url, "/listings/location-search/")

    def test_guest_and_incomplete_members_are_forbidden_and_trigger_no_request(self):
        self.ok([COBLONG])
        for viewer in (None, make_user("budi"), make_user("kosong", " ")):
            with self.subTest(viewer=getattr(viewer, "username", "guest")):
                self.client.logout()
                if viewer:
                    self.client.force_login(viewer)
                self.assertEqual(self.client.get(self.url, {"city": "Coblong"}).status_code, 403)
        self.get.assert_not_called()

    def test_member_gets_suggestions_with_data_attributes_and_attribution(self):
        self.ok([COBLONG, COBLONG_HAMLET])
        response = self.client.get(self.url, {"city": "Coblong"})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "listings/components/location_results.html")
        self.assertContains(response, 'data-city="Coblong, Kota Bandung"')
        self.assertContains(response, 'data-lat="-6.88"')
        self.assertContains(response, 'data-lon="107.62"')
        self.assertContains(response, "Jawa Barat, Indonesia")
        self.assertContains(response, "OpenStreetMap contributors")
        self.assertContains(response, "Nominatim")
        self.assertNotContains(response, "<html")

    def test_response_is_private_and_not_stored(self):
        self.ok([COBLONG])
        header = self.client.get(self.url, {"city": "Coblong"})["Cache-Control"]
        self.assertIn("private", header)
        self.assertIn("no-store", header)

    def test_text_from_the_external_service_is_escaped(self):
        evil = {**COBLONG, "name": '"><script>alert(1)</script>', "address": {"state": '<img src=x onerror=alert(2)>'}}
        self.ok([evil])
        response = self.client.get(self.url, {"city": "Coblong"})
        self.assertNotContains(response, "<script>alert(1)</script>")
        self.assertNotContains(response, "<img src=x")
        self.assertNotContains(response, 'data-city=""><script>')

    def test_no_match_shows_the_manual_fallback_message(self):
        self.ok([])
        response = self.client.get(self.url, {"city": "Tempat Fiktif"})
        self.assertContains(response, "Ketik nama kota secara manual")
        self.assertNotContains(response, "location-option")

    def test_service_failure_shows_the_manual_fallback_message_not_an_error(self):
        self.get.side_effect = requests.ConnectionError()
        response = self.client.get(self.url, {"city": "Coblong"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "sedang tidak tersedia")
        self.assertContains(response, "listing tetap bisa terbit")
        self.assertNotContains(response, "Traceback")

    def test_throttled_response_retries_itself_after_a_moment(self):
        self.ok([COBLONG])
        self.client.get(self.url, {"city": "Coblong"})
        response = self.client.get(self.url, {"city": "Dago Pakar"})
        self.assertContains(response, "Mencari lokasi")
        self.assertContains(response, 'hx-trigger="load delay:1100ms"')
        self.assertContains(response, 'hx-get="/listings/location-search/?city=Dago%20Pakar"')
        self.assertEqual(self.get.call_count, 1)

    def test_retry_url_cannot_inject_markup(self):
        self.ok([COBLONG])
        self.client.get(self.url, {"city": "Coblong"})
        response = self.client.get(self.url, {"city": '"><script>alert(1)</script>'})
        self.assertNotContains(response, "<script>alert(1)</script>")

    def test_short_query_returns_an_empty_body_and_no_request(self):
        for text in ("", "a", "ab"):
            with self.subTest(text=text):
                response = self.client.get(self.url, {"city": text})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.content.strip(), b"")
        self.get.assert_not_called()

    def test_missing_parameter_does_not_crash(self):
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_only_get_is_allowed(self):
        self.assertEqual(self.client.post(self.url, {"city": "Coblong"}).status_code, 405)


class ListingFormLocationTests(NoRealNetworkMixin, TestCase):
    def test_valid_coordinates_are_saved_rounded(self):
        form = ListingForm(valid_data(latitude="-6.8848474", longitude="107.6152496"))
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual((form.cleaned_data["latitude"], form.cleaned_data["longitude"]),
                         (Decimal("-6.88"), Decimal("107.62")))

    def test_invalid_coordinates_are_dropped_silently_and_the_listing_is_still_valid(self):
        cases = [
            ("51.5", "-0.12"),           # London
            ("-33.9", "151.2"),          # Sydney
            ("0", "0"),
            ("-6.9", ""), ("", "107.6"), ("", ""),
            ("abc", "def"), ("NaN", "107.6"), ("-6.9", "Infinity"), ("1e999", "1e999"), ("--6", "107"),
        ]
        for lat, lon in cases:
            with self.subTest(lat=lat, lon=lon):
                form = ListingForm(valid_data(latitude=lat, longitude=lon))
                self.assertTrue(form.is_valid(), form.errors)
                self.assertIsNone(form.cleaned_data["latitude"])
                self.assertIsNone(form.cleaned_data["longitude"])

    def test_city_input_is_wired_for_htmx_suggestions(self):
        widget = ListingForm().fields["city"].widget.attrs
        self.assertEqual(widget["hx-get"], "/listings/location-search/")
        self.assertEqual(widget["hx-target"], "#location-results")
        self.assertEqual(widget["hx-trigger"], "input changed delay:500ms")
        self.assertEqual(widget["autocomplete"], "off")


class ListingCoordinatesFlowTests(NoRealNetworkMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.member = make_user("sari", "Sari")
        self.client.force_login(self.member)

    def test_create_page_has_hidden_fields_results_box_and_attribution(self):
        response = self.client.get(reverse("listings:create"))
        self.assertContains(response, 'type="hidden" name="latitude"')
        self.assertContains(response, 'type="hidden" name="longitude"')
        self.assertContains(response, 'id="location-results"')
        self.assertContains(response, "OpenStreetMap contributors")
        self.assertContains(response, "listing tetap bisa terbit")

    def test_footer_carries_the_openstreetmap_attribution_on_every_page(self):
        self.assertContains(self.client.get("/"), "OpenStreetMap contributors")

    def test_create_with_a_suggestion_stores_city_and_rounded_coordinates(self):
        self.client.post(reverse("listings:create"), valid_data(
            city="Coblong, Kota Bandung", latitude="-6.8848474", longitude="107.6152496"))
        listing = Listing.objects.get()
        self.assertEqual(listing.city, "Coblong, Kota Bandung")
        self.assertEqual((listing.latitude, listing.longitude), (Decimal("-6.88"), Decimal("107.62")))

    def test_create_with_a_manual_city_stores_no_coordinates(self):
        self.client.post(reverse("listings:create"), valid_data(city="Kota Kecil Manual"))
        listing = Listing.objects.get()
        self.assertEqual(listing.city, "Kota Kecil Manual")
        self.assertIsNone(listing.latitude)

    def test_forged_coordinates_outside_indonesia_are_ignored(self):
        self.client.post(reverse("listings:create"), valid_data(latitude="40.7", longitude="-74.0"))
        self.assertIsNone(Listing.objects.get().latitude)

    def test_editing_keeps_coordinates_when_city_is_unchanged(self):
        listing = create_listing(self.member, city="Coblong, Kota Bandung",
                                 latitude=Decimal("-6.88"), longitude=Decimal("107.62"))
        self.client.post(reverse("listings:edit", args=[listing.pk]), valid_data(
            city="Coblong, Kota Bandung", latitude="-6.88", longitude="107.62", title="Judul baru yang jelas"))
        listing.refresh_from_db()
        self.assertEqual((listing.latitude, listing.longitude), (Decimal("-6.88"), Decimal("107.62")))

    def test_editing_city_by_hand_discards_the_old_coordinates(self):
        listing = create_listing(self.member, city="Coblong, Kota Bandung",
                                 latitude=Decimal("-6.88"), longitude=Decimal("107.62"))
        self.client.post(reverse("listings:edit", args=[listing.pk]), valid_data(
            city="Depok", latitude="-6.88", longitude="107.62"))
        listing.refresh_from_db()
        self.assertEqual(listing.city, "Depok")
        self.assertIsNone(listing.latitude)
        self.assertIsNone(listing.longitude)

    def test_editing_city_with_a_new_suggestion_stores_the_new_coordinates(self):
        listing = create_listing(self.member, city="Coblong, Kota Bandung",
                                 latitude=Decimal("-6.88"), longitude=Decimal("107.62"))
        self.client.post(reverse("listings:edit", args=[listing.pk]), valid_data(
            city="Depok", latitude="-6.4025", longitude="106.7942"))
        listing.refresh_from_db()
        self.assertEqual((listing.latitude, listing.longitude), (Decimal("-6.40"), Decimal("106.79")))

    def test_edit_form_prefills_the_stored_coordinates(self):
        listing = create_listing(self.member, latitude=Decimal("-6.88"), longitude=Decimal("107.62"))
        response = self.client.get(reverse("listings:edit", args=[listing.pk]))
        self.assertContains(response, 'name="latitude"')
        self.assertContains(response, "-6.88")

    def test_coordinates_are_never_shown_on_public_pages(self):
        listing = create_listing(self.member, city="Coblong, Kota Bandung",
                                 latitude=Decimal("-6.88"), longitude=Decimal("107.62"))
        self.client.logout()
        for url in (reverse("listings:list"), reverse("listings:detail", args=[listing.pk])):
            with self.subTest(url=url):
                html = self.client.get(url).content.decode()
                self.assertNotIn("-6.88", html)
                self.assertNotIn("107.62", html)
                self.assertIn("Coblong, Kota Bandung", html)

    def test_suggested_city_label_works_as_a_catalog_filter(self):
        create_listing(self.member, title="Dari Coblong", city="Coblong, Kota Bandung")
        create_listing(self.member, title="Dari Depok", city="Depok")
        response = self.client.get(reverse("listings:list"), {"city": "coblong, kota bandung"})
        self.assertEqual([l.title for l in response.context["page"].object_list], ["Dari Coblong"])
        self.assertIn("Coblong, Kota Bandung", response.context["city_choices"])
