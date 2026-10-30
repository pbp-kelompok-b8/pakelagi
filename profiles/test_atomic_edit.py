from unittest.mock import patch

from django.contrib.auth.models import User
from django.db import DatabaseError
from django.test import TestCase

from profiles.models import Profile


class AtomicProfileEditTests(TestCase):
    def test_email_write_failure_rolls_back_profile_edit(self):
        user = User.objects.create_user("atomic-seller", email="old@example.com")
        Profile.objects.create(user=user, display_name="Sebelum")
        self.client.force_login(user)
        original_save = User.save

        def fail_email_write(instance, *args, **kwargs):
            if kwargs.get("update_fields") == ["email"]:
                raise DatabaseError("Injected account persistence failure")
            return original_save(instance, *args, **kwargs)

        # Inject failure only at the account persistence boundary. Observe the
        # result through HTTP, rather than testing the form/service internals.
        with patch.object(User, "save", fail_email_write):
            with self.assertRaises(DatabaseError):
                self.client.post("/profile/edit/", {
                    "display_name": "Sesudah", "email": "new@example.com",
                })
        response = self.client.get("/profile/edit/")
        self.assertContains(response, 'value="Sebelum"')
        self.assertContains(response, 'value="old@example.com"')
        self.assertNotContains(response, 'value="Sesudah"')
        self.assertNotContains(response, 'value="new@example.com"')
