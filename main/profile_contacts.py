"""Build only the seller contact data the current viewer may receive."""
from urllib.parse import urlencode, urlsplit

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.urls import reverse

from main.access import has_complete_profile, onboarding_url, safe_profile_next


def contact_context(request, profile):
    if not has_complete_profile(request.user):
        target = safe_profile_next(request, request.get_full_path())
        return {
            "contact_invite_url": onboarding_url(target) if request.user.is_authenticated else reverse("main:login") + "?" + urlencode({"next": target}),
            "contact_invite_label": "Lengkapi profil untuk melihat kontak" if request.user.is_authenticated else "Masuk untuk melihat kontak",
        }
    value = profile.contact_value
    label = value
    url = ""
    cta = ""
    if value and profile.contact_type == "instagram":
        from main.validators import normalize_instagram_contact
        try:
            handle = normalize_instagram_contact(value)
            label, url, cta = "@" + handle, "https://www.instagram.com/" + handle + "/", "Hubungi via Instagram"
        except ValidationError:
            pass
    elif value and profile.contact_type == "email":
        from django.core.validators import validate_email
        try:
            validate_email(value)
            url, cta = "mailto:" + value, "Hubungi via email"
        except ValidationError:
            pass
    elif value and profile.contact_type == "other":
        try:
            URLValidator(schemes=["http", "https"])(value)
            if not urlsplit(value).username and not urlsplit(value).password:
                url, cta = value, "Buka kontak penjual"
        except (ValidationError, ValueError):
            pass
    return {"seller_contact": {"value": label, "url": url, "cta": cta, "phone": profile.phone_number}}
