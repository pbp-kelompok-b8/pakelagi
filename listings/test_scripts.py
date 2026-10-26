import re

from django.test import TestCase

from listings.test_detail import create_listing, make_user


class ScriptSafetyTests(TestCase):
    # HTMX menjalankan ulang semua <script> di halaman saat tombol back dipakai. Kalau sebuah skrip memakai
    # const atau let di tingkat paling luar, jalan kedua akan error "Identifier ... has already been declared"
    # dan semua binding di skrip itu mati. Variabel harus dibuat di dalam fungsi.
    # Skrip kita memakai indentasi 4 spasi di dalam <script>, jadi "const"/"let" dengan 4 spasi = tingkat luar.

    def top_level_declarations(self, html):
        found = []
        for script in re.findall(r"<script>(.*?)</script>", html, re.DOTALL):
            for line in script.splitlines():
                if re.match(r"^ {4}(const|let) ", line):
                    found.append(line.strip())
        return found

    def test_pages_do_not_declare_top_level_variables_in_scripts(self):
        seller = make_user("sari", "Sari Wulan")
        listing = create_listing(seller)
        pages = [
            "/", "/listings/", f"/listings/{listing.pk}/", f"/profile/{seller.pk}/",
            "/listings/create/", "/listings/mine/", f"/listings/{listing.pk}/edit/",
        ]
        for logged_in in (False, True):
            if logged_in:
                self.client.force_login(seller)
            for page in pages:
                with self.subTest(page=page, logged_in=logged_in):
                    response = self.client.get(page)
                    if response.status_code != 200:   # halaman member bagi guest berupa redirect login
                        continue
                    self.assertEqual(self.top_level_declarations(response.content.decode()), [])

    def test_the_detector_itself_catches_the_bug(self):
        broken = "<script>\n    const $menu = document.getElementById('x');\n    let kota = '';\n</script>"
        self.assertEqual(self.top_level_declarations(broken), ["const $menu = document.getElementById('x');", "let kota = '';"])
        fine = "<script>\n    function pasang() {\n        const $menu = 1;\n    }\n</script>"
        self.assertEqual(self.top_level_declarations(fine), [])
