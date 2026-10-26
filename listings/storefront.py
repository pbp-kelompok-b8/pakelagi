# Daftar barang untuk etalase profil penjual. Dipanggil oleh profiles/storefront.py (listing_context).
from django.db.models import Count, F, Q

from listings.models import Listing

STOREFRONT_PAGE_SIZE = 8     # jumlah barang yang dimuat setiap kali
SOLD_PREVIEW_SIZE = 4        # cuplikan "Baru saja terjual" di tab Dijual
MAX_LOADED_PAGES = 500       # batas ?page= supaya angka sangat besar tidak membuat LIMIT raksasa di database

# Nama urutan di URL -> kolom untuk order_by. id jadi pembeda tetap supaya barang yang harganya sama
# tidak bertukar tempat di antara pemuatan.
STOREFRONT_SORT = {
    "terbaru": ["-created_at", "-id"],
    "harga_terendah": ["price", "id"],
    "harga_tertinggi": ["-price", "id"],
}


def for_profile(seller_id, viewer, selection):
    # selection adalah StorefrontSelection (tab, sort, page) dari profiles/storefront.py.
    # viewer belum dipakai di sini; nanti dipakai modul Favorit untuk tahu barang mana yang sudah disimpan.

    # Etalase hanya menampilkan Available dan Sold. Hidden (termasuk yang disembunyikan moderator)
    # tidak ikut dihitung dan tidak ditampilkan, bahkan ketika pemiliknya sendiri yang membuka.
    public = Listing.objects.filter(
        seller_id=seller_id,
        status__in=[Listing.Status.AVAILABLE, Listing.Status.SOLD],
    )

    # Jumlah total per status. Ini angka sebenarnya di database, bukan jumlah kartu yang sudah dimuat.
    counts = public.aggregate(
        available=Count("pk", filter=Q(status=Listing.Status.AVAILABLE)),
        sold=Count("pk", filter=Q(status=Listing.Status.SOLD)),
    )
    available_count = counts["available"]
    sold_count = counts["sold"]

    if selection.tab == "terjual":
        status = Listing.Status.SOLD
        total = sold_count
    else:
        status = Listing.Status.AVAILABLE
        total = available_count

    # Pemuatan bersifat kumulatif: ?page=3 langsung menampilkan 3 x 8 barang pertama sekaligus.
    # Jadi halaman bisa dibuka langsung dari URL (atau tombol back) tanpa JavaScript.
    page = min(selection.page, MAX_LOADED_PAGES)
    listings = list(public.filter(status=status).order_by(*STOREFRONT_SORT[selection.sort])[:page * STOREFRONT_PAGE_SIZE])

    remaining = total - len(listings)
    has_more = remaining > 0 and page < MAX_LOADED_PAGES

    # Cuplikan Sold hanya di tab Dijual: 4 terakhir berdasarkan kapan barangnya ditandai terjual.
    # nulls_last: barang Sold lama yang sold_at-nya kosong ditaruh paling akhir, bukan paling awal.
    sold_preview = []
    if selection.tab != "terjual":
        sold_listings = public.filter(status=Listing.Status.SOLD)
        sold_preview = list(sold_listings.order_by(F("sold_at").desc(nulls_last=True), "-id")[:SOLD_PREVIEW_SIZE])

    return {
        "available_count": available_count,
        "sold_count": sold_count,
        "listings": listings,
        "sold_preview": sold_preview,
        "has_more": has_more,
        "next_count": min(STOREFRONT_PAGE_SIZE, max(remaining, 0)),   # label tombol: "Muat 8 lagi" atau sisanya
        "next_page": page + 1,
    }
