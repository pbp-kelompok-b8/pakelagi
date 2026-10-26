"""
Pencarian kota/area lewat Nominatim (OpenStreetMap) untuk form listing.

Aturan dari Nominatim Usage Policy yang kita ikuti:
- request dikirim dari server (bukan browser) dengan User-Agent yang jelas menyebut Pakelagi
- hasil di-cache, jadi pencarian yang sama tidak dikirim berulang
- maksimal 1 request per detik
- kalau Nominatim menolak (403/429), kita berhenti bertanya beberapa menit
- atribusi OpenStreetMap ditampilkan di halaman (ada di template)

Kalau ada yang gagal, hasilnya cuma status "unavailable" atau "throttled", bukan error.
Penjual tetap bisa mengetik nama kotanya sendiri.
"""
import hashlib
import logging
from decimal import Decimal, InvalidOperation

import requests
from django.conf import settings
from django.core.cache import cache

log = logging.getLogger(__name__)

DEFAULT_URL = "https://nominatim.openstreetmap.org/search"
DEFAULT_USER_AGENT = "Pakelagi/1.0 (+https://github.com/pbp-kelompok-b8/pakelagi; PBP Fasilkom UI student project)"

MIN_QUERY_LENGTH = 3
MAX_QUERY_LENGTH = 100
FETCH_LIMIT = 8             # jumlah yang diminta ke Nominatim (sebagian akan dibuang)
MAX_RESULTS = 5             # jumlah yang ditampilkan ke penjual
REQUEST_TIMEOUT = (2, 4)    # (detik untuk menyambung, detik untuk membaca) supaya form tidak menunggu lama

RESULT_TTL = 24 * 60 * 60   # hasil yang ada isinya disimpan 24 jam
EMPTY_TTL = 60 * 60         # hasil kosong disimpan 1 jam
THROTTLE_SECONDS = 1
COOLDOWN_SECONDS = 5 * 60
THROTTLE_KEY = "nominatim:throttle"
COOLDOWN_KEY = "nominatim:cooldown"

# Status hasil pencarian
OK = "ok"
SHORT = "short"
THROTTLED = "throttled"
UNAVAILABLE = "unavailable"

# Hanya tempat setingkat kota/area yang kita terima. Jalan, bangunan, toko, dan rumah dibuang
# karena spesifikasi melarang alamat rumah atau titik pickup yang presisi.
ALLOWED_CATEGORIES = ["place", "boundary"]
ALLOWED_TYPES = [
    "city", "town", "village", "hamlet", "suburb", "neighbourhood", "quarter", "borough", "city_district",
    "municipality", "county", "state_district", "district", "administrative", "island",
]
REGION_KEYS = ["city", "town", "municipality", "county", "regency", "state_district"]

# Kotak kasar Indonesia, cuma untuk membuang koordinat yang ngawur (misal di Eropa atau Amerika).
# Ini BUKAN batas negara: Singapura dan Malaysia bagian utara ikut berada di dalam kotak.
# Pencarian kita sudah dibatasi countrycodes=id, jadi koordinat yang disimpan berasal dari Indonesia.
LAT_MIN, LAT_MAX = Decimal("-11.5"), Decimal("6.5")
LON_MIN, LON_MAX = Decimal("94.0"), Decimal("141.5")
COORD_PRECISION = Decimal("0.01")   # sekitar 1 km: cukup untuk "area umum", tidak cukup untuk menunjuk rumah


def round_coordinate(value):
    # Contoh: Decimal("-6.8848474") jadi Decimal("-6.88")
    return value.quantize(COORD_PRECISION)


def parse_coordinate(raw):
    # Ubah teks jadi Decimal. Kalau bukan angka biasa (termasuk NaN dan Infinity), hasilnya None.
    try:
        value = Decimal(str(raw).strip())
    except InvalidOperation:
        return None
    if not value.is_finite():
        return None
    return value


def is_in_indonesia(lat, lon):
    return LAT_MIN <= lat <= LAT_MAX and LON_MIN <= lon <= LON_MAX


def build_label(item):
    # Judul dan keterangan satu hasil, contoh: ("Coblong, Kota Bandung", "Jawa Barat, Indonesia")
    address = item.get("address")
    if not isinstance(address, dict):
        address = {}

    name = str(item.get("name") or "").strip()
    if not name:
        name = str(item.get("display_name") or "").split(",")[0].strip()

    # Wilayah induknya (kota/kabupaten) dicari dari beberapa kemungkinan kunci
    region = ""
    for key in REGION_KEYS:
        if address.get(key):
            region = str(address[key]).strip()
            break

    # Kalau nama sudah bagian dari wilayah (atau sebaliknya), misal "Bandung" dan "Kota Bandung",
    # cukup pakai yang lebih lengkap supaya tidak tertulis dua kali
    sama = name.casefold() in region.casefold() or region.casefold() in name.casefold()
    if region and name and not sama:
        title = name + ", " + region
    elif len(region) > len(name):
        title = region
    else:
        title = name

    state = str(address.get("state") or "").strip()
    if state:
        subtitle = state + ", Indonesia"
    else:
        subtitle = "Indonesia"

    return title[:100].rstrip(" ,"), subtitle


def parse_results(payload):
    results = []
    sudah_ada = []   # judul yang sudah dimasukkan, supaya tidak ada yang dobel

    for item in payload:
        if not isinstance(item, dict):
            continue
        if item.get("category") not in ALLOWED_CATEGORIES or item.get("type") not in ALLOWED_TYPES:
            continue

        lat = parse_coordinate(item.get("lat"))
        lon = parse_coordinate(item.get("lon"))
        if lat is None or lon is None or not is_in_indonesia(lat, lon):
            continue

        title, subtitle = build_label(item)
        if not title or title.casefold() in sudah_ada:
            continue
        sudah_ada.append(title.casefold())

        results.append({
            "title": title,
            "subtitle": subtitle,
            "city": title,                       # teks yang nanti masuk ke kolom kota
            "lat": str(round_coordinate(lat)),
            "lon": str(round_coordinate(lon)),
        })
        if len(results) == MAX_RESULTS:
            break

    return results


def search(query):
    # Mengembalikan (results, status). results berupa list dict, status salah satu dari OK/SHORT/THROTTLED/UNAVAILABLE.
    text = " ".join(str(query or "").split())[:MAX_QUERY_LENGTH]

    # Spasi tidak dihitung, jadi "a b" belum layak dicari dan tidak membuang jatah 1 request per detik
    if len(text.replace(" ", "")) < MIN_QUERY_LENGTH:
        return [], SHORT

    # Kunci cache tidak membedakan huruf besar-kecil. Di-hash supaya panjang dan karakternya aman.
    key = "nominatim:q:" + hashlib.sha1(text.casefold().encode("utf-8")).hexdigest()
    cached = cache.get(key)
    if cached is not None:
        return cached, OK

    if cache.get(COOLDOWN_KEY):
        return [], UNAVAILABLE

    # cache.add cuma berhasil kalau kuncinya belum ada. Karena kuncinya hangus dalam 1 detik,
    # ini jadi pembatas "maksimal 1 request per detik".
    if not cache.add(THROTTLE_KEY, 1, THROTTLE_SECONDS):
        return [], THROTTLED

    url = getattr(settings, "NOMINATIM_URL", DEFAULT_URL)
    user_agent = getattr(settings, "NOMINATIM_USER_AGENT", DEFAULT_USER_AGENT)
    params = {
        "q": text,
        "format": "jsonv2",
        "countrycodes": "id",
        "limit": FETCH_LIMIT,
        "addressdetails": 1,
        "accept-language": "id",
    }

    try:
        response = requests.get(url, params=params, headers={"User-Agent": user_agent}, timeout=REQUEST_TIMEOUT)
    except requests.RequestException as error:
        log.warning("Nominatim tidak dapat dihubungi: %s", type(error).__name__)
        return [], UNAVAILABLE

    # 403/429 artinya kita ditolak: berhenti bertanya dulu supaya tidak memperburuk keadaan
    if response.status_code in [403, 429]:
        log.warning("Nominatim menolak permintaan (HTTP %s), berhenti meminta selama %s detik.",
                    response.status_code, COOLDOWN_SECONDS)
        cache.set(COOLDOWN_KEY, True, COOLDOWN_SECONDS)
        return [], UNAVAILABLE
    if response.status_code != 200:
        log.warning("Nominatim membalas HTTP %s", response.status_code)
        return [], UNAVAILABLE

    try:
        payload = response.json()
    except ValueError:
        return [], UNAVAILABLE
    if not isinstance(payload, list):
        return [], UNAVAILABLE

    results = parse_results(payload)
    if results:
        cache.set(key, results, RESULT_TTL)
    else:
        cache.set(key, results, EMPTY_TTL)
    return results, OK
