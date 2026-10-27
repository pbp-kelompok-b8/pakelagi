from urllib.parse import urlencode

from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from favorites.access import favorite_member_required
from favorites.forms import FavoriteNoteForm
from favorites.models import Favorite
from listings.filters import get_catalog_filter
from listings.models import Listing
from profiles.access import safe_profile_next


def list_context(request):
    category = get_catalog_filter(request.GET)["category"]
    favorites = Favorite.objects.filter(
        user=request.user, listing__status__in=[Listing.Status.AVAILABLE, Listing.Status.SOLD],
    ).select_related("listing")
    total_count = favorites.count()
    if category:
        favorites = favorites.filter(listing__category=category)
    url = reverse("favorites:list")
    tabs = [{
        "label": label,
        "href": url + "?" + urlencode({"category": value}) if value else url,
        "active": value == category,
    } for value, label in [("", "Semua"), *Listing.Category.choices]]
    return {"favorites": favorites, "category": category, "tabs": tabs, "total_count": total_count}


@favorite_member_required
@require_GET
def favorite_list(request):
    return render(request, "favorites/list.html", list_context(request))


@favorite_member_required
@require_POST
def favorite_add(request, listing_id):
    listing = get_object_or_404(
        Listing.objects.filter(status=Listing.Status.AVAILABLE).exclude(seller=request.user), pk=listing_id,
    )
    Favorite.objects.get_or_create(user=request.user, listing=listing)
    target = safe_profile_next(request, request.POST.get("next"))
    return redirect(target or reverse("listings:detail", args=[listing.pk]))


@favorite_member_required
@require_POST
def favorite_remove(request, listing_id):
    # Tidak membaca detail listing: favorit lama tetap bisa dihapus setelah Sold/Hidden.
    Favorite.objects.filter(user=request.user, listing_id=listing_id).delete()
    target = safe_profile_next(request, request.POST.get("next"))
    return redirect(target or "favorites:list")


@favorite_member_required
@require_http_methods(["GET", "POST"])
def favorite_edit(request, pk):
    favorite = get_object_or_404(
        Favorite.objects.select_related("listing").filter(
            user=request.user, listing__status__in=[Listing.Status.AVAILABLE, Listing.Status.SOLD],
        ), pk=pk,
    )
    form = FavoriteNoteForm(request.POST if request.method == "POST" else None, instance=favorite)
    if request.method == "POST" and form.is_valid():
        favorite.note = form.cleaned_data["note"]
        favorite.save(update_fields=["note", "updated_at"])
        return redirect("favorites:list")
    return render(request, "favorites/edit.html", {"form": form, "favorite": favorite})
