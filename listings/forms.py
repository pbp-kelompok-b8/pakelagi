from django import forms
from django.urls import reverse

from listings.models import Listing
from listings.nominatim import is_in_indonesia, parse_coordinate, round_coordinate
from listings.validators import validate_no_home_address

# Pilihan kondisi untuk kartu di form: (nilai, label, penjelasan, jumlah garis yang terisi)
CONDITION_OPTIONS = [
    (Listing.Condition.LIKE_NEW.value, "Like New", "Hampir tak terlihat pernah dipakai.", 4),
    (Listing.Condition.GOOD.value, "Good", "Tanda pakai wajar, tanpa cacat.", 3),
    (Listing.Condition.FAIR.value, "Fair", "Ada cacat kecil — sebutkan di deskripsi.", 2),
    (Listing.Condition.NEEDS_REPAIR.value, "Needs Repair", "Perlu diperbaiki sebelum dipakai.", 1),
]


# Form untuk penjual. Kolom seller, status, dan sold_at sengaja TIDAK ada di sini:
# - seller diisi oleh view dari akun yang sedang login, bukan dari input
# - status hanya berubah lewat aksi khusus, supaya pemilik tidak bisa membatalkan "Hidden" dari moderator
class ListingForm(forms.ModelForm):
    condition_options = CONDITION_OPTIONS

    # Koordinat datang dari saran Nominatim lewat dua kolom tersembunyi. Dibuat CharField supaya nilai sampah
    # tidak memunculkan error di kolom yang tidak terlihat. Pembersihannya ada di clean().
    latitude = forms.CharField(required=False, widget=forms.HiddenInput)
    longitude = forms.CharField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = Listing
        fields = [
            "image_url",
            "title",
            "brand",
            "category",
            "size",
            "condition",
            "price",
            "city",
            "latitude",
            "longitude",
            "is_repairable",
            "is_upcycled",
            "is_locally_available",
            "extends_clothing_life",
            "description",
        ]

        widgets = {
            "image_url": forms.URLInput(attrs={"placeholder": "https://..."}),
            "price": forms.NumberInput(attrs={"min": 0, "inputmode": "numeric"}),
            "description": forms.Textarea(attrs={"rows": 5}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Pilihan ditampilkan sebagai chip/kartu, jadi opsi kosong "---------" kita hilangkan
        self.fields["category"].choices = Listing.Category.choices
        self.fields["size"].choices = Listing.Size.choices
        self.fields["condition"].choices = Listing.Condition.choices

        # Saran kota lewat HTMX: kolom kota mengirim isinya (?city=...) ke endpoint pencarian
        # setiap kali penjual berhenti mengetik selama 500 ms
        self.fields["city"].widget.attrs.update({
            "hx-get": reverse("listings:location_search"),
            "hx-trigger": "input changed delay:500ms",
            "hx-target": "#location-results",
            "hx-swap": "innerHTML",
            "autocomplete": "off",
            "aria-controls": "location-results",
        })

    def clean_city(self):
        city = self.cleaned_data["city"]
        validate_no_home_address(city)
        return city

    def clean(self):
        cleaned = super().clean()

        # Koordinat dari browser tidak boleh dipercaya begitu saja, jadi dicek ulang di sini
        lat = parse_coordinate(cleaned.get("latitude"))
        lon = parse_coordinate(cleaned.get("longitude"))

        coordinates_ok = lat is not None and lon is not None and is_in_indonesia(lat, lon)

        if coordinates_ok:
            lat = round_coordinate(lat)
            lon = round_coordinate(lon)

            # Kalau kota diubah manual tanpa memilih saran (misal JavaScript mati), koordinat lamanya sudah tidak cocok
            if self.instance.pk:
                city_baru = (cleaned.get("city") or "").casefold()
                city_lama = self.instance.city.casefold()
                koordinat_lama = (lat, lon) == (self.instance.latitude, self.instance.longitude)
                if city_baru != city_lama and koordinat_lama:
                    coordinates_ok = False

        # Koordinat yang tidak lolos dibuang diam-diam. Listing tetap bisa terbit dengan kota manual.
        if coordinates_ok:
            cleaned["latitude"] = lat
            cleaned["longitude"] = lon
        else:
            cleaned["latitude"] = None
            cleaned["longitude"] = None

        return cleaned
