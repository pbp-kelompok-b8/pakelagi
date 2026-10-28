from django.test import TestCase


class CategoryPageTests(TestCase):
    def test_guest_can_open_dedicated_category_page(self):
        response = self.client.get("/categories/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "categories/index.html")
