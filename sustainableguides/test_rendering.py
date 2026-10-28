from html.parser import HTMLParser
from urllib.parse import urlsplit

from django.test import SimpleTestCase

from .rendering import render_guide_markdown


class ElementCollector(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.elements = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))


class GuideMarkdownTests(SimpleTestCase):
    def test_unsafe_link_and_image_protocols_are_removed(self):
        for url in (
            'javascript:alert(1)',
            'JaVaScRiPt:alert(1)',
            'JAVASCRIPT:alert(1)',
            'data:text/html;base64,PHNjcmlwdD4=',
            'vbscript:msgbox(1)',
        ):
            with self.subTest(url=url):
                html, _ = render_guide_markdown(f'[Klik]({url})\n\n![Gambar]({url})')
                elements = ElementCollector(html).elements
                self.assertTrue(any(tag == 'a' for tag, _ in elements))
                self.assertTrue(any(tag == 'img' for tag, _ in elements))
                for tag, attrs in elements:
                    if tag == 'a':
                        self.assertNotIn('href', attrs)
                    if tag == 'img':
                        self.assertNotIn('src', attrs)

    def test_entity_obfuscation_is_not_reinterpreted_as_a_url_scheme(self):
        for url in ('java&#x73;cript:alert(1)', 'java&#x09;script:alert(1)'):
            with self.subTest(url=url):
                html, _ = render_guide_markdown(f'[Klik]({url})')
                for tag, attrs in ElementCollector(html).elements:
                    if tag == 'a' and 'href' in attrs:
                        # escape() keeps entities literal; the browser sees a relative URL.
                        self.assertEqual(urlsplit(attrs['href']).scheme, '')

    def test_markdown_and_toc_keep_safe_links_and_formatting(self):
        html, toc = render_guide_markdown(
            '## Perawatan\n\n**Tebal** dan *miring*.\n\n'
            '[Web](https://example.com) [Email](mailto:help@example.com) '
            '[Bagian](#perawatan) [Lokal](/guides/)\n\n'
            '![Kain](https://example.com/kain.jpg)\n\n'
            '| Bahan | Cara |\n| --- | --- |\n| Linen | Cuci |\n\n'
            '```\ncontoh kode\n```'
        )
        self.assertIn('<h2 id="perawatan">', html)
        self.assertIn('<strong>Tebal</strong>', html)
        self.assertIn('<em>miring</em>', html)
        self.assertIn('<table>', html)
        self.assertIn('<code>', html)
        self.assertIn('src="https://example.com/kain.jpg"', html)
        for url in ('https://example.com', 'mailto:help@example.com', '#perawatan', '/guides/'):
            self.assertIn(f'href="{url}"', html)
        self.assertIn('href="#perawatan"', toc)

    def test_raw_html_is_displayed_as_text_not_executed(self):
        html, toc = render_guide_markdown(
            '## <img src=x onerror=alert(1)>\n\n<script>alert(1)</script>'
        )
        self.assertIn('&lt;script&gt;', html)
        for value in (html, toc):
            for tag, attrs in ElementCollector(value).elements:
                self.assertNotIn(tag, ('script', 'img'))
                self.assertFalse(any(name.startswith('on') for name in attrs))
