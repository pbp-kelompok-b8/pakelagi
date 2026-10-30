from django.test import SimpleTestCase
from django.urls import resolve, reverse


class AppRouteTests(SimpleTestCase):
    def test_app_namespaces_preserve_public_paths(self):
        routes = {
            "main:show_main": "/",
            "accounts:register": "/accounts/register/",
            "accounts:login": "/accounts/login/",
            "accounts:logout": "/accounts/logout/",
            "profiles:profile_create": "/profile/create/",
            "profiles:profile": "/profile/",
            "profiles:profile_edit": "/profile/edit/",
        }
        for name, path in routes.items():
            with self.subTest(name=name):
                self.assertEqual(reverse(name), path)
                self.assertEqual(resolve(path).view_name, name)
        self.assertEqual(reverse("profiles:profile_public", args=[42]), "/profile/42/")
        self.assertEqual(resolve("/profile/42/").kwargs, {"user_id": 42})
