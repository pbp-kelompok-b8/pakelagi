from django.conf import settings
from django.core.validators import MaxValueValidator, MinLengthValidator
from django.db import models
from django.utils import timezone

from listings.validators import validate_http_url

MAX_PRICE = 100_000_000


class Listing(models.Model):
    # Kategori barang
    class Category(models.TextChoices):
        TOP = "Top", "Top"
        BOTTOM = "Bottom", "Bottom"
        DRESS = "Dress", "Dress"
        OUTERWEAR = "Outerwear", "Outerwear"
        MODEST_WEAR = "Modest Wear", "Modest Wear"

    # Ukuran barang
    class Size(models.TextChoices):
        XS = "XS", "XS"
        S = "S", "S"
        M = "M", "M"
        L = "L", "L"
        XL = "XL", "XL"
        XXL = "XXL", "XXL"
        FREE_SIZE = "Free Size", "Free Size"

    # Kondisi barang
    class Condition(models.TextChoices):
        LIKE_NEW = "Like New", "Like New"
        GOOD = "Good", "Good"
        FAIR = "Fair", "Fair"
        NEEDS_REPAIR = "Needs Repair", "Needs Repair"

    # Status barang
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
    # Batas atas menjaga nilai tetap muat di kolom integer 32-bit PostgreSQL (SQLite tidak mengeluh, PostgreSQL error).
    price = models.PositiveIntegerField(
        "Harga (Rp)",
        validators=[MaxValueValidator(MAX_PRICE, message="Harga maksimal Rp 100.000.000.")],
    )
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

    @property
    def sustainability_tags(self):
        """Label tag keberlanjutan yang dipilih penjual (fakta dari penjual, bukan klaim dampak)."""
        names = ("is_repairable", "is_upcycled", "is_locally_available", "extends_clothing_life")
        return [self._meta.get_field(name).verbose_name for name in names if getattr(self, name)]

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
