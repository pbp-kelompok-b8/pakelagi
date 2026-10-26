"""Pencarian, filter, dan pengurutan katalog.

Semua input datang dari URL (?q=...&size=M&...) jadi tidak dipercaya: nilai yang tidak dikenal
dibuang diam-diam, angka dibatasi, dan hasilnya selalu berupa query yang aman (tidak pernah error 500).
"""
from dataclasses import dataclass, replace
from urllib.parse import urlencode

from django.db.models import Q

from listings.models import MAX_PRICE, Listing

SORTS = {
    "terbaru": ("-created_at", "-id"),
    "harga_terendah": ("price", "id"),
    "harga_tertinggi": ("-price", "id"),
}
SORT_LABELS = {"terbaru": "Terbaru", "harga_terendah": "Harga terendah", "harga_tertinggi": "Harga tertinggi"}
DEFAULT_SORT = "terbaru"

# kunci di URL -> field boolean di model
TAG_FIELDS = {
    "repairable": "is_repairable",
    "upcycled": "is_upcycled",
    "local": "is_locally_available",
    "extends": "extends_clothing_life",
}
TAG_LABELS = {key: Listing._meta.get_field(field).verbose_name for key, field in TAG_FIELDS.items()}

MAX_QUERY_LENGTH = 100
MAX_SEARCH_WORDS = 5


def _pick(values, allowed):
    """Ambil nilai yang valid saja, urutannya mengikuti daftar resmi agar URL selalu konsisten."""
    chosen = set(values)
    return tuple(value for value in allowed if value in chosen)


def _price(value):
    try:
        number = int(str(value).strip())
    except (TypeError, ValueError):
        return None
    return min(max(number, 0), MAX_PRICE)


@dataclass(frozen=True)
class CatalogQuery:
    q: str = ""
    category: str = ""
    sizes: tuple = ()
    conditions: tuple = ()
    price_min: int | None = None
    price_max: int | None = None
    city: str = ""
    tags: tuple = ()
    sort: str = DEFAULT_SORT

    @classmethod
    def from_query(cls, params):
        """params: request.GET (QueryDict)."""
        category = params.get("category", "")
        sort = params.get("sort", DEFAULT_SORT)
        price_min, price_max = _price(params.get("price_min")), _price(params.get("price_max"))
        if price_min is not None and price_max is not None and price_min > price_max:
            price_min, price_max = price_max, price_min
        return cls(
            q=" ".join(params.get("q", "").split())[:MAX_QUERY_LENGTH],
            category=category if category in Listing.Category.values else "",
            sizes=_pick(params.getlist("size"), Listing.Size.values),
            conditions=_pick(params.getlist("condition"), Listing.Condition.values),
            price_min=price_min,
            price_max=price_max,
            city=" ".join(params.get("city", "").split())[:100],
            tags=_pick(params.getlist("tag"), TAG_FIELDS),
            sort=sort if sort in SORTS else DEFAULT_SORT,
        )

    @property
    def is_filtered(self):
        """Apakah ada pencarian atau filter yang aktif (urutan tidak dihitung)."""
        return bool(
            self.q or self.category or self.sizes or self.conditions or self.city or self.tags
            or self.price_min is not None or self.price_max is not None
        )

    def apply(self, queryset):
        # Setiap kata harus cocok di judul ATAU brand.
        for word in self.q.split()[:MAX_SEARCH_WORDS]:
            queryset = queryset.filter(Q(title__icontains=word) | Q(brand__icontains=word))
        if self.category:
            queryset = queryset.filter(category=self.category)
        if self.sizes:
            queryset = queryset.filter(size__in=self.sizes)
        if self.conditions:
            queryset = queryset.filter(condition__in=self.conditions)
        if self.price_min is not None:
            queryset = queryset.filter(price__gte=self.price_min)
        if self.price_max is not None:
            queryset = queryset.filter(price__lte=self.price_max)
        if self.city:
            queryset = queryset.filter(city__iexact=self.city)
        for tag in self.tags:
            queryset = queryset.filter(**{TAG_FIELDS[tag]: True})
        return queryset.order_by(*SORTS[self.sort])

    # --- membangun URL ---------------------------------------------------------------

    def pairs(self, page=None):
        pairs = []
        if self.q:
            pairs.append(("q", self.q))
        if self.category:
            pairs.append(("category", self.category))
        pairs += [("size", value) for value in self.sizes]
        pairs += [("condition", value) for value in self.conditions]
        if self.price_min is not None:
            pairs.append(("price_min", self.price_min))
        if self.price_max is not None:
            pairs.append(("price_max", self.price_max))
        if self.city:
            pairs.append(("city", self.city))
        pairs += [("tag", value) for value in self.tags]
        if self.sort != DEFAULT_SORT:
            pairs.append(("sort", self.sort))
        if page and page > 1:
            pairs.append(("page", page))
        return pairs

    def querystring(self, page=None):
        return urlencode(self.pairs(page))

    def with_(self, **changes):
        return replace(self, **changes)

    def chips(self):
        """Filter aktif sebagai (label, query tanpa filter itu), untuk chip yang bisa dihapus satu per satu."""
        chips = []
        if self.q:
            chips.append((f"“{self.q}”", self.with_(q="")))
        chips += [(value, self.with_(sizes=tuple(v for v in self.sizes if v != value))) for value in self.sizes]
        chips += [(value, self.with_(conditions=tuple(v for v in self.conditions if v != value))) for value in self.conditions]
        if self.price_min is not None:
            chips.append((f"Min Rp {self.price_min:,}".replace(",", "."), self.with_(price_min=None)))
        if self.price_max is not None:
            chips.append((f"Maks Rp {self.price_max:,}".replace(",", "."), self.with_(price_max=None)))
        if self.city:
            chips.append((self.city, self.with_(city="")))
        chips += [(TAG_LABELS[tag], self.with_(tags=tuple(v for v in self.tags if v != tag))) for tag in self.tags]
        return chips
