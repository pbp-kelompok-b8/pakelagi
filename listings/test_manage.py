from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import Client, SimpleTestCase, TestCase
from django.urls import reverse

from listings.forms import ListingForm
from listings.models import Listing
from listings.test_detail import create_listing, make_user
from listings.validators import validate_no_home_address


def valid_data(**overrides):
    data = {
        "image_url": "https://example.com/coat.jpg",
        "title": "Wool-blend oversized coat",
        "brand": "COS",
        "category": "Outerwear",
        "size": "M",
        "condition": "Like New",
        "price": "285000",
        "city": "Bandung",
        "is_repairable": "on",
        "is_locally_available": "on",
        "description": "Coat wol campuran warna camel.",
    }
    data.update(overrides)
    return data


class HomeAddressValidatorTests(SimpleTestCase):
    def test_rejects_home_address_markers(self):
        for value in ("Jl. Merdeka No. 5", "jalan mawar", "Gang Kelinci", "RT 05", "rw 3", "Nomor 12", "Bandung, no 7"):
            with self.subTest(value=value):
                with self.assertRaises(ValidationError):
                    validate_no_home_address(value)

    def test_accepts_city_and_area_names(self):
        for value in ("Bandung", "Coblong, Kota Bandung", "Jalancagak", "Nobel", "Cimahi", "Kebayoran Baru", "Gangnam"):
            with self.subTest(value=value):
                validate_no_home_address(value)


class ListingFormTests(TestCase):
    def test_valid_data_is_accepted(self):
        form = ListingForm(valid_data())
        self.assertTrue(form.is_valid(), form.errors)

    def test_form_does_not_expose_protected_fields(self):
        for name in ("seller", "status", "sold_at", "created_at"):
            with self.subTest(field=name):
                self.assertNotIn(name, ListingForm().fields)

    def test_required_fields(self):
        form = ListingForm({})
        self.assertFalse(form.is_valid())
        for name in ("image_url", "title", "category", "size", "condition", "price", "city", "description"):
            with self.subTest(field=name):
                self.assertIn(name, form.errors)
        self.assertNotIn("brand", form.errors)

    def test_invalid_values_are_rejected(self):
        cases = {
            "price": "-1", "title": "abcd", "image_url": "ftp://example.com/a.jpg",
            "category": "Ngawur", "size": "Ngawur", "condition": "Ngawur", "city": "Jl. Mawar No. 5",
        }
        for name, bad in cases.items():
            with self.subTest(field=name):
                form = ListingForm(valid_data(**{name: bad}))
                self.assertFalse(form.is_valid())
                self.assertIn(name, form.errors)

    def test_free_listing_is_allowed(self):
        self.assertTrue(ListingForm(valid_data(price="0")).is_valid())

    def test_huge_price_is_a_form_error_not_a_server_error(self):
        # Di PostgreSQL kolom integer 32-bit: tanpa batas ini angka besar menjadi error 500.
        for price in ("99999999999999", "2147483648", "100000001"):
            with self.subTest(price=price):
                form = ListingForm(valid_data(price=price))
                self.assertFalse(form.is_valid())
                self.assertIn("Harga maksimal Rp 100.000.000.", form.errors["price"])

    def test_price_at_the_limit_is_accepted(self):
        self.assertTrue(ListingForm(valid_data(price="100000000")).is_valid())

    def test_choice_fields_have_no_blank_option(self):
        for name in ("category", "size", "condition"):
            with self.subTest(field=name):
                self.assertNotIn("", [value for value, _ in ListingForm().fields[name].choices])


class AccessControlTests(TestCase):
    def setUp(self):
        self.seller = make_user("sari", "Sari")
        self.listing = create_listing(self.seller)

    def urls(self):
        pk = self.listing.pk
        return [
            reverse("listings:create"), reverse("listings:mine"),
            reverse("listings:edit", args=[pk]), reverse("listings:delete", args=[pk]),
        ]

    def test_guest_is_sent_to_login(self):
        for url in self.urls():
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertRedirects(response, f"/accounts/login/?next={url}", fetch_redirect_response=False)

    def test_guest_cannot_post_status_change(self):
        url = reverse("listings:status", args=[self.listing.pk])
        response = self.client.post(url, {"status": "Sold"})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/accounts/login/"))
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.status, Listing.Status.AVAILABLE)

    def test_member_without_complete_profile_is_sent_to_onboarding(self):
        self.client.force_login(make_user("budi"))
        for url in self.urls():
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertRedirects(response, f"/profile/create/?next={url}", fetch_redirect_response=False)

    def test_member_without_profile_cannot_create_listing(self):
        self.client.force_login(make_user("budi"))
        self.client.post(reverse("listings:create"), valid_data())
        self.assertEqual(Listing.objects.count(), 1)

    def test_post_without_csrf_token_is_rejected(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.seller)
        response = client.post(reverse("listings:delete", args=[self.listing.pk]))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Listing.objects.filter(pk=self.listing.pk).exists())


class CreateTests(TestCase):
    def setUp(self):
        self.member = make_user("sari", "Sari")
        self.client.force_login(self.member)
        self.url = reverse("listings:create")

    def test_url_pattern(self):
        self.assertEqual(self.url, "/listings/create/")

    def test_form_page_renders_all_sections(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "listings/form.html")
        for text in ("Foto", "Tentang pakaian", "Kondisi", "Harga", "Lokasi", "Tag keberlanjutan", "Deskripsi",
                     "Terbitkan listing", "Like New", "Free Size", "Modest Wear"):
            with self.subTest(text=text):
                self.assertContains(response, text)

    def test_valid_post_creates_listing_for_logged_in_user(self):
        response = self.client.post(self.url, valid_data())
        listing = Listing.objects.get()
        self.assertRedirects(response, reverse("listings:detail", args=[listing.pk]))
        self.assertEqual(listing.seller, self.member)
        self.assertEqual(listing.status, Listing.Status.AVAILABLE)
        self.assertIsNone(listing.sold_at)
        self.assertEqual((listing.title, listing.price, listing.city), ("Wool-blend oversized coat", 285000, "Bandung"))
        self.assertTrue(listing.is_repairable)
        self.assertFalse(listing.is_upcycled)

    def test_unchecked_tags_are_saved_as_false(self):
        self.client.post(self.url, valid_data())
        listing = Listing.objects.get()
        self.assertFalse(listing.extends_clothing_life)

    def test_success_message_is_shown_after_redirect(self):
        response = self.client.post(self.url, valid_data(), follow=True)
        self.assertContains(response, "Listing berhasil diterbitkan.")

    def test_new_listing_appears_in_public_catalog(self):
        self.client.post(self.url, valid_data())
        self.client.logout()
        self.assertContains(self.client.get(reverse("listings:list")), "Wool-blend oversized coat")

    def test_protected_fields_in_post_are_ignored(self):
        other = make_user("budi", "Budi")
        self.client.post(self.url, valid_data(
            seller=other.pk, status="Sold", sold_at="2020-01-01T00:00:00Z", latitude="1.5", longitude="2.5",
        ))
        listing = Listing.objects.get()
        self.assertEqual(listing.seller, self.member)
        self.assertEqual(listing.status, Listing.Status.AVAILABLE)
        self.assertIsNone(listing.sold_at)
        self.assertIsNone(listing.latitude)
        self.assertIsNone(listing.longitude)

    def test_invalid_post_creates_nothing_and_keeps_input_with_errors(self):
        response = self.client.post(self.url, valid_data(price="-5", title="abcd", description=""))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Listing.objects.count(), 0)
        self.assertContains(response, "Periksa kembali isian yang ditandai di bawah.")
        self.assertContains(response, 'value="abcd"')
        self.assertContains(response, 'value="Outerwear" checked')
        self.assertContains(response, 'value="Like New" checked')

    def test_address_in_city_is_rejected_with_message(self):
        response = self.client.post(self.url, valid_data(city="Jl. Mawar No. 5"))
        self.assertEqual(Listing.objects.count(), 0)
        self.assertContains(response, "Jangan cantumkan alamat rumah")

    def test_user_input_is_escaped_when_form_is_redisplayed(self):
        response = self.client.post(self.url, valid_data(title='"><script>alert(1)</script>', price="x"))
        self.assertNotContains(response, "<script>alert(1)</script>")

    def test_create_only_accepts_get_and_post(self):
        self.assertEqual(self.client.put(self.url).status_code, 405)


class EditTests(TestCase):
    def setUp(self):
        self.seller = make_user("sari", "Sari")
        self.other = make_user("budi", "Budi")
        self.listing = create_listing(self.seller, title="Judul lama yang cukup", price=100000)
        self.url = reverse("listings:edit", args=[self.listing.pk])

    def test_url_pattern(self):
        self.assertEqual(self.url, f"/listings/{self.listing.pk}/edit/")

    def test_owner_sees_prefilled_form(self):
        self.client.force_login(self.seller)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="Judul lama yang cukup"')
        self.assertContains(response, "Simpan perubahan")

    def test_owner_can_update(self):
        self.client.force_login(self.seller)
        response = self.client.post(self.url, valid_data(title="Judul baru yang jelas", price="150000"))
        self.assertRedirects(response, reverse("listings:detail", args=[self.listing.pk]))
        self.listing.refresh_from_db()
        self.assertEqual((self.listing.title, self.listing.price), ("Judul baru yang jelas", 150000))
        self.assertEqual(self.listing.seller, self.seller)

    def test_invalid_update_changes_nothing(self):
        self.client.force_login(self.seller)
        response = self.client.post(self.url, valid_data(price="-1"))
        self.assertEqual(response.status_code, 200)
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.price, 100000)

    def test_other_member_gets_404_and_cannot_change_data(self):
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.assertEqual(self.client.post(self.url, valid_data(title="Dibajak orang lain")).status_code, 404)
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.title, "Judul lama yang cukup")

    def test_unknown_listing_is_404(self):
        self.client.force_login(self.seller)
        self.assertEqual(self.client.get("/listings/999999/edit/").status_code, 404)

    def test_staff_can_edit_any_listing_without_taking_ownership(self):
        staff = make_user("mod", "Moderator")
        staff.is_staff = True
        staff.save()
        self.client.force_login(staff)
        self.client.post(self.url, valid_data(title="Diperbaiki oleh moderator"))
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.title, "Diperbaiki oleh moderator")
        self.assertEqual(self.listing.seller, self.seller)

    def test_editing_cannot_unhide_a_moderated_listing(self):
        self.listing.status = Listing.Status.HIDDEN
        self.listing.save()
        self.client.force_login(self.seller)
        self.client.post(self.url, valid_data(status="Available"))
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.status, Listing.Status.HIDDEN)

    def test_editing_cannot_change_status_or_seller_through_post(self):
        self.client.force_login(self.seller)
        self.client.post(self.url, valid_data(status="Sold", seller=self.other.pk))
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.status, Listing.Status.AVAILABLE)
        self.assertEqual(self.listing.seller, self.seller)

    def test_editing_a_sold_listing_keeps_sold_at(self):
        self.listing.status = Listing.Status.SOLD
        self.listing.save()
        sold_at = Listing.objects.get(pk=self.listing.pk).sold_at
        self.client.force_login(self.seller)
        self.client.post(self.url, valid_data(title="Judul sesudah terjual"))
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.sold_at, sold_at)
        self.assertEqual(self.listing.status, Listing.Status.SOLD)


class DeleteTests(TestCase):
    def setUp(self):
        self.seller = make_user("sari", "Sari")
        self.other = make_user("budi", "Budi")
        self.listing = create_listing(self.seller, title="Barang yang akan dihapus")
        self.url = reverse("listings:delete", args=[self.listing.pk])

    def test_url_pattern(self):
        self.assertEqual(self.url, f"/listings/{self.listing.pk}/delete/")

    def test_get_shows_confirmation_and_never_deletes(self):
        self.client.force_login(self.seller)
        response = self.client.get(self.url)
        self.assertContains(response, "Hapus “Barang yang akan dihapus”?")
        self.assertContains(response, "Ya, hapus")
        self.assertTrue(Listing.objects.filter(pk=self.listing.pk).exists())

    def test_owner_post_deletes_and_redirects_to_mine(self):
        self.client.force_login(self.seller)
        response = self.client.post(self.url, follow=True)
        self.assertRedirects(response, reverse("listings:mine"))
        self.assertFalse(Listing.objects.filter(pk=self.listing.pk).exists())
        self.assertContains(response, "dihapus")

    def test_other_member_cannot_delete(self):
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.assertEqual(self.client.post(self.url).status_code, 404)
        self.assertTrue(Listing.objects.filter(pk=self.listing.pk).exists())

    def test_staff_can_delete_any_listing(self):
        staff = make_user("mod", "Moderator")
        staff.is_staff = True
        staff.save()
        self.client.force_login(staff)
        self.client.post(self.url)
        self.assertFalse(Listing.objects.filter(pk=self.listing.pk).exists())

    def test_deleting_one_listing_keeps_others(self):
        keep = create_listing(self.seller, title="Barang yang tetap ada")
        self.client.force_login(self.seller)
        self.client.post(self.url)
        self.assertTrue(Listing.objects.filter(pk=keep.pk).exists())


class StatusChangeTests(TestCase):
    def setUp(self):
        self.seller = make_user("sari", "Sari")
        self.other = make_user("budi", "Budi")
        self.listing = create_listing(self.seller)
        self.url = reverse("listings:status", args=[self.listing.pk])

    def status(self):
        return Listing.objects.get(pk=self.listing.pk).status

    def test_owner_marks_sold_and_sold_at_is_recorded(self):
        self.client.force_login(self.seller)
        response = self.client.post(self.url, {"status": "Sold"})
        self.assertRedirects(response, reverse("listings:mine"))
        listing = Listing.objects.get(pk=self.listing.pk)
        self.assertEqual(listing.status, Listing.Status.SOLD)
        self.assertIsNotNone(listing.sold_at)

    def test_sold_listing_leaves_public_catalog_and_can_come_back(self):
        self.client.force_login(self.seller)
        self.client.post(self.url, {"status": "Sold"})
        self.assertNotContains(self.client.get(reverse("listings:list")), self.listing.title)
        self.client.post(self.url, {"status": "Available"})
        self.assertEqual(self.status(), Listing.Status.AVAILABLE)
        self.assertContains(self.client.get(reverse("listings:list")), self.listing.title)

    def test_selling_again_updates_sold_at(self):
        self.client.force_login(self.seller)
        self.client.post(self.url, {"status": "Sold"})
        first = Listing.objects.get(pk=self.listing.pk).sold_at
        self.client.post(self.url, {"status": "Available"})
        self.client.post(self.url, {"status": "Sold"})
        self.assertGreater(Listing.objects.get(pk=self.listing.pk).sold_at, first)

    def test_repeating_the_same_status_is_harmless(self):
        self.client.force_login(self.seller)
        self.client.post(self.url, {"status": "Sold"})
        first = Listing.objects.get(pk=self.listing.pk).sold_at
        self.client.post(self.url, {"status": "Sold"})
        self.assertEqual(Listing.objects.get(pk=self.listing.pk).sold_at, first)

    def test_owner_cannot_set_hidden_or_unknown_status(self):
        self.client.force_login(self.seller)
        for value in ("Hidden", "Ngawur", ""):
            with self.subTest(value=value):
                self.assertEqual(self.client.post(self.url, {"status": value}).status_code, 400)
                self.assertEqual(self.status(), Listing.Status.AVAILABLE)
        self.assertEqual(self.client.post(self.url).status_code, 400)

    def test_owner_cannot_change_status_of_moderated_listing(self):
        self.listing.status = Listing.Status.HIDDEN
        self.listing.save()
        self.client.force_login(self.seller)
        for value in ("Available", "Sold"):
            with self.subTest(value=value):
                response = self.client.post(self.url, {"status": value}, follow=True)
                self.assertContains(response, "tidak bisa diubah statusnya")
                self.assertEqual(self.status(), Listing.Status.HIDDEN)

    def test_other_member_and_staff_cannot_change_someone_elses_status(self):
        staff = make_user("mod", "Moderator")
        staff.is_staff = True
        staff.save()
        for viewer in (self.other, staff):
            with self.subTest(viewer=viewer.username):
                self.client.force_login(viewer)
                self.assertEqual(self.client.post(self.url, {"status": "Sold"}).status_code, 404)
                self.assertEqual(self.status(), Listing.Status.AVAILABLE)

    def test_get_is_not_allowed(self):
        self.client.force_login(self.seller)
        self.assertEqual(self.client.get(self.url).status_code, 405)


class MineTests(TestCase):
    def setUp(self):
        self.member = make_user("sari", "Sari")
        self.other = make_user("budi", "Budi")
        self.client.force_login(self.member)
        self.url = reverse("listings:mine")

    def test_url_pattern(self):
        self.assertEqual(self.url, "/listings/mine/")

    def test_shows_own_listings_of_every_status_and_nobody_elses(self):
        create_listing(self.member, title="Punyaku yang tersedia")
        create_listing(self.member, title="Punyaku yang terjual", status=Listing.Status.SOLD)
        create_listing(self.member, title="Punyaku yang disembunyikan", status=Listing.Status.HIDDEN)
        create_listing(self.other, title="Punya orang lain")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "listings/mine.html")
        for title in ("Punyaku yang tersedia", "Punyaku yang terjual", "Punyaku yang disembunyikan"):
            self.assertContains(response, title)
        self.assertNotContains(response, "Punya orang lain")

    def test_tab_counts_and_filtering(self):
        create_listing(self.member, title="Barang tersedia satu")
        create_listing(self.member, title="Barang tersedia dua")
        create_listing(self.member, title="Barang sudah terjual", status=Listing.Status.SOLD)
        create_listing(self.member, title="Barang disembunyikan", status=Listing.Status.HIDDEN)
        counts = self.client.get(self.url).context["counts"]
        self.assertEqual(
            (counts["all"], counts["tersedia"], counts["terjual"], counts["disembunyikan"]), (4, 2, 1, 1),
        )
        response = self.client.get(self.url + "?status=terjual")
        self.assertContains(response, "Barang sudah terjual")
        self.assertNotContains(response, "Barang tersedia satu")
        response = self.client.get(self.url + "?status=disembunyikan")
        self.assertContains(response, "Barang disembunyikan")
        self.assertContains(response, "Disembunyikan moderator")
        self.assertNotContains(response, "Barang sudah terjual")

    def test_unknown_tab_falls_back_to_all(self):
        create_listing(self.member, title="Barang tersedia satu")
        create_listing(self.member, title="Barang sudah terjual", status=Listing.Status.SOLD)
        response = self.client.get(self.url + "?status=ngawur")
        self.assertContains(response, "Barang tersedia satu")
        self.assertContains(response, "Barang sudah terjual")

    def test_counts_never_include_other_members(self):
        create_listing(self.other, title="Punya orang lain")
        self.assertEqual(self.client.get(self.url).context["counts"]["all"], 0)

    def test_pagination_is_six_per_page(self):
        for i in range(8):
            create_listing(self.member, title=f"Barang nomor {i}")
        first = self.client.get(self.url)
        self.assertEqual(len(first.context["page"].object_list), 6)
        self.assertContains(first, "Menampilkan 1–6 dari 8 listing")
        second = self.client.get(self.url + "?page=2")
        self.assertEqual(len(second.context["page"].object_list), 2)
        self.assertContains(second, "Menampilkan 7–8 dari 8 listing")

    def test_invalid_page_numbers_do_not_crash(self):
        create_listing(self.member)
        for page in ("abc", "0", "-1", "999"):
            with self.subTest(page=page):
                self.assertEqual(self.client.get(self.url + f"?page={page}").status_code, 200)

    def test_pagination_keeps_selected_tab(self):
        for i in range(7):
            create_listing(self.member, title=f"Barang terjual {i}", status=Listing.Status.SOLD)
        self.assertContains(self.client.get(self.url + "?status=terjual"), "?status=terjual&amp;page=2")

    def test_row_actions_depend_on_status(self):
        available = create_listing(self.member, title="Barang yang tersedia")
        sold = create_listing(self.member, title="Barang yang terjual", status=Listing.Status.SOLD)
        response = self.client.get(self.url)
        self.assertContains(response, "Tandai terjual")
        self.assertContains(response, "Jual lagi")
        self.assertContains(response, reverse("listings:edit", args=[available.pk]))
        self.assertNotContains(response, reverse("listings:edit", args=[sold.pk]))
        self.assertContains(response, reverse("listings:delete", args=[sold.pk]))

    def test_empty_state(self):
        response = self.client.get(self.url)
        self.assertContains(response, "Kamu belum punya listing")
        self.assertContains(response, reverse("listings:create"))

    def test_titles_are_escaped(self):
        create_listing(self.member, title="<script>alert(1)</script> kemeja")
        self.assertNotContains(self.client.get(self.url), "<script>alert(1)</script>")


class NavigationLinkTests(TestCase):
    def test_member_header_links_to_create_and_mine(self):
        self.client.force_login(make_user("sari", "Sari"))
        response = self.client.get("/")
        self.assertContains(response, 'href="/listings/create/"')
        self.assertContains(response, 'href="/listings/mine/"')

    def test_guest_header_has_icons_login_and_register_but_no_account_menu(self):
        html = self.client.get("/").content.decode()
        for text in ('aria-label="Cari pakaian"', 'aria-label="Favorit"', ">Masuk<", ">Daftar<"):
            with self.subTest(text=text):
                self.assertIn(text, html)
        self.assertNotIn('id="account-menu"', html)
        self.assertNotIn('href="/listings/create/"', html)

    def test_member_header_has_account_menu_without_username_in_the_label(self):
        member = make_user("sari", "Sari")
        self.client.force_login(member)
        html = self.client.get("/").content.decode()
        self.assertIn('id="account-menu"', html)
        self.assertIn("Masuk sebagai <strong", html)
        self.assertNotIn("Akun saya (sari)", html.split('id="mobileNav"')[0])
        # Keluar ada di dalam menu akun, bukan lagi tombol terpisah di bilah atas.
        menu = html.split('id="account-menu"')[1].split("</details>")[0]
        self.assertIn('action="/accounts/logout/"', menu)

    def test_header_main_menu_matches_the_design_in_desktop_and_mobile_menus(self):
        html = self.client.get("/").content.decode().split("</header>")[0]  # footer punya tautan serupa
        for href in ('href="/categories/"', 'href="/guides/"'):
            with self.subTest(href=href):
                self.assertEqual(html.count(href), 2)  # menu desktop + menu HP
        for label in (">Katalog<", ">Kategori<", ">Jurnal<", ">Penjual<"):
            with self.subTest(label=label):
                self.assertEqual(html.count(label), 2)

    def test_moderation_link_is_shown_to_staff_only(self):
        self.assertNotContains(self.client.get("/"), ">Moderasi<")
        staff = make_user("mod", "Moderator")
        staff.is_staff = True
        staff.save()
        self.client.force_login(staff)
        self.assertContains(self.client.get("/"), ">Moderasi<", count=2)

    def test_current_section_is_marked_in_the_menu(self):
        self.assertContains(self.client.get("/listings/"), 'class="nav-link" aria-current="page">Katalog<', count=2)
        self.assertNotContains(self.client.get("/"), 'aria-current="page">Katalog<')

    def test_catalog_keeps_its_existing_category_tabs_anchor(self):
        self.assertContains(self.client.get("/listings/"), 'id="kategori"')

    def test_guest_homepage_cta_points_to_register(self):
        response = self.client.get("/")
        self.assertNotContains(response, 'href="/listings/create/"')
        self.assertContains(response, 'href="/accounts/register/"')
