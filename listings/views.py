from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import Http404, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.cache import patch_vary_headers
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from listings.filters import SORT_LABELS, TAG_LABELS, CatalogQuery
from listings.forms import ListingForm
from listings.models import MAX_PRICE, Listing
from profiles.access import member_required
from profiles.models import Profile
from profiles.profile_contacts import contact_context

CATALOG_PAGE_SIZE = 12
MINE_PAGE_SIZE = 6

# Nilai ?status= di halaman "Listing saya" -> status di database.
MINE_TABS = {
    "tersedia": Listing.Status.AVAILABLE,
    "terjual": Listing.Status.SOLD,
    "disembunyikan": Listing.Status.HIDDEN,
}


def _page_number(request):
    """Nomor halaman dari ?page=. Bawaan Django melompat ke halaman TERAKHIR untuk 0 atau -1; di sini jadi halaman 1."""
    try:
        return max(int(request.GET.get("page", 1)), 1)
    except (TypeError, ValueError):
        return 1


def _href(querystring=""):
    url = reverse("listings:list")
    return f"{url}?{querystring}" if querystring else url


def _page_links(query, page):
    """Nomor halaman (dengan elipsis) yang tiap tautannya mempertahankan pencarian dan filter."""
    links = []
    for number in page.paginator.get_elided_page_range(page.number, on_each_side=1, on_ends=1):
        if number == Paginator.ELLIPSIS:
            links.append({"ellipsis": True})
        else:
            links.append({"number": number, "href": _href(query.querystring(page=number)), "current": number == page.number})
    return links


@require_GET
def listing_list(request):
    query = CatalogQuery.from_query(request.GET)

    # Katalog publik: hanya Available. Sold dan Hidden tidak pernah tampil di sini.
    available = Listing.objects.filter(status=Listing.Status.AVAILABLE)
    page = Paginator(query.apply(available), CATALOG_PAGE_SIZE).get_page(_page_number(request))

    # Kota ditampilkan sekali saja meski penulisannya berbeda huruf besar/kecil.
    cities = {}
    for city in available.values_list("city", flat=True).distinct():
        cities.setdefault(city.casefold(), city)

    context = {
        "query": query,
        "page": page,
        "total_count": available.count(),
        "results_count": page.paginator.count,
        "page_links": _page_links(query, page),
        "prev_href": _href(query.querystring(page=page.previous_page_number())) if page.has_previous() else "",
        "next_href": _href(query.querystring(page=page.next_page_number())) if page.has_next() else "",
        "tabs": [
            {"label": label, "href": _href(query.with_(category=value).querystring()), "active": query.category == value}
            for value, label in (("", "Semua"), *Listing.Category.choices)
        ],
        "chips": [(label, _href(without.querystring())) for label, without in query.chips()],
        "sort_options": list(SORT_LABELS.items()),
        "size_choices": Listing.Size.choices,
        "condition_choices": Listing.Condition.choices,
        "tag_choices": list(TAG_LABELS.items()),
        "city_choices": sorted(cities.values(), key=str.casefold),
        "price_presets": [
            ("< 100rb", _href(query.with_(price_min=None, price_max=100_000).querystring())),
            ("100–250rb", _href(query.with_(price_min=100_000, price_max=250_000).querystring())),
            ("> 250rb", _href(query.with_(price_min=250_000, price_max=None).querystring())),
        ],
        "max_price": MAX_PRICE,
    }

    # HTMX hanya meminta bagian hasilnya. Pemulihan riwayat (tombol back) butuh halaman penuh.
    is_htmx = request.headers.get("HX-Request") == "true" and request.headers.get("HX-History-Restore-Request") != "true"
    if is_htmx:
        response = render(request, "listings/components/results.html", {**context, "partial": True})
    else:
        response = render(request, "listings/list.html", context)
    # URL yang sama menghasilkan HTML berbeda tergantung jenis permintaan: jangan campur di cache.
    patch_vary_headers(response, ["HX-Request", "HX-History-Restore-Request", "Cookie"])
    return response


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
    page = Paginator(mine.order_by("-updated_at", "-id"), MINE_PAGE_SIZE).get_page(_page_number(request))
    return render(request, "listings/mine.html", {
        "page": page,
        "tab": tab,
        "counts": counts,
    })
