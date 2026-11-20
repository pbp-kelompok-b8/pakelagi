from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone

from favorites.models import Favorite
from favorites.querysets import favoritable_listings


@transaction.atomic
def save_favorite(user, listing_id):
    listing = get_object_or_404(favoritable_listings(user).select_for_update(), pk=listing_id)
    favorite, created = Favorite.objects.get_or_create(user=user, listing=listing)
    favorite.listing = listing
    return favorite, created


def save_favorite_note(favorite, note):
    updated_at = timezone.now()
    # UPDATE cannot recreate a favorite deleted by another request.
    if not Favorite.objects.filter(pk=favorite.pk).update(note=note, updated_at=updated_at):
        raise Http404
    favorite.note = note
    favorite.updated_at = updated_at
