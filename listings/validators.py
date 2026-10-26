from django.core.exceptions import ValidationError
from django.core.validators import URLValidator


def validate_http_url(value):
    """Gambar listing boleh HTTP atau HTTPS; skema lain (ftp, javascript, dll.) ditolak."""
    try:
        URLValidator(schemes=["http", "https"])(value)
    except ValidationError:
        raise ValidationError("Gunakan URL gambar HTTP atau HTTPS yang valid.")
