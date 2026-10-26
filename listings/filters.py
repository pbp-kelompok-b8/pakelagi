# Pencarian, filter, dan pengurutan katalog.
# Semua nilai datang dari URL (misal ?q=kemeja&size=M), jadi tidak boleh dipercaya begitu saja:
# nilai yang tidak dikenal dibuang, angka dibatasi, dan hasilnya tetap aman (tidak pernah error 500).
from urllib.parse import urlencode

from django.db.models import Q

from listings.models import MAX_PRICE, Listing

# Nama urutan di URL -> kolom untuk order_by. id dipakai sebagai pembeda supaya barang
# yang harganya sama tidak bertukar tempat setiap kali halaman dibuka.
SORT_ORDER = {
    "terbaru": ["-created_at", "-id"],
    "harga_terendah": ["price", "id"],
    "harga_tertinggi": ["-price", "id"],
}
SORT_LABELS = {
    "terbaru": "Terbaru",
    "harga_terendah": "Harga terendah",
    "harga_tertinggi": "Harga tertinggi",
}
DEFAULT_SORT = "terbaru"

# Kunci tag di URL -> kolom boolean di model, dan labelnya untuk ditampilkan
TAG_FIELDS = {
    "repairable": "is_repairable",
    "upcycled": "is_upcycled",
    "local": "is_locally_available",
    "extends": "extends_clothing_life",
}
TAG_LABELS = {
    "repairable": "Bisa diperbaiki",
    "upcycled": "Upcycled",
    "local": "Tersedia lokal",
    "extends": "Memperpanjang usia pakaian",
}

MAX_QUERY_LENGTH = 100
MAX_SEARCH_WORDS = 5


def pick_valid(values, allowed):
    # Ambil nilai yang valid saja. Urutannya ikut daftar resmi, jadi pilihan yang sama
    # selalu menghasilkan URL yang sama (tidak peduli urutan kliknya).
    result = []
    for item in allowed:
        if item in values:
            result.append(item)
    return result


def parse_price(value):
    # Ubah teks jadi angka 0 sampai MAX_PRICE. Kalau bukan angka, hasilnya None (filter diabaikan).
    try:
        number = int(str(value).strip())
    except ValueError:
        return None
    if number < 0:
        return 0
    if number > MAX_PRICE:
        return MAX_PRICE   # dibatasi supaya tidak membuat error di PostgreSQL (kolom integer 32-bit)
    return number


def get_catalog_filter(params):
    # params adalah request.GET. Hasilnya dictionary berisi nilai filter yang sudah bersih.
    category = params.get("category", "")
    if category not in Listing.Category.values:
        category = ""

    sort = params.get("sort", DEFAULT_SORT)
    if sort not in SORT_ORDER:
        sort = DEFAULT_SORT

    price_min = parse_price(params.get("price_min"))
    price_max = parse_price(params.get("price_max"))
    # Kalau terbalik (min lebih besar dari maks), tukar saja
    if price_min is not None and price_max is not None and price_min > price_max:
        price_min, price_max = price_max, price_min

    return {
        "q": " ".join(params.get("q", "").split())[:MAX_QUERY_LENGTH],   # spasi berlebih dirapikan
        "category": category,
        "sizes": pick_valid(params.getlist("size"), Listing.Size.values),
        "conditions": pick_valid(params.getlist("condition"), Listing.Condition.values),
        "price_min": price_min,
        "price_max": price_max,
        "city": " ".join(params.get("city", "").split())[:100],
        "tags": pick_valid(params.getlist("tag"), list(TAG_FIELDS)),
        "sort": sort,
    }


def is_filtered(catalog_filter):
    # True kalau ada pencarian atau filter yang aktif. Pengurutan tidak dihitung sebagai filter.
    f = catalog_filter
    return bool(
        f["q"] or f["category"] or f["sizes"] or f["conditions"] or f["city"] or f["tags"]
        or f["price_min"] is not None or f["price_max"] is not None
    )


def filter_listings(listings, catalog_filter):
    # listings adalah queryset; filter ditumpuk satu per satu
    f = catalog_filter

    # Setiap kata harus cocok di judul ATAU brand (Q object dengan | berarti OR)
    for word in f["q"].split()[:MAX_SEARCH_WORDS]:
        listings = listings.filter(Q(title__icontains=word) | Q(brand__icontains=word))

    if f["category"]:
        listings = listings.filter(category=f["category"])
    if f["sizes"]:
        listings = listings.filter(size__in=f["sizes"])
    if f["conditions"]:
        listings = listings.filter(condition__in=f["conditions"])
    if f["price_min"] is not None:
        listings = listings.filter(price__gte=f["price_min"])
    if f["price_max"] is not None:
        listings = listings.filter(price__lte=f["price_max"])
    if f["city"]:
        listings = listings.filter(city__iexact=f["city"])   # iexact = sama persis, huruf besar-kecil diabaikan

    # Kalau beberapa tag dipilih, barangnya harus punya semuanya
    for tag in f["tags"]:
        listings = listings.filter(**{TAG_FIELDS[tag]: True})

    return listings.order_by(*SORT_ORDER[f["sort"]])


def change_filter(catalog_filter, **changes):
    # Salinan filter dengan beberapa nilai diganti. Filter aslinya tidak berubah.
    new_filter = dict(catalog_filter)
    new_filter.update(changes)
    return new_filter


def build_querystring(catalog_filter, page=None):
    # Susun kembali jadi teks URL, misal "q=kemeja&size=M&page=2". Nilai default tidak ikut ditulis.
    f = catalog_filter
    pairs = []

    if f["q"]:
        pairs.append(("q", f["q"]))
    if f["category"]:
        pairs.append(("category", f["category"]))
    for size in f["sizes"]:
        pairs.append(("size", size))
    for condition in f["conditions"]:
        pairs.append(("condition", condition))
    if f["price_min"] is not None:
        pairs.append(("price_min", f["price_min"]))
    if f["price_max"] is not None:
        pairs.append(("price_max", f["price_max"]))
    if f["city"]:
        pairs.append(("city", f["city"]))
    for tag in f["tags"]:
        pairs.append(("tag", tag))
    if f["sort"] != DEFAULT_SORT:
        pairs.append(("sort", f["sort"]))
    if page and page > 1:
        pairs.append(("page", page))

    return urlencode(pairs)


def format_rupiah(number):
    # 200000 jadi "Rp 200.000" (sama seperti filter rupiah di template)
    return "Rp " + f"{number:,}".replace(",", ".")


def get_filter_chips(catalog_filter):
    # Daftar filter yang sedang aktif untuk ditampilkan sebagai chip. Tiap chip berisi
    # (label, filter tanpa chip itu), jadi mengkliknya menghapus filter tersebut saja.
    f = catalog_filter
    chips = []

    if f["q"]:
        chips.append(("“" + f["q"] + "”", change_filter(f, q="")))
    for size in f["sizes"]:
        sisa = [s for s in f["sizes"] if s != size]
        chips.append((size, change_filter(f, sizes=sisa)))
    for condition in f["conditions"]:
        sisa = [c for c in f["conditions"] if c != condition]
        chips.append((condition, change_filter(f, conditions=sisa)))
    if f["price_min"] is not None:
        chips.append(("Min " + format_rupiah(f["price_min"]), change_filter(f, price_min=None)))
    if f["price_max"] is not None:
        chips.append(("Maks " + format_rupiah(f["price_max"]), change_filter(f, price_max=None)))
    if f["city"]:
        chips.append((f["city"], change_filter(f, city="")))
    for tag in f["tags"]:
        sisa = [t for t in f["tags"] if t != tag]
        chips.append((TAG_LABELS[tag], change_filter(f, tags=sisa)))

    return chips
