from favorites.models import Favorite
from listings.models import Listing


def favoritable_listings(user):
    return Listing.objects.filter(status=Listing.Status.AVAILABLE).exclude(seller=user)


def visible_favorites(user):
    return Favorite.objects.filter(
        user=user, listing__status__in=[Listing.Status.AVAILABLE, Listing.Status.SOLD],
    ).select_related("listing")


def editable_favorites(user):
    # Lock the listing until the note write finishes so moderation cannot change its visibility.
    return visible_favorites(user).select_for_update(of=("listing",))
