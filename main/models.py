from django.conf import settings
from django.db import models


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    display_name = models.CharField("Nama tampilan", max_length=150)
    bio = models.TextField("Bio", blank=True)
    city = models.CharField("Kota/area umum", max_length=150, blank=True)
    contact_type = models.CharField(
        "Metode kontak publik", max_length=10, blank=True,
        choices=[("email", "Email"), ("instagram", "Instagram"), ("other", "Lainnya")],
    )
    contact_value = models.CharField("Kontak publik", max_length=254, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
