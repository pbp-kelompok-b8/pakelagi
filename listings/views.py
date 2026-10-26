from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET

from listings.models import Listing
from profiles.models import Profile
from profiles.profile_contacts import contact_context


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
