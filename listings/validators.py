import re

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator

# Kata penanda alamat rumah. Kata harus berdiri sendiri (\b) supaya nama tempat seperti
# "Jalancagak" atau "Nobel" tidak ikut ditolak.
_HOME_ADDRESS = re.compile(
    r"\b(jalan|jl|gang|gg|nomor)\b\.?\s*\S+|\b(no|rt|rw)\b\.?\s*\d+",
    re.IGNORECASE,
)


def validate_http_url(value):
    """Gambar listing boleh HTTP atau HTTPS; skema lain (ftp, javascript, dll.) ditolak."""
    try:
        URLValidator(schemes=["http", "https"])(value)
    except ValidationError:
        raise ValidationError("Gunakan URL gambar HTTP atau HTTPS yang valid.")


def validate_no_home_address(value):
    """Lokasi listing hanya kota/area umum, bukan alamat rumah atau titik pickup presisi."""
    if _HOME_ADDRESS.search(value):
        raise ValidationError("Jangan cantumkan alamat rumah; gunakan nama kota atau area umum saja.")
