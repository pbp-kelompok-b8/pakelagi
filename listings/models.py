from django.conf import settings
from django.core.validators import MinLengthValidator
from django.db import models
from django.utils import timezone

from listings.validators import validate_http_url


class Listing(models.Model):
    class Category(models.TextChoices):
        TOP = "Top", "Atasan"
        BOTTOM = "Bottom", "Bawahan"
        DRESS = "Dress", "Dress"
        OUTERWEAR = "Outerwear", "Outerwear"
        MODEST_WEAR = "Modest Wear", "Modest Wear"

    class Size(models.TextChoices):
        XS = "XS", "XS"
        S = "S", "S"
        M = "M", "M"
        L = "L", "L"
        XL = "XL", "XL"
        XXL = "XXL", "XXL"
        FREE_SIZE = "Free Size", "Free Size"

    class Condition(models.TextChoices):
        LIKE_NEW = "Like New", "Like New"
        GOOD = "Good", "Good"
        FAIR = "Fair", "Fair"
        NEEDS_REPAIR = "Needs Repair", "Needs Repair"

    class Status(models.TextChoices):
        AVAILABLE = "Available", "Dijual"
        SOLD = "Sold", "Terjual"
        HIDDEN = "Hidden", "Disembunyikan"

    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="listings")
    title = models.CharField("Judul", max_length=120, validators=[MinLengthValidator(5)])
    description = models.TextField("Deskripsi")
    category = models.CharField("Kategori", max_length=20, choices=Category.choices)
    brand = models.CharField("Brand", max_length=80, blank=True)
    size = models.CharField("Ukuran", max_length=10, choices=Size.choices)
    condition = models.CharField("Kondisi", max_length=20, choices=Condition.choices)
    price = models.PositiveIntegerField("Harga (Rp)")
    image_url = models.URLField("URL gambar", max_length=2048, validators=[validate_http_url])
    city = models.CharField("Kota/area umum", max_length=100)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    is_repairable = models.BooleanField("Bisa diperbaiki", default=False)
    is_upcycled = models.BooleanField("Upcycled", default=False)
    is_locally_available = models.BooleanField("Tersedia lokal", default=True)
    extends_clothing_life = models.BooleanField("Memperpanjang usia pakaian", default=True)

    status = models.CharField("Status", max_length=10, choices=Status.choices, default=Status.AVAILABLE)
    sold_at = models.DateTimeField(null=True, blank=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["status", "-created_at"])]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        # sold_at hanya dicatat saat status berpindah KE Sold, bukan setiap kali listing diedit.
        was_sold = (
            self.pk is not None
            and Listing.objects.filter(pk=self.pk, status=self.Status.SOLD).exists()
        )
        if self.status == self.Status.SOLD and not was_sold:
            self.sold_at = timezone.now()
            if kwargs.get("update_fields") is not None:
                kwargs["update_fields"] = {*kwargs["update_fields"], "sold_at"}
        super().save(*args, **kwargs)
