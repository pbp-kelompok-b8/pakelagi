from django.test import SimpleTestCase
from django.urls import reverse


class IntroPageTests(SimpleTestCase):
    def test_login_keeps_its_form_and_includes_local_intro_assets(self):
        response = self.client.get(reverse('accounts:login'), {'next': '/'})
        self.assertContains(response, 'name="next" value="/"')
        self.assertContains(response, 'aria-label="Intro Pakelagi"')
        self.assertContains(response, '/static/js/intro.js')
        self.assertContains(response, 'data-progress=', count=8)
        self.assertContains(response, '<img src="/static/intro/', count=16)
