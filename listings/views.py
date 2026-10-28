from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import Http404, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.cache import patch_vary_headers
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from listings import nominatim
from listings.filters import (SORT_LABELS, TAG_LABELS, build_querystring, change_filter, filter_listings,
                              get_catalog_filter, get_filter_chips, is_filtered)
from listings.forms import ListingForm
from listings.models import MAX_PRICE, Listing
from favorites.presentation import with_favorite_state
from profiles.access import has_complete_profile, member_required
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


def get_page_number(request):
    # Baca ?page= dari URL. Kalau pakai bawaan Django, ?page=0 atau ?page=-1 melompat ke halaman TERAKHIR,
    # jadi di sini kita buat angka di bawah 1 dianggap halaman 1.
    try:
        number = int(request.GET.get("page", 1))
    except ValueError:
        return 1
    if number < 1:
        return 1
    return number


def build_href(querystring=""):
    # Contoh: "/listings/?size=M". Kalau querystring kosong, hasilnya "/listings/" saja.
    url = reverse("listings:list")
    if querystring:
        return url + "?" + querystring
    return url


def build_page_links(catalog_filter, page):
    # Nomor halaman untuk pagination (dengan "..." kalau halamannya banyak).
    # Tiap tautan membawa pencarian dan filter yang sedang aktif.
    links = []
    page_range = page.paginator.get_elided_page_range(page.number, on_each_side=1, on_ends=1)
    for number in page_range:
        if number == Paginator.ELLIPSIS:
            links.append({"ellipsis": True})
        else:
            links.append({
                "number": number,
                "href": build_href(build_querystring(catalog_filter, page=number)),
                "current": number == page.number,
            })
    return links


@cache_control(private=True, no_store=True)
@require_GET
def listing_list(request):
    catalog_filter = get_catalog_filter(request.GET)

    # Katalog publik hanya yang Available. Sold dan Hidden tidak pernah tampil di sini.
    available = Listing.objects.filter(status=Listing.Status.AVAILABLE)
    results = with_favorite_state(filter_listings(available, catalog_filter), request.user)
    page = Paginator(results, CATALOG_PAGE_SIZE).get_page(get_page_number(request))

    # Daftar kota untuk dropdown. Kota yang sama (beda huruf besar-kecil) cukup muncul sekali.
    cities = []
    sudah_ada = []
    for city in available.values_list("city", flat=True).distinct():
        if city.casefold() not in sudah_ada:
            sudah_ada.append(city.casefold())
            cities.append(city)
    cities.sort(key=str.casefold)

    # Link halaman sebelum/sesudahnya (kosong kalau tidak ada)
    prev_href = ""
    if page.has_previous():
        prev_href = build_href(build_querystring(catalog_filter, page=page.previous_page_number()))
    next_href = ""
    if page.has_next():
        next_href = build_href(build_querystring(catalog_filter, page=page.next_page_number()))

    # Tab kategori: "Semua" + tiap kategori. Pencarian dan filter lain tetap dibawa.
    tab_options = [("", "Semua")] + list(Listing.Category.choices)
    tabs = []
    for value, label in tab_options:
        tabs.append({
            "label": label,
            "href": build_href(build_querystring(change_filter(catalog_filter, category=value))),
            "active": catalog_filter["category"] == value,
        })

    # Chip filter aktif. Tiap chip berisi (label, link untuk menghapus filter itu)
    chips = []
    for label, filter_without in get_filter_chips(catalog_filter):
        chips.append((label, build_href(build_querystring(filter_without))))

    # Tombol cepat rentang harga
    price_presets = [
        ("< 100rb", change_filter(catalog_filter, price_min=None, price_max=100000)),
        ("100–250rb", change_filter(catalog_filter, price_min=100000, price_max=250000)),
        ("> 250rb", change_filter(catalog_filter, price_min=250000, price_max=None)),
    ]
    price_presets = [(label, build_href(build_querystring(f))) for label, f in price_presets]

    context = {
        "query": catalog_filter,
        "is_filtered": is_filtered(catalog_filter),
        "page": page,
        "total_count": available.count(),
        "results_count": page.paginator.count,
        "page_links": build_page_links(catalog_filter, page),
        "prev_href": prev_href,
        "next_href": next_href,
        "tabs": tabs,
        "chips": chips,
        "sort_options": list(SORT_LABELS.items()),
        "size_choices": Listing.Size.choices,
        "condition_choices": Listing.Condition.choices,
        "tag_choices": list(TAG_LABELS.items()),
        "city_choices": cities,
        "price_presets": price_presets,
        "max_price": MAX_PRICE,
    }

    # HTMX cuma butuh bagian hasilnya. Tombol back browser butuh halaman penuh.
    is_htmx = request.headers.get("HX-Request") == "true"
    is_history_restore = request.headers.get("HX-History-Restore-Request") == "true"
    if is_htmx and not is_history_restore:
        context["partial"] = True
        response = render(request, "listings/components/results.html", context)
    else:
        response = render(request, "listings/list.html", context)

    # URL yang sama bisa menghasilkan HTML berbeda (penuh atau potongan), jadi cache jangan mencampurnya
    patch_vary_headers(response, ["HX-Request", "HX-History-Restore-Request", "Cookie"])
    return response


# Isi halaman bergantung pada siapa yang melihat (kontak penjual), jadi jangan disimpan cache bersama.
@cache_control(private=True, no_store=True)
@require_GET
def listing_detail(request, pk):
    listing = get_object_or_404(with_favorite_state(Listing.objects.select_related("seller"), request.user), pk=pk)
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
    response = render(request, "listings/detail.html", {
        "listing": listing,
        "seller_profile": profile,
        "is_owner": is_owner,
        "more_from_seller": with_favorite_state(seller_listings.exclude(pk=listing.pk), viewer)[:4],
        "seller_active_count": seller_listings.count(),
        **contact,
    })
    patch_vary_headers(response, ["Cookie"])
    return response


def get_manageable_listing(request, pk, owner_only=False):
    # Listing yang boleh diubah user ini: miliknya sendiri, atau milik siapa pun kalau dia admin.
    # Selain itu hasilnya 404 (bukan 403), supaya orang luar tidak bisa menebak listing mana yang ada.
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
    listing = get_manageable_listing(request, pk)
    form = ListingForm(request.POST or None, instance=listing)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Perubahan listing disimpan.")
        return redirect("listings:detail", pk=listing.pk)
    return render(request, "listings/form.html", {"form": form, "listing": listing})


@member_required
@require_http_methods(["GET", "POST"])
def listing_delete(request, pk):
    listing = get_manageable_listing(request, pk)
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
    listing = get_manageable_listing(request, pk, owner_only=True)
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
    page = Paginator(mine.order_by("-updated_at", "-id"), MINE_PAGE_SIZE).get_page(get_page_number(request))
    return render(request, "listings/mine.html", {
        "page": page,
        "tab": tab,
        "counts": counts,
    })


@require_GET
def location_search(request):
    # Saran kota/area untuk form listing. HTMX memanggil ini saat penjual mengetik di kolom kota.
    # Hanya member berprofil lengkap yang boleh, karena endpoint ini memicu request keluar ke Nominatim
    # yang dibatasi 1 request per detik. Kalau terbuka untuk semua orang, jatahnya bisa dihabiskan satu orang.
    # Kegagalan apa pun tetap membalas 200 dengan pesan, supaya penjual bisa mengetik kotanya sendiri.
    if not has_complete_profile(request.user):
        return HttpResponse(status=403)
    query = " ".join(request.GET.get("city", "").split())[:nominatim.MAX_QUERY_LENGTH]
    results, status = nominatim.search(query)

    context = {
        "results": results,
        "status": status,
        "query": query,
    }
    response = render(request, "listings/components/location_results.html", context)
    response["Cache-Control"] = "private, no-store"
    return response
