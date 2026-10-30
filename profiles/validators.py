import ipaddress
import re
from urllib.parse import urlsplit

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator


def normalize_instagram_contact(value):
    message = "Masukkan handle atau URL profil Instagram yang valid."
    handle = value.removeprefix("@")
    if ":" in value or "/" in value:
        try:
            parsed = urlsplit(value)
            if parsed.scheme not in {"http", "https"} or parsed.netloc.lower() not in {"instagram.com", "www.instagram.com"}:
                raise ValueError
            if parsed.query or parsed.fragment or "?" in value or "#" in value:
                raise ValueError
            match = re.fullmatch(r"/([A-Za-z0-9_.]+)/?", parsed.path)
            if not match:
                raise ValueError
            handle = match.group(1)
        except ValueError:
            raise ValidationError(message)
    if (
        not re.fullmatch(r"[A-Za-z0-9_](?:[A-Za-z0-9_.]{0,28}[A-Za-z0-9_])?", handle)
        or ".." in handle
        or handle.lower() in {"p", "reel", "reels", "stories", "explore", "accounts", "direct", "about", "developer", "legal", "web"}
    ):
        raise ValidationError(message)
    return handle.lower()


def validate_external_https_url(value):
    """Validate syntax only; never resolve or fetch user-provided image URLs."""
    if not value:
        return
    message = "Gunakan URL HTTPS eksternal yang valid tanpa kredensial."
    try:
        URLValidator(schemes=["https"])(value)
        parsed = urlsplit(value)
        host = (parsed.hostname or "").lower().rstrip(".")
        if parsed.scheme != "https" or parsed.username is not None or parsed.password is not None:
            raise ValueError
        if "." not in host or host.endswith((".localhost", ".local", ".internal")):
            raise ValueError
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            pass
        else:
            if not address.is_global:
                raise ValueError
    except (ValueError, ValidationError):
        raise ValidationError(message)
