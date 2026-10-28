from urllib.parse import urlencode

from django.db.models import BooleanField, Exists, OuterRef, Value
from django.urls import reverse

from favorites.models import Favorite
from listings.models import Listing
from profiles.access import has_complete_profile, onboarding_url


def with_favorite_state(listings, user):
    # Subquery pada query listing, bukan satu query tambahan per kartu.
    saved = Value(False, output_field=BooleanField())
    if user.is_authenticated:
        saved = Exists(Favorite.objects.filter(user=user, listing_id=OuterRef("pk")))
    return listings.annotate(is_favorited=saved)


def favorite_context(request):
    return {"favorite_member": has_complete_profile(request.user)}


def button_context(request, listing, *, member, slot="card", return_to=None):
    slot = slot if slot in {"card", "detail"} else "card"
    target = request.get_full_path() if return_to is None else return_to
    saved = bool(getattr(listing, "is_favorited", False))
    invite_url = ""
    invite_label = ""
    if not request.user.is_authenticated:
        invite_url = reverse("accounts:login") + "?" + urlencode({"next": target})
        invite_label = "Masuk untuk menyimpan favorit"
    elif not member:
        invite_url = onboarding_url(target)
        invite_label = "Lengkapi profil untuk menyimpan favorit"
    can_show = listing.status != Listing.Status.HIDDEN and listing.seller_id != request.user.pk
    can_show = can_show and (saved or listing.status == Listing.Status.AVAILABLE)
    return {
        "listing": listing, "saved": saved, "show_button": can_show, "invite_url": invite_url,
        "invite_label": invite_label, "slot": slot, "return_to": target,
        "component_id": f"favorite-{slot}-{listing.pk}",
    }
