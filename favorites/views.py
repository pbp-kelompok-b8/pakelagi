import json
from urllib.parse import urlencode

from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from favorites.access import favorite_member_required
from favorites.forms import FavoriteNoteForm
from favorites.models import Favorite
from favorites.presentation import button_context
from listings.filters import get_catalog_filter
from listings.models import Listing
from profiles.access import safe_profile_next


def is_partial(request):
    return request.headers.get("HX-Request") == "true" and request.headers.get("HX-History-Restore-Request") != "true"


def list_context(request, params=None):
    category = get_catalog_filter(request.GET if params is None else params)["category"]
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
    return {
        "favorites": favorites, "category": category, "tabs": tabs, "total_count": total_count,
        "favorites_return_to": url + "?" + urlencode({"category": category}) if category else url,
    }


@favorite_member_required
@require_GET
def favorite_list(request):
    template = "favorites/components/results.html" if is_partial(request) else "favorites/list.html"
    return render(request, template, list_context(request))


def mutation_response(request, listing_id, saved, listing=None):
    if request.POST.get("surface") == "list":
        response = render(request, "favorites/components/results.html", list_context(request, request.POST))
    else:
        listing = listing or Listing.objects.filter(pk=listing_id).first()
        slot = request.POST.get("slot", "card")
        slot = slot if slot in {"card", "detail"} else "card"
        context = {"component_id": f"favorite-{slot}-{listing_id}", "show_button": False}
        if listing:
            listing.is_favorited = saved
            target = safe_profile_next(request, request.POST.get("next")) or reverse("listings:detail", args=[listing_id])
            context = button_context(request, listing, member=True, slot=slot, return_to=target)
        response = render(request, "favorites/components/button.html", context)
    response["HX-Trigger"] = json.dumps({"favoriteChanged": {"listingId": listing_id, "saved": saved}})
    return response


@favorite_member_required
@require_POST
def favorite_add(request, listing_id):
    listing = get_object_or_404(
        Listing.objects.filter(status=Listing.Status.AVAILABLE).exclude(seller=request.user), pk=listing_id,
    )
    Favorite.objects.get_or_create(user=request.user, listing=listing)
    if is_partial(request):
        return mutation_response(request, listing.pk, True, listing)
    target = safe_profile_next(request, request.POST.get("next"))
    return redirect(target or reverse("listings:detail", args=[listing.pk]))


@favorite_member_required
@require_POST
def favorite_remove(request, listing_id):
    # Tidak membaca detail listing: favorit lama tetap bisa dihapus setelah Sold/Hidden.
    Favorite.objects.filter(user=request.user, listing_id=listing_id).delete()
    if is_partial(request):
        return mutation_response(request, listing_id, False)
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
    form = FavoriteNoteForm(
        request.POST if request.method == "POST" else None, instance=favorite, auto_id=f"favorite-{favorite.pk}-%s",
    )
    target = safe_profile_next(request, request.POST.get("next") or request.GET.get("next"))
    if request.method == "POST" and form.is_valid():
        favorite.note = form.cleaned_data["note"]
        favorite.save(update_fields=["note", "updated_at"])
        if is_partial(request):
            return render(request, "favorites/components/note.html", {
                "favorite": favorite, "saved": True, "return_to": target,
            })
        return redirect(target or "favorites:list")
    template = "favorites/components/note_form.html" if is_partial(request) else "favorites/edit.html"
    return render(request, template, {"form": form, "favorite": favorite, "return_to": target})
