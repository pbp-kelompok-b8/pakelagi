from django.contrib.auth.models import User
from django.template import Context, Template
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from listings.models import Listing
from listings.test_models import make_listing


class RupiahFilterTests(SimpleTestCase):
    def render(self, value):
        return Template("{% load listing_extras %}{{ v|rupiah }}").render(Context({"v": value}))

    def test_formats_with_dot_thousand_separator(self):
        for value, expected in ((0, "Rp 0"), (950, "Rp 950"), (285000, "Rp 285.000"), (1234567, "Rp 1.234.567")):
            with self.subTest(value=value):
                self.assertEqual(self.render(value), expected)

    def test_invalid_value_renders_empty(self):
        for value in (None, "", "abc"):
            with self.subTest(value=value):
                self.assertEqual(self.render(value), "")


class CatalogViewTests(TestCase):
    def setUp(self):
        self.seller = User.objects.create_user("sari", password="Strong!9382")
        self.url = reverse("listings:list")

    def test_url_is_listings_root(self):
        self.assertEqual(self.url, "/listings/")

    def test_guest_can_open_catalog(self):
        make_listing(self.seller).save()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "listings/list.html")
        self.assertTemplateUsed(response, "listings/components/listing_card.html")

    def test_only_available_listings_are_public(self):
        make_listing(self.seller, title="Barang tersedia").save()
        make_listing(self.seller, title="Barang sudah laku", status=Listing.Status.SOLD).save()
        make_listing(self.seller, title="Barang disembunyikan", status=Listing.Status.HIDDEN).save()
        response = self.client.get(self.url)
        self.assertContains(response, "Barang tersedia")
        self.assertNotContains(response, "Barang sudah laku")
        self.assertNotContains(response, "Barang disembunyikan")
        self.assertEqual(response.context["total_count"], 1)
        self.assertContains(response, "1 pakaian")

    def test_card_shows_brand_title_price_size_condition_and_city(self):
        make_listing(
            self.seller, title="Wool-blend oversized coat", brand="COS", price=285000,
            size=Listing.Size.M, condition=Listing.Condition.LIKE_NEW, city="Bandung",
        ).save()
        response = self.client.get(self.url)
        for text in ("COS", "Wool-blend oversized coat", "Rp 285.000", "Like New · Bandung"):
            with self.subTest(text=text):
                self.assertContains(response, text)

    def test_card_without_brand_omits_brand_line(self):
        make_listing(self.seller, brand="").save()
        self.assertNotContains(self.client.get(self.url), "label-caps !text-[10px]")

    def test_image_has_alt_text_and_local_fallback(self):
        make_listing(self.seller, title="Kemeja flanel kotak", image_url="https://example.com/k.jpg").save()
        response = self.client.get(self.url)
        self.assertContains(response, 'src="https://example.com/k.jpg"')
        self.assertContains(response, 'alt="Kemeja flanel kotak"')
        self.assertContains(response, "Foto tidak tersedia")
        self.assertContains(response, 'onerror="this.remove()"')

    def test_listing_text_is_escaped(self):
        make_listing(self.seller, title="<script>alert(1)</script> kemeja", brand="<b>X</b>").save()
        response = self.client.get(self.url)
        self.assertNotContains(response, "<script>alert(1)</script>")
        self.assertContains(response, "&lt;script&gt;alert(1)&lt;/script&gt; kemeja")
        self.assertNotContains(response, "<b>X</b>")

    def test_newest_listing_comes_first(self):
        make_listing(self.seller, title="Listing pertama").save()
        make_listing(self.seller, title="Listing kedua").save()
        content = self.client.get(self.url).content.decode()
        self.assertLess(content.index("Listing kedua"), content.index("Listing pertama"))

    def test_empty_state_when_no_listings(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Belum ada pakaian di katalog")
        self.assertContains(response, "0 pakaian")

    def test_catalog_only_accepts_get(self):
        self.assertEqual(self.client.post(self.url).status_code, 405)

    def test_navigation_links_to_catalog(self):
        for page in ("/", self.url):
            with self.subTest(page=page):
                self.assertContains(self.client.get(page), 'href="/listings/"')

    def test_catalog_shows_no_seller_contact_data(self):
        from profiles.models import Profile
        Profile.objects.create(
            user=self.seller, display_name="Sari", contact_type="email",
            contact_value="rahasia@example.com", phone_number="+628123456789",
        )
        make_listing(self.seller).save()
        response = self.client.get(self.url)
        self.assertNotContains(response, "rahasia@example.com")
        self.assertNotContains(response, "+628123456789")
