from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from listings.models import Listing
from listings.nominatim import is_in_indonesia
from listings.seed_data import AVAILABLE, CITIES, SAMPLE_USERNAME_PREFIX, SELLERS, SOLD
from listings.test_detail import create_listing, make_user
from listings.validators import validate_http_url, validate_no_home_address
from profiles.models import Profile


def run_seed(*args):
    output = StringIO()
    call_command("seed_listings", *args, stdout=output)
    return output.getvalue()


class SeedDataTests(TestCase):
    # Memeriksa isi data contoh: cukup, bervariasi, valid, dan tidak mengandung data pribadi.

    def test_there_are_at_least_fifty_available_listings_ten_per_category(self):
        self.assertGreaterEqual(len(AVAILABLE), 50)
        for category in Listing.Category.values:
            with self.subTest(category=category):
                self.assertEqual(len([row for row in AVAILABLE if row["category"] == category]), 10)

    def test_there_are_sold_listings_for_the_profile_storefront_preview(self):
        self.assertGreaterEqual(len(SOLD), 8)
        for key in SELLERS:
            with self.subTest(seller=key):
                self.assertGreaterEqual(len([row for row in SOLD if row["seller"] == key]), 1)
        for row in SOLD:
            self.assertIsNotNone(row["sold_days_ago"])
        for row in AVAILABLE:
            self.assertIsNone(row["sold_days_ago"])

    def test_every_row_is_valid_for_the_model(self):
        for row in AVAILABLE + SOLD:
            with self.subTest(title=row["title"]):
                self.assertIn(row["category"], Listing.Category.values)
                self.assertIn(row["size"], Listing.Size.values)
                self.assertIn(row["condition"], Listing.Condition.values)
                self.assertIn(row["seller"], SELLERS)
                self.assertIn(row["city"], CITIES)
                self.assertTrue(5 <= len(row["title"]) <= 120)
                self.assertTrue(row["description"].strip())
                self.assertGreaterEqual(row["price"], 0)
                self.assertEqual(row["price"] % 5000, 0)   # harga bulat seperti harga sungguhan

    def test_titles_are_unique_per_seller_so_rerunning_never_duplicates(self):
        keys = [(row["seller"], row["title"]) for row in AVAILABLE + SOLD]
        self.assertEqual(len(keys), len(set(keys)))

    def test_every_image_url_is_valid_and_unique_enough_to_look_varied(self):
        urls = [row["image_url"] for row in AVAILABLE + SOLD]
        for url in urls:
            validate_http_url(url)
            self.assertTrue(url.startswith("https://images.unsplash.com/photo-"))
        self.assertGreaterEqual(len(set(urls)), 30)

    def test_cities_are_general_areas_with_coordinates_inside_indonesia(self):
        from decimal import Decimal
        for key, (label, lat, lon) in CITIES.items():
            with self.subTest(city=key):
                validate_no_home_address(label)
                self.assertTrue(is_in_indonesia(Decimal(lat), Decimal(lon)))
                self.assertEqual(Decimal(lat), Decimal(lat).quantize(Decimal("0.01")))   # sudah dibulatkan ~1 km
                self.assertLessEqual(len(label), 100)

    def test_the_data_has_real_variety(self):
        rows = AVAILABLE
        self.assertEqual({row["size"] for row in rows}, set(Listing.Size.values))   # XS sampai XXL dan Free Size
        self.assertEqual({row["condition"] for row in rows}, set(Listing.Condition.values))
        self.assertGreaterEqual(len({row["city"] for row in rows}), 10)
        self.assertGreaterEqual(len({row["brand"] for row in rows}), 15)
        prices = [row["price"] for row in rows]
        self.assertLessEqual(min(prices), 50000)
        self.assertGreaterEqual(max(prices), 400000)
        for flag in ("is_repairable", "is_upcycled", "is_locally_available", "extends_clothing_life"):
            with self.subTest(flag=flag):
                self.assertTrue(any(row[flag] for row in rows))
                self.assertTrue(any(not row[flag] for row in rows))
        self.assertTrue(any(row["brand"] == "" for row in rows))   # tidak semua barang bermerek

    def test_every_seller_has_the_same_number_of_available_listings(self):
        for key in SELLERS:
            with self.subTest(seller=key):
                self.assertEqual(len([row for row in AVAILABLE if row["seller"] == key]), 10)

    def test_seed_contains_no_personal_contact_data(self):
        text = " ".join(
            [row["description"] for row in AVAILABLE + SOLD]
            + [bio for _, bio in SELLERS.values()]
        )
        for forbidden in ("@gmail", "@yahoo", "wa.me", "instagram.com", "+62", "08123", "http"):
            self.assertNotIn(forbidden, text)


class SeedCommandTests(TestCase):
    def test_creates_sellers_profiles_and_listings(self):
        output = run_seed()
        self.assertIn("Selesai", output)
        self.assertEqual(User.objects.filter(username__startswith=SAMPLE_USERNAME_PREFIX).count(), 5)
        self.assertEqual(Profile.objects.filter(user__username__startswith=SAMPLE_USERNAME_PREFIX).count(), 5)
        self.assertEqual(Listing.objects.filter(status=Listing.Status.AVAILABLE).count(), 50)
        self.assertEqual(Listing.objects.filter(status=Listing.Status.SOLD).count(), 10)
        self.assertEqual(Listing.objects.count(), 60)

    def test_ten_available_listings_per_category(self):
        run_seed()
        for category in Listing.Category.values:
            with self.subTest(category=category):
                self.assertEqual(Listing.objects.filter(category=category, status=Listing.Status.AVAILABLE).count(), 10)

    def test_every_saved_listing_passes_model_validation(self):
        run_seed()
        for listing in Listing.objects.all():
            with self.subTest(title=listing.title):
                listing.full_clean()

    def test_running_it_again_does_not_duplicate_anything(self):
        run_seed()
        first_ids = sorted(Listing.objects.values_list("pk", flat=True))
        output = run_seed()
        self.assertIn("0 listing baru, 60 diperbarui", output)
        self.assertEqual(Listing.objects.count(), 60)
        self.assertEqual(User.objects.filter(username__startswith=SAMPLE_USERNAME_PREFIX).count(), 5)
        self.assertEqual(Profile.objects.count(), 5)
        self.assertEqual(sorted(Listing.objects.values_list("pk", flat=True)), first_ids)   # id tetap sama

    def test_running_it_many_times_stays_stable(self):
        for _ in range(3):
            run_seed()
        self.assertEqual(Listing.objects.count(), 60)

    def test_rerun_restores_edited_sample_listings(self):
        run_seed()
        listing = Listing.objects.get(title="Kemeja flanel kotak merah")
        listing.price = 1
        listing.save()
        run_seed()
        listing.refresh_from_db()
        self.assertEqual(listing.price, 85000)

    def test_sample_accounts_cannot_log_in_and_are_not_staff(self):
        run_seed()
        for user in User.objects.filter(username__startswith=SAMPLE_USERNAME_PREFIX):
            with self.subTest(user=user.username):
                self.assertFalse(user.has_usable_password())
                self.assertFalse(user.is_staff)
                self.assertFalse(user.is_superuser)
                self.assertFalse(self.client.login(username=user.username, password=""))
                self.assertFalse(self.client.login(username=user.username, password=user.username))

    def test_sample_profiles_are_complete_and_use_only_reserved_example_contacts(self):
        run_seed()
        for profile in Profile.objects.all():
            with self.subTest(profile=profile.display_name):
                self.assertTrue(profile.display_name.strip())
                self.assertEqual(profile.contact_type, "email")
                self.assertTrue(profile.contact_value.endswith("@example.com"))
                self.assertEqual(profile.phone_number, "")
                self.assertIn("Akun contoh", profile.bio)

    def test_sold_listings_have_sold_dates_and_available_ones_do_not(self):
        run_seed()
        for listing in Listing.objects.filter(status=Listing.Status.SOLD):
            self.assertIsNotNone(listing.sold_at)
        for listing in Listing.objects.filter(status=Listing.Status.AVAILABLE):
            self.assertIsNone(listing.sold_at)

    def test_creation_dates_are_spread_out(self):
        run_seed()
        days = {listing.created_at.date() for listing in Listing.objects.all()}
        self.assertGreaterEqual(len(days), 15)

    def test_coordinates_are_saved_rounded_and_inside_indonesia(self):
        run_seed()
        for listing in Listing.objects.all():
            with self.subTest(title=listing.title):
                self.assertTrue(is_in_indonesia(listing.latitude, listing.longitude))

    def test_reset_rebuilds_sample_data_but_never_touches_real_users(self):
        run_seed()
        real_seller = make_user("penjual_asli", "Penjual Asli")
        real_listing = create_listing(real_seller, title="Barang milik pengguna asli")
        sample_user = User.objects.get(username="sample_nina")
        extra = create_listing(sample_user, title="Tambahan lain milik akun contoh")
        self.assertEqual(Listing.objects.count(), 62)

        output = run_seed("--reset")
        self.assertIn("Reset: 61 listing akun contoh dihapus", output)   # 60 listing kelima akun contoh + 1 tambahan
        self.assertFalse(Listing.objects.filter(pk=extra.pk).exists())
        self.assertTrue(Listing.objects.filter(pk=real_listing.pk).exists())
        self.assertEqual(Listing.objects.filter(seller=real_seller).count(), 1)
        self.assertEqual(Listing.objects.count(), 61)
        self.assertEqual(Listing.objects.filter(seller__username__startswith=SAMPLE_USERNAME_PREFIX).count(), 60)

    def test_real_users_with_a_similar_name_are_not_mistaken_for_sample_accounts(self):
        real = make_user("sampel_nina", "Bukan Akun Contoh")
        create_listing(real, title="Punya pengguna asli")
        run_seed("--reset")
        self.assertTrue(Listing.objects.filter(seller=real).exists())

    def test_existing_real_account_with_a_sample_username_is_made_unloginable_but_keeps_nothing_else_unsafe(self):
        # Kalau seseorang sudah memakai username sample_nina, perintah ini tetap memastikan akunnya tidak punya
        # kata sandi dan bukan staf (aman), alih-alih membuat akun ganda.
        User.objects.create_user("sample_nina", password="rahasia123", is_staff=True)
        run_seed()
        user = User.objects.get(username="sample_nina")
        self.assertEqual(User.objects.filter(username="sample_nina").count(), 1)
        self.assertFalse(user.has_usable_password())
        self.assertFalse(user.is_staff)

class SeededSiteTests(TestCase):
    # Sesudah seed, halaman-halaman utama harus tampil benar dengan data nyata.

    @classmethod
    def setUpTestData(cls):
        run_seed()

    def test_catalog_shows_fifty_available_listings_over_five_pages_of_twelve(self):
        response = self.client.get(reverse("listings:list"))
        self.assertEqual(response.context["total_count"], 50)
        self.assertEqual(len(response.context["page"].object_list), 12)
        self.assertEqual(response.context["page"].paginator.num_pages, 5)
        self.assertNotContains(response, "Belum ada pakaian di katalog")

    def test_every_category_tab_has_ten_listings(self):
        for category in Listing.Category.values:
            with self.subTest(category=category):
                response = self.client.get(reverse("listings:list"), {"category": category})
                self.assertEqual(response.context["results_count"], 10)

    def test_filters_work_on_the_seeded_data(self):
        url = reverse("listings:list")
        self.assertGreater(self.client.get(url, {"size": "M"}).context["results_count"], 0)
        self.assertGreater(self.client.get(url, {"condition": "Fair"}).context["results_count"], 0)
        self.assertGreater(self.client.get(url, {"tag": "upcycled"}).context["results_count"], 0)
        self.assertGreater(self.client.get(url, {"price_max": "100000"}).context["results_count"], 0)
        self.assertGreater(self.client.get(url, {"q": "zara"}).context["results_count"], 0)
        self.assertGreater(len(self.client.get(url).context["city_choices"]), 8)

    def test_sold_and_hidden_never_leak_into_the_catalog(self):
        titles = [l.title for l in self.client.get(reverse("listings:list")).context["page"].object_list]
        sold_titles = {row["title"] for row in SOLD}
        self.assertFalse(sold_titles & set(titles))

    def test_a_sample_sellers_storefront_shows_listings_and_a_sold_preview(self):
        nina = User.objects.get(username="sample_nina")
        response = self.client.get(f"/profile/{nina.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["available_count"], 10)
        self.assertEqual(response.context["sold_count"], 2)
        self.assertEqual(len(response.context["listings"]), 8)
        self.assertEqual(len(response.context["sold_preview"]), 2)
        self.assertContains(response, "Muat 2 lagi")
        self.assertContains(response, "Baru saja terjual")

    def test_sample_contact_is_hidden_from_guests_and_never_a_real_address(self):
        nina = User.objects.get(username="sample_nina")
        self.assertNotContains(self.client.get(f"/profile/{nina.pk}/"), "nina@example.com")
        viewer = make_user("pembeli", "Pembeli")
        self.client.force_login(viewer)
        self.assertContains(self.client.get(f"/profile/{nina.pk}/"), "mailto:nina@example.com")

    def test_detail_pages_open_for_every_seeded_listing(self):
        for listing in Listing.objects.all():
            with self.subTest(title=listing.title):
                self.assertEqual(self.client.get(reverse("listings:detail", args=[listing.pk])).status_code, 200)
