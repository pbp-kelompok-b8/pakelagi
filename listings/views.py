from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import Http404, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from listings.forms import ListingForm
from listings.models import Listing
from profiles.access import member_required
from profiles.models import Profile
from profiles.profile_contacts import contact_context

MINE_PAGE_SIZE = 6

# Nilai ?status= di halaman "Listing saya" -> status di database.
MINE_TABS = {
    "tersedia": Listing.Status.AVAILABLE,
    "terjual": Listing.Status.SOLD,
    "disembunyikan": Listing.Status.HIDDEN,
}


@require_GET
def listing_list(request):
    # Katalog publik: hanya Available. Sold dan Hidden tidak pernah tampil di sini.
    listings = Listing.objects.filter(status=Listing.Status.AVAILABLE)
    return render(request, "listings/list.html", {
        "listings": listings,
        "total_count": listings.count(),
    })


# Isi halaman bergantung pada siapa yang melihat (kontak penjual), jadi jangan disimpan cache bersama.
@cache_control(private=True, no_store=True)
@require_GET
def listing_detail(request, pk):
    listing = get_object_or_404(Listing.objects.select_related("seller"), pk=pk)
    viewer = request.user
    is_owner = viewer.is_authenticated and viewer.pk == listing.seller_id

    # Hidden (termasuk hasil moderasi) hanya boleh dilihat penjual dan admin.
    if listing.status == Listing.Status.HIDDEN and not (is_owner or viewer.is_staff):
        raise Http404

    # Penjual mungkin belum/tidak lagi punya profil: halaman tetap harus utuh tanpa itu.
    profile = Profile.objects.filter(user_id=listing.seller_id).first()
    if profile and not profile.display_name.strip():
        profile = None

    # Kontak hanya relevan untuk barang yang masih dijual milik orang lain.
    contact = {}
    if profile and not is_owner and listing.status == Listing.Status.AVAILABLE:
        contact = contact_context(request, profile)

    seller_listings = Listing.objects.filter(seller_id=listing.seller_id, status=Listing.Status.AVAILABLE)
    return render(request, "listings/detail.html", {
        "listing": listing,
        "seller_profile": profile,
        "is_owner": is_owner,
        "more_from_seller": seller_listings.exclude(pk=listing.pk)[:4],
        "seller_active_count": seller_listings.count(),
        **contact,
    })


def _manageable_listing_or_404(request, pk, *, owner_only=False):
    """Listing yang boleh diubah user ini: miliknya sendiri, atau siapa pun jika admin.

    Selain itu 404 (bukan 403) supaya orang luar tidak bisa menebak listing mana yang ada.
    """
    listing = get_object_or_404(Listing, pk=pk)
    is_owner = listing.seller_id == request.user.pk
    if not is_owner and (owner_only or not request.user.is_staff):
        raise Http404
    return listing


@member_required
@require_http_methods(["GET", "POST"])
def listing_create(request):
    form = ListingForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        listing = form.save(commit=False)
        listing.seller = request.user  # selalu dari akun yang login, tidak pernah dari input
        listing.save()
        messages.success(request, "Listing berhasil diterbitkan.")
        return redirect("listings:detail", pk=listing.pk)
    return render(request, "listings/form.html", {"form": form, "listing": None})


@member_required
@require_http_methods(["GET", "POST"])
def listing_edit(request, pk):
    listing = _manageable_listing_or_404(request, pk)
    form = ListingForm(request.POST or None, instance=listing)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Perubahan listing disimpan.")
        return redirect("listings:detail", pk=listing.pk)
    return render(request, "listings/form.html", {"form": form, "listing": listing})


@member_required
@require_http_methods(["GET", "POST"])
def listing_delete(request, pk):
    listing = _manageable_listing_or_404(request, pk)
    if request.method == "POST":
        title = listing.title
        listing.delete()
        messages.success(request, f"Listing “{title}” dihapus.")
        return redirect("listings:mine")
    return render(request, "listings/confirm_delete.html", {"listing": listing})


@member_required
@require_POST
def listing_set_status(request, pk):
    """Penjual menandai listing miliknya Terjual atau Tersedia lagi."""
    listing = _manageable_listing_or_404(request, pk, owner_only=True)
    new_status = request.POST.get("status")
    if new_status not in (Listing.Status.AVAILABLE, Listing.Status.SOLD):
        return HttpResponseBadRequest("Status tidak valid.")
    if listing.status == Listing.Status.HIDDEN:
        messages.error(request, "Listing yang disembunyikan moderator tidak bisa diubah statusnya.")
        return redirect("listings:mine")
    if listing.status != new_status:
        listing.status = new_status
        listing.save(update_fields=["status", "updated_at"])
        messages.success(
            request,
            "Listing ditandai terjual." if new_status == Listing.Status.SOLD else "Listing tersedia kembali.",
        )
    return redirect("listings:mine")


@member_required
@require_GET
def listing_mine(request):
    mine = Listing.objects.filter(seller=request.user)
    counts = mine.aggregate(
        all=Count("pk"),
        tersedia=Count("pk", filter=Q(status=Listing.Status.AVAILABLE)),
        terjual=Count("pk", filter=Q(status=Listing.Status.SOLD)),
        disembunyikan=Count("pk", filter=Q(status=Listing.Status.HIDDEN)),
    )
    tab = request.GET.get("status", "")
    if tab not in MINE_TABS:
        tab = ""
    if tab:
        mine = mine.filter(status=MINE_TABS[tab])
    page = Paginator(mine.order_by("-updated_at", "-id"), MINE_PAGE_SIZE).get_page(request.GET.get("page"))
    return render(request, "listings/mine.html", {
        "page": page,
        "tab": tab,
        "counts": counts,
    })
