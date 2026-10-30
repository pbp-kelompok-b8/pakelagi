from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from listings.models import Listing
from listings.test_models import make_listing
from profiles.models import Profile


def make_user(username, display_name=None, **profile_fields):
    user = User.objects.create_user(username)
    if display_name is not None:
        Profile.objects.create(user=user, display_name=display_name, **profile_fields)
    return user


def create_listing(seller, **overrides):
    listing = make_listing(seller, **overrides)
    listing.save()
    return listing


class DetailAccessTests(TestCase):
    def setUp(self):
        self.seller = make_user("sari", "Sari Wulan")

    def url(self, listing):
        return reverse("listings:detail", args=[listing.pk])

    def test_url_pattern(self):
        listing = create_listing(self.seller)
        self.assertEqual(self.url(listing), f"/listings/{listing.pk}/")

    def test_guest_can_open_available_listing_with_all_public_fields(self):
        listing = create_listing(
            self.seller, title="Wool-blend oversized coat", brand="COS", price=285000,
            category=Listing.Category.OUTERWEAR, size=Listing.Size.M, condition=Listing.Condition.LIKE_NEW,
            city="Bandung", description="Coat wol campuran warna camel.",
        )
        response = self.client.get(self.url(listing))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "listings/detail.html")
        for text in ("Wool-blend oversized coat", "COS", "Rp 285.000", "Outerwear", "Like New", "Bandung",
                     "Coat wol campuran warna camel.", "Sari Wulan", "Harga dari penjual"):
            with self.subTest(text=text):
                self.assertContains(response, text)

    def test_unknown_listing_is_404(self):
        self.assertEqual(self.client.get("/listings/999999/").status_code, 404)

    def test_detail_only_accepts_get(self):
        listing = create_listing(self.seller)
        self.assertEqual(self.client.post(self.url(listing)).status_code, 405)

    def test_response_is_not_cacheable_by_shared_caches(self):
        listing = create_listing(self.seller)
        header = self.client.get(self.url(listing))["Cache-Control"]
        self.assertIn("private", header)
        self.assertIn("no-store", header)

    def test_sold_listing_is_viewable_but_shows_no_contact(self):
        listing = create_listing(self.seller, status=Listing.Status.SOLD)
        member = make_user("budi", "Budi")
        self.client.force_login(member)
        response = self.client.get(self.url(listing))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Barang ini sudah terjual")
        self.assertNotContains(response, "Kontak penjual</p>")

    def test_hidden_listing_is_404_for_guest_and_other_members(self):
        listing = create_listing(self.seller, status=Listing.Status.HIDDEN)
        self.assertEqual(self.client.get(self.url(listing)).status_code, 404)
        self.client.force_login(make_user("budi", "Budi"))
        self.assertEqual(self.client.get(self.url(listing)).status_code, 404)

    def test_hidden_listing_is_visible_to_its_seller_and_staff_with_notice(self):
        listing = create_listing(self.seller, status=Listing.Status.HIDDEN)
        staff = User.objects.create_user("admin1", is_staff=True)
        for viewer in (self.seller, staff):
            with self.subTest(viewer=viewer.username):
                self.client.force_login(viewer)
                response = self.client.get(self.url(listing))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "disembunyikan")


class DetailContactPrivacyTests(TestCase):
    def setUp(self):
        self.seller = make_user(
            "sari", "Sari Wulan", contact_type="instagram", contact_value="sari.lemari",
            phone_number="+628123456789",
        )
        self.listing = create_listing(self.seller)
        self.url = reverse("listings:detail", args=[self.listing.pk])

    def assertNoContactLeak(self, response):
        for secret in ("sari.lemari", "+628123456789", "instagram.com/sari"):
            self.assertNotContains(response, secret)

    def test_guest_gets_login_invite_and_no_contact_data(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Masuk untuk melihat kontak")
        self.assertContains(response, "/accounts/login/?next=")
        self.assertNoContactLeak(response)

    def test_member_without_profile_gets_onboarding_invite_and_no_contact_data(self):
        self.client.force_login(make_user("budi"))
        response = self.client.get(self.url)
        self.assertContains(response, "Lengkapi profil untuk melihat kontak")
        self.assertNoContactLeak(response)

    def test_member_with_blank_display_name_gets_no_contact_data(self):
        self.client.force_login(make_user("budi", " "))
        response = self.client.get(self.url)
        self.assertContains(response, "Lengkapi profil untuk melihat kontak")
        self.assertNoContactLeak(response)

    def test_complete_member_sees_contact_and_cta(self):
        self.client.force_login(make_user("budi", "Budi"))
        response = self.client.get(self.url)
        self.assertContains(response, "@sari.lemari")
        self.assertContains(response, "https://www.instagram.com/sari.lemari/")
        self.assertContains(response, "Hubungi via Instagram")
        self.assertContains(response, "Telepon: +628123456789")

    def test_seller_account_email_is_never_shown(self):
        self.seller.email = "pribadi@example.com"
        self.seller.save()
        self.client.force_login(make_user("budi", "Budi"))
        self.assertNotContains(self.client.get(self.url), "pribadi@example.com")

    def test_owner_sees_own_listing_notice_instead_of_contact_panel(self):
        self.client.force_login(self.seller)
        response = self.client.get(self.url)
        self.assertContains(response, "Ini listing milikmu")
        self.assertNotContains(response, "Hubungi via Instagram")

    def test_seller_without_profile_page_still_renders(self):
        orphan = make_user("tanpaprofil")
        listing = create_listing(orphan)
        self.client.force_login(make_user("budi", "Budi"))
        response = self.client.get(reverse("listings:detail", args=[listing.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Penjual Pakelagi")
        self.assertContains(response, "Penjual belum menambahkan kontak.")
        self.assertNotContains(response, f"/profile/{orphan.pk}/")

    def test_seller_with_blank_display_name_is_treated_as_no_profile(self):
        blank = make_user("kosong", " ", contact_type="other", contact_value="https://example.com/x")
        listing = create_listing(blank)
        response = self.client.get(reverse("listings:detail", args=[listing.pk]))
        self.assertContains(response, "Penjual Pakelagi")
        self.assertNotContains(response, "https://example.com/x")

    def test_seller_name_links_to_public_profile(self):
        self.assertContains(self.client.get(self.url), f'href="/profile/{self.seller.pk}/"')


class DetailContentTests(TestCase):
    def setUp(self):
        self.seller = make_user("sari", "Sari Wulan")

    def get(self, listing):
        return self.client.get(reverse("listings:detail", args=[listing.pk]))

    def test_only_selected_sustainability_tags_are_shown(self):
        listing = create_listing(
            self.seller, is_repairable=True, is_upcycled=False,
            is_locally_available=True, extends_clothing_life=False,
        )
        self.assertEqual(listing.sustainability_tags, ["Bisa diperbaiki", "Tersedia lokal"])
        response = self.get(listing)
        self.assertContains(response, "Tag keberlanjutan (dari penjual)")
        self.assertContains(response, "Bisa diperbaiki")
        self.assertContains(response, "Tersedia lokal")
        self.assertNotContains(response, "Upcycled")
        self.assertNotContains(response, "Memperpanjang usia pakaian")

    def test_no_tags_section_when_nothing_selected(self):
        listing = create_listing(
            self.seller, is_repairable=False, is_upcycled=False,
            is_locally_available=False, extends_clothing_life=False,
        )
        self.assertNotContains(self.get(listing), "Tag keberlanjutan")

    def test_brand_row_is_omitted_when_brand_is_empty(self):
        listing = create_listing(self.seller, brand="")
        self.assertNotContains(self.get(listing), "Brand</dt>")

    def test_user_text_is_escaped(self):
        listing = create_listing(
            self.seller, title="<script>alert(1)</script> kemeja", brand="<b>X</b>",
            description="<img src=x onerror=alert(2)>",
        )
        response = self.get(listing)
        for raw in ("<script>alert(1)</script>", "<b>X</b>", "<img src=x onerror=alert(2)>"):
            with self.subTest(raw=raw):
                self.assertNotContains(response, raw)
        self.assertContains(response, "&lt;script&gt;alert(1)&lt;/script&gt; kemeja")

    def test_image_has_alt_text_and_local_fallback(self):
        listing = create_listing(self.seller, title="Kemeja flanel kotak", image_url="https://example.com/k.jpg")
        response = self.get(listing)
        self.assertContains(response, 'alt="Kemeja flanel kotak"')
        self.assertContains(response, "Foto tidak tersedia")
        self.assertContains(response, 'onerror="this.remove()"')

    def test_upload_date_is_shown_in_indonesian(self):
        from datetime import datetime, timezone
        listing = create_listing(self.seller)
        Listing.objects.filter(pk=listing.pk).update(created_at=datetime(2026, 9, 24, 8, 0, tzinfo=timezone.utc))
        self.assertContains(self.get(listing), "Diunggah 24 September 2026")

    def test_seller_active_listing_count_counts_only_available(self):
        listing = create_listing(self.seller)
        create_listing(self.seller, title="Barang kedua yang tersedia")
        create_listing(self.seller, title="Barang yang sudah laku", status=Listing.Status.SOLD)
        create_listing(self.seller, title="Barang yang disembunyikan", status=Listing.Status.HIDDEN)
        self.assertContains(self.get(listing), "2 listing aktif")


class MoreFromSellerTests(TestCase):
    def setUp(self):
        self.seller = make_user("sari", "Sari Wulan")
        self.other = make_user("budi", "Budi")
        self.listing = create_listing(self.seller, title="Listing yang sedang dibuka")

    def get(self):
        return self.client.get(reverse("listings:detail", args=[self.listing.pk]))

    def test_shows_other_available_listings_from_same_seller_only(self):
        create_listing(self.seller, title="Lainnya yang tersedia")
        create_listing(self.seller, title="Lainnya yang sudah laku", status=Listing.Status.SOLD)
        create_listing(self.seller, title="Lainnya yang disembunyikan", status=Listing.Status.HIDDEN)
        create_listing(self.other, title="Milik penjual lain")
        response = self.get()
        self.assertContains(response, "Lainnya dari Sari Wulan")
        self.assertContains(response, "Lainnya yang tersedia")
        self.assertNotContains(response, "Lainnya yang sudah laku")
        self.assertNotContains(response, "Lainnya yang disembunyikan")
        self.assertNotContains(response, "Milik penjual lain")
        self.assertNotIn(self.listing, response.context["more_from_seller"])

    def test_limited_to_four_listings(self):
        for i in range(6):
            create_listing(self.seller, title=f"Barang tambahan nomor {i}")
        self.assertEqual(len(self.get().context["more_from_seller"]), 4)

    def test_section_is_absent_when_seller_has_nothing_else(self):
        self.assertNotContains(self.get(), "Lainnya dari")


class CardLinkTests(TestCase):
    def test_catalog_card_links_to_detail_page(self):
        listing = create_listing(make_user("sari", "Sari"))
        response = self.client.get(reverse("listings:list"))
        self.assertContains(response, f'href="/listings/{listing.pk}/"')
