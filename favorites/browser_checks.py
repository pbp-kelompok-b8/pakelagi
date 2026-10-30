"""Pemeriksaan browser opsional: python manage.py test favorites.browser_checks.

Memerlukan Playwright dan Chromium; tidak termasuk discovery test Django biasa.
Data dibuat pada database test, bukan database pengembangan.
"""
from pathlib import Path
import os
from unittest import skipUnless
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import requests
from django.conf import settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import Client

from favorites.models import Favorite
from listings.models import Listing
from listings.test_detail import create_listing, make_user

try:
    from playwright.sync_api import expect, sync_playwright
except ImportError:
    sync_playwright = None


@skipUnless(sync_playwright, "Install Playwright untuk pemeriksaan browser opsional.")
class FavoriteBrowserChecks(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        response = requests.get("https://unpkg.com/htmx.org@2.0.4/dist/htmx.min.js", timeout=30)
        response.raise_for_status()
        cls.htmx_source = response.text
        # API sync Playwright menjalankan event loop pada thread test. ORM di sini
        # tetap berurutan; pengecualian ini hanya aktif selama kelas browser test.
        cls.async_safety = patch.dict(os.environ, {"DJANGO_ALLOW_ASYNC_UNSAFE": "true"})
        cls.async_safety.start()
        cls.addClassCleanup(cls.async_safety.stop)
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        super().tearDownClass()

    def setUp(self):
        self.seller = make_user("browser-seller", "Penjual")
        self.member = make_user("browser-member", "Member")
        self.listing = create_listing(self.seller, title="Atasan browser", size=Listing.Size.M)
        self.dress = create_listing(self.seller, title="Dress browser", category=Listing.Category.DRESS)
        self.context = self.make_context()
        self.page = self.context.new_page()
        self.errors = []
        self.page.on("pageerror", lambda error: self.errors.append(str(error)))

    def tearDown(self):
        self.context.close()
        self.assertEqual(self.errors, [])

    def make_context(self, user=True, javascript=True, mobile=False):
        context = self.browser.new_context(
            java_script_enabled=javascript,
            viewport={"width": 390, "height": 844} if mobile else {"width": 1440, "height": 1000},
        )
        # Gunakan library HTMX resmi, tanpa bergantung pada waktu muat CDN setiap halaman.
        context.route("https://unpkg.com/htmx.org@2.0.4", lambda route: route.fulfill(
            status=200, content_type="application/javascript", body=self.htmx_source,
        ))
        if user:
            client = Client()
            client.force_login(self.member if user is True else user)
            context.add_cookies([{
                "name": settings.SESSION_COOKIE_NAME,
                "value": client.cookies[settings.SESSION_COOKIE_NAME].value,
                "url": self.live_server_url,
            }])
        return context

    def open(self, path):
        self.page.goto(self.live_server_url + path)
        self.page.wait_for_function("window.htmx !== undefined")

    def heart(self, slot="card"):
        return self.page.locator(f"#favorite-{slot}-{self.listing.pk} button")

    def expect_query(self, **params):
        expected = {key: [value] for key, value in params.items()}
        self.page.wait_for_url(lambda url: parse_qs(urlsplit(url).query) == expected)

    def screenshot(self, name):
        directory = os.environ.get("PAKELAGI_BROWSER_SCREENSHOTS")
        if directory:
            Path(directory).mkdir(parents=True, exist_ok=True)
            self.page.screenshot(path=str(Path(directory) / name), full_page=True)

    def test_catalog_filters_history_and_heart(self):
        self.open("/listings/")
        self.page.get_by_role("navigation", name="Kategori", exact=True).get_by_role("link", name="Top", exact=True).click()
        expect(self.page).to_have_url(self.live_server_url + "/listings/?category=Top")
        expect(self.page.locator(".listing-card")).to_have_count(1)
        self.page.locator('input[name="size"][value="M"]').check()
        self.expect_query(category="Top", size="M")
        self.page.locator("#catalog-sort").select_option("harga_terendah")
        self.expect_query(category="Top", size="M", sort="harga_terendah")
        self.page.locator("#catalog-q").fill("Atasan")
        self.expect_query(q="Atasan", category="Top", size="M", sort="harga_terendah")
        before = self.page.url
        self.heart().click()
        expect(self.heart()).to_have_attribute("aria-pressed", "true")
        expect(self.page).to_have_url(before)
        self.heart().click()
        expect(self.heart()).to_have_attribute("aria-pressed", "false")
        self.page.get_by_role("navigation", name="Kategori", exact=True).get_by_role("link", name="Dress", exact=True).click()
        expect(self.page.get_by_text("Tidak ada pakaian yang cocok")).to_be_visible()
        self.page.go_back()
        expect(self.heart()).to_be_visible()
        self.page.go_forward()
        expect(self.page.get_by_text("Tidak ada pakaian yang cocok")).to_be_visible()
        self.page.reload()
        expect(self.page.get_by_role("navigation", name="Kategori", exact=True).locator('[aria-current="page"]')).to_have_text("Dress")

    def test_notes_filter_remove_last_and_screenshots(self):
        Favorite.objects.create(user=self.member, listing=self.listing)
        self.open("/favorites/?category=Top")
        self.page.get_by_role("link", name="Edit catatan").click()
        expect(self.page.locator('textarea[name="note"]')).to_be_visible()
        self.page.locator('textarea[name="note"]').fill("Catatan privat <b>bukan HTML</b>")
        self.page.get_by_role("button", name="Simpan catatan").click()
        expect(self.page.get_by_text("Catatan disimpan.")).to_be_visible()
        expect(self.page.get_by_text("Catatan privat <b>bukan HTML</b>")).to_be_visible()
        self.assertEqual(self.page.locator("#favorite-results b").count(), 0)
        self.screenshot("favorites-desktop.png")
        self.page.set_viewport_size({"width": 390, "height": 844})
        self.screenshot("favorites-mobile.png")
        self.assertLessEqual(self.page.evaluate("document.documentElement.scrollWidth"), 390)
        self.page.get_by_role("button", name="Hapus favorit", exact=True).click()
        expect(self.page.get_by_text("Belum ada favorit", exact=True)).to_be_visible()
        expect(self.page.get_by_text("0 dari 0 favorit")).to_be_visible()
        expect(self.page).to_have_url(self.live_server_url + "/favorites/?category=Top")

    def test_failure_retry_and_multiple_controls(self):
        self.open("/listings/?category=Top")
        self.page.route("**/favorites/listings/*/add/", lambda route: route.abort(), times=1)
        self.heart().click()
        expect(self.page.locator("[data-favorite-error]")).to_be_visible()
        expect(self.heart()).to_have_attribute("aria-pressed", "false")
        self.heart().click()
        expect(self.heart()).to_have_attribute("aria-pressed", "true")
        self.page.evaluate("""id => {
            const clone = document.getElementById('favorite-card-' + id).cloneNode(true);
            clone.id = 'favorite-detail-' + id;
            const form = clone.querySelector('form');
            form.querySelector('[name="slot"]').value = 'detail';
            form.setAttribute('hx-target', '#' + clone.id);
            document.getElementById('listing-results').append(clone);
            htmx.process(clone);
        }""", self.listing.pk)
        self.heart().click()
        expect(self.heart()).to_have_attribute("aria-pressed", "false")
        expect(self.heart("detail")).to_have_attribute("aria-pressed", "false")
        self.heart("detail").click()
        expect(self.heart()).to_have_attribute("aria-pressed", "true")
        expect(self.heart("detail")).to_have_attribute("aria-pressed", "true")
        self.assertEqual(Favorite.objects.filter(user=self.member, listing=self.listing).count(), 1)

    def test_html_fallback_and_mobile_keyboard(self):
        context = self.make_context(javascript=False, mobile=True)
        try:
            page = context.new_page()
            page.goto(self.live_server_url + "/listings/?category=Top")
            page.locator('input[name="size"][value="M"]').check()
            page.locator("#catalog-sort").select_option("harga_terendah")
            page.get_by_role("button", name="Terapkan filter").click()
            expect(page.locator(".listing-card")).to_have_count(1)
            self.assertIn("category=Top", page.url)
            self.assertIn("size=M", page.url)
            self.assertIn("sort=harga_terendah", page.url)
            button = page.locator(f"#favorite-card-{self.listing.pk} button")
            button.focus()
            page.keyboard.press("Enter")
            expect(page.locator(f"#favorite-card-{self.listing.pk} button")).to_have_attribute("aria-pressed", "true")
            self.assertIn("category=Top", page.url)
            page.goto(self.live_server_url + "/favorites/?category=Top")
            page.get_by_role("link", name="Edit catatan").click()
            page.locator('textarea[name="note"]').fill("Tanpa JavaScript")
            page.get_by_role("button", name="Simpan catatan").click()
            expect(page.get_by_text("Tanpa JavaScript")).to_be_visible()
            page.get_by_role("button", name="Hapus favorit", exact=True).click()
            expect(page.get_by_text("Belum ada favorit", exact=True)).to_be_visible()
        finally:
            context.close()

    def test_guest_incomplete_and_expired_session(self):
        for user, destination in ((False, "/accounts/login/"), (make_user("unfinished"), "/profile/create/")):
            context = self.make_context(user=user)
            try:
                page = context.new_page()
                page.goto(self.live_server_url + "/listings/?category=Top")
                invite = page.locator(f"#favorite-card-{self.listing.pk} a")
                expect(invite).to_be_visible()
                self.assertIn(destination, invite.get_attribute("href"))
            finally:
                context.close()
        self.open("/listings/?category=Top")
        from django.contrib.sessions.models import Session
        session_id = next(cookie["value"] for cookie in self.context.cookies()
                          if cookie["name"] == settings.SESSION_COOKIE_NAME)
        Session.objects.filter(session_key=session_id).delete()
        self.heart().click()
        expect(self.page).to_have_url(self.live_server_url + "/accounts/login/?next=%2Flistings%2F%3Fcategory%3DTop")

    def test_sold_favorite_removal_hides_all_save_controls(self):
        Favorite.objects.create(user=self.member, listing=self.listing)
        Listing.objects.filter(pk=self.listing.pk).update(status=Listing.Status.SOLD)
        self.open(f"/listings/{self.listing.pk}/")
        expect(self.heart("detail")).to_have_attribute("aria-pressed", "true")
        self.page.evaluate("""id => {
            const clone = document.getElementById('favorite-detail-' + id).cloneNode(true);
            clone.id = 'favorite-card-' + id;
            clone.querySelector('[name="slot"]').value = 'card';
            clone.querySelector('form').setAttribute('hx-target', '#' + clone.id);
            document.getElementById('konten').append(clone);
            htmx.process(clone);
        }""", self.listing.pk)
        self.heart("detail").click()
        expect(self.heart("detail")).to_have_count(0)
        expect(self.heart()).to_have_count(0)
        self.assertFalse(Favorite.objects.filter(user=self.member, listing=self.listing).exists())
