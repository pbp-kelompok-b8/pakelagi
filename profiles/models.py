from django.conf import settings
from django.db import models

from profiles.validators import validate_external_https_url


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    display_name = models.CharField("Nama tampilan", max_length=150)
    avatar_url = models.URLField("URL foto profil", max_length=2048, blank=True, validators=[validate_external_https_url])
    cover_url = models.URLField("URL foto sampul", max_length=2048, blank=True, validators=[validate_external_https_url])
    bio = models.TextField("Bio", max_length=500, blank=True)
    city = models.CharField("Kota/area umum", max_length=100, blank=True)
    phone_number = models.CharField("Nomor telepon (opsional)", max_length=16, blank=True)
    contact_type = models.CharField(
        "Metode kontak publik", max_length=10, blank=True,
        choices=[("email", "Email"), ("instagram", "Instagram"), ("other", "Lainnya")],
    )
    contact_value = models.CharField("Kontak publik", max_length=254, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "main_profile"
