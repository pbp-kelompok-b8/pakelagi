"""Browser opsional: python manage.py test main.category_browser_checks.

Memerlukan Playwright/Chromium. Fixture dan server memakai database test.
"""
import os
from pathlib import Path
from unittest import skipUnless
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import requests
from django.contrib.staticfiles.testing import StaticLiveServerTestCase

from listings.models import Listing
from listings.test_detail import create_listing, make_user

try:
    from playwright.sync_api import expect, sync_playwright
except ImportError:
    sync_playwright = None


@skipUnless(sync_playwright, "Install Playwright untuk pemeriksaan browser opsional.")
class CategoryBrowserChecks(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        response = requests.get("https://unpkg.com/htmx.org@2.0.4/dist/htmx.min.js", timeout=30)
        response.raise_for_status()
        cls.htmx_source = response.text
        # API sync Playwright menjalankan event loop di thread test. ORM fixture
        # tetap berurutan; pengecualian hanya berlaku selama kelas test ini.
        cls.async_safety = patch.dict(os.environ, {"DJANGO_ALLOW_ASYNC_UNSAFE": "true"})
        cls.async_safety.start()
        cls.addClassCleanup(cls.async_safety.stop)
        cls.playwright = sync_playwright().start()
        cls.addClassCleanup(cls.playwright.stop)
        cls.browser = cls.playwright.chromium.launch()
        cls.addClassCleanup(cls.browser.close)

    def setUp(self):
        seller = make_user("category-seller", "Penjual")
        self.top = create_listing(seller, title="Atasan kategori")
        for i in range(14):
            create_listing(seller, title=f"Atasan kategori {i}")
        for category in (Listing.Category.BOTTOM, Listing.Category.OUTERWEAR, Listing.Category.MODEST_WEAR):
            create_listing(seller, category=category)
        for status in (Listing.Status.SOLD, Listing.Status.HIDDEN):
            create_listing(seller, title="Tidak boleh dihitung", status=status)
        self.context = self.new_context()
        self.addCleanup(self.context.close)
        self.page = self.context.new_page()
        self.errors = []
        self.page.on("pageerror", lambda error: self.errors.append(str(error)))

    def tearDown(self):
        self.assertEqual(self.errors, [])

    def new_context(self, javascript=True):
        context = self.browser.new_context(java_script_enabled=javascript, viewport={"width": 1440, "height": 1000})
        context.route("https://unpkg.com/htmx.org@2.0.4", lambda route: route.fulfill(
            status=200, content_type="application/javascript", body=self.htmx_source,
        ))
        return context

    def open_categories(self):
        self.page.goto(self.live_server_url + "/categories/")
        expect(self.page.locator(".category-card")).to_have_count(5)

    def screenshot(self, name):
        directory = os.environ.get("PAKELAGI_BROWSER_SCREENSHOTS")
        if directory:
            Path(directory).mkdir(parents=True, exist_ok=True)
            expect(self.page.locator(".category-card")).to_have_count(5)
            for image in self.page.locator(".category-card img").all():
                image.scroll_into_view_if_needed()
                expect(image).to_be_visible()
            self.page.wait_for_function("""() => [...document.querySelectorAll('.category-card img')]
                .every(image => image.complete && image.naturalWidth > 0)""")
            self.page.evaluate("window.scrollTo(0, 0)")
            self.page.screenshot(path=str(Path(directory) / name), full_page=True)

    def test_desktop_navigation_cards_catalog_and_history(self):
        self.page.goto(self.live_server_url + "/")
        self.page.get_by_role("navigation", name="Navigasi utama", exact=True).get_by_role("link", name="Kategori").click()
        expect(self.page).to_have_url(self.live_server_url + "/categories/")
        expect(self.page.locator('[data-category="Top"]')).to_contain_text("15 item")
        expect(self.page.locator('[data-category="Dress"]')).to_contain_text("0 item")
        self.page.locator('.category-card img').first.wait_for(state="visible")
        self.assertTrue(self.page.locator('.category-card img').evaluate_all(
            "images => images.every(image => image.complete && image.naturalWidth > 0)"))
        self.screenshot("categories-desktop.png")

        for category in Listing.Category.values:
            self.page.locator(f'[data-category="{category}"]').click()
            self.page.wait_for_url(lambda url: parse_qs(urlsplit(url).query) == {"category": [category]})
            expect(self.page.locator('#kategori [aria-current="page"]')).to_have_text(category)
            if category == Listing.Category.TOP:
                expect(self.page.locator(".listing-card")).to_have_count(12)
                expect(self.page.locator("#catalog-count")).to_contain_text("15 dari 18 pakaian")
            elif category == Listing.Category.DRESS:
                expect(self.page.get_by_text("Tidak ada pakaian yang cocok")).to_be_visible()
            self.page.go_back()
            expect(self.page).to_have_url(self.live_server_url + "/categories/")
            self.page.go_forward()
            expect(self.page.locator('#kategori [aria-current="page"]')).to_have_text(category)
            self.page.go_back()
            self.page.reload()
            expect(self.page.locator(".category-card")).to_have_count(5)

        self.page.get_by_role("link", name="Lihat seluruh katalog").click()
        expect(self.page).to_have_url(self.live_server_url + "/listings/")
        expect(self.page.locator('#kategori [aria-current="page"]')).to_have_text("Semua")

    def test_responsive_grid_mobile_menu_and_keyboard(self):
        self.open_categories()
        for width, columns in ((1440, 5), (768, 3), (390, 2), (320, 1)):
            self.page.set_viewport_size({"width": width, "height": 1000})
            self.assertEqual(self.page.locator('.category-grid').evaluate(
                "grid => getComputedStyle(grid).gridTemplateColumns.split(' ').length"), columns)
            box = self.page.locator('.category-artwork').first.bounding_box()
            self.assertAlmostEqual(box["width"] / box["height"], .8, places=2)
            self.assertLessEqual(self.page.evaluate("document.documentElement.scrollWidth"), width)
        self.page.set_viewport_size({"width": 390, "height": 844})
        self.page.goto(self.live_server_url + "/")
        self.page.get_by_role("button", name="Buka menu").click()
        self.page.get_by_role("navigation", name="Navigasi utama (HP)").get_by_role("link", name="Kategori").click()
        expect(self.page).to_have_url(self.live_server_url + "/categories/")
        self.screenshot("categories-mobile.png")
        self.page.locator('[data-category="Modest Wear"]').focus()
        expect(self.page.locator('[data-category="Modest Wear"]')).to_be_focused()
        self.page.keyboard.press("Enter")
        self.page.wait_for_url(lambda url: parse_qs(urlsplit(url).query) == {"category": ["Modest Wear"]})
        expect(self.page.locator('#kategori [aria-current="page"]')).to_have_text("Modest Wear")

    def test_plain_links_work_without_javascript(self):
        context = self.new_context(javascript=False)
        try:
            page = context.new_page()
            page.goto(self.live_server_url + "/categories/")
            for category in Listing.Category.values:
                page.locator(f'[data-category="{category}"]').click()
                self.assertEqual(parse_qs(urlsplit(page.url).query), {"category": [category]})
                expect(page.locator('#kategori [aria-current="page"]')).to_have_text(category)
                page.go_back()
            page.get_by_role("link", name="Lihat seluruh katalog").click()
            expect(page).to_have_url(self.live_server_url + "/listings/")
        finally:
            context.close()

    def test_counts_refresh_and_catalog_htmx_stays_intact(self):
        self.open_categories()
        Listing.objects.filter(pk=self.top.pk).update(status=Listing.Status.SOLD)
        self.page.reload()
        expect(self.page.locator('[data-category="Top"]')).to_contain_text("14 item")
        self.page.locator('[data-category="Top"]').click()
        self.page.wait_for_function("window.htmx !== undefined")
        self.page.locator('input[name="size"][value="M"]').check()
        self.page.wait_for_url(lambda url: parse_qs(urlsplit(url).query) == {"category": ["Top"], "size": ["M"]})
        self.page.locator("#kategori").get_by_role("link", name="Modest Wear", exact=True).click()
        self.page.wait_for_url(lambda url: parse_qs(urlsplit(url).query) == {"category": ["Modest Wear"], "size": ["M"]})
        expect(self.page.locator(".listing-card")).to_have_count(1)
        expect(self.page.locator('#kategori [aria-current="page"]')).to_have_text("Modest Wear")
