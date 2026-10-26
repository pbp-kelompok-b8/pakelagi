import re

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator

# Pola penanda alamat rumah, misal "Jl. Merdeka No. 5", "Gang Kelinci", atau "RT 05".
# Kata penandanya harus berdiri sendiri (\b = batas kata), supaya nama tempat nyata seperti
# "Jalancagak" atau "Nobel" tidak ikut ditolak. re.IGNORECASE = huruf besar-kecil tidak dibedakan.
HOME_ADDRESS_PATTERN = re.compile(
    r"\b(jalan|jl|gang|gg|nomor)\b\.?\s*\S+|\b(no|rt|rw)\b\.?\s*\d+",
    re.IGNORECASE,
)


def validate_http_url(value):
    # Gambar listing boleh HTTP atau HTTPS. Skema lain (ftp, javascript, dll.) ditolak.
    try:
        URLValidator(schemes=["http", "https"])(value)
    except ValidationError:
        raise ValidationError("Gunakan URL gambar HTTP atau HTTPS yang valid.")


def validate_no_home_address(value):
    # Lokasi listing hanya kota/area umum, bukan alamat rumah atau titik pickup yang presisi.
    if HOME_ADDRESS_PATTERN.search(value):
        raise ValidationError("Jangan cantumkan alamat rumah; gunakan nama kota atau area umum saja.")
