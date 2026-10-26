from django import forms

from listings.models import Listing
from listings.validators import validate_no_home_address

# (nilai, label, penjelasan, jumlah garis terisi pada indikator kondisi)
CONDITION_OPTIONS = [
    (Listing.Condition.LIKE_NEW.value, "Like New", "Hampir tak terlihat pernah dipakai.", 4),
    (Listing.Condition.GOOD.value, "Good", "Tanda pakai wajar, tanpa cacat.", 3),
    (Listing.Condition.FAIR.value, "Fair", "Ada cacat kecil — sebutkan di deskripsi.", 2),
    (Listing.Condition.NEEDS_REPAIR.value, "Needs Repair", "Perlu diperbaiki sebelum dipakai.", 1),
]


class ListingForm(forms.ModelForm):
    """Form untuk penjual. Sengaja TIDAK memuat seller, status, sold_at, dan koordinat:

    - seller diisi view dari akun yang login (bukan dari input),
    - status hanya berubah lewat aksi khusus (supaya pemilik tidak bisa membatalkan Hidden dari moderator).
    """

    condition_options = CONDITION_OPTIONS

    class Meta:
        model = Listing
        fields = (
            "image_url", "title", "brand", "category", "size", "condition", "price", "city",
            "is_repairable", "is_upcycled", "is_locally_available", "extends_clothing_life",
            "description",
        )
        widgets = {
            "image_url": forms.URLInput(attrs={"placeholder": "https://..."}),
            "price": forms.NumberInput(attrs={"min": 0, "inputmode": "numeric"}),
            "description": forms.Textarea(attrs={"rows": 5}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Pilihan ditampilkan sebagai chip/kartu tanpa opsi kosong "---------".
        self.fields["category"].choices = Listing.Category.choices
        self.fields["size"].choices = Listing.Size.choices
        self.fields["condition"].choices = Listing.Condition.choices

    def clean_city(self):
        city = self.cleaned_data["city"]
        validate_no_home_address(city)
        return city
