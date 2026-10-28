"""Storefront: membaca pilihan tab/urutan/halaman dari URL lalu meminta barangnya dari modul listing."""
from dataclasses import dataclass
from urllib.parse import urlencode

from listings.storefront import for_profile


@dataclass(frozen=True)
class StorefrontSelection:
    tab: str = "dijual"
    sort: str = "terbaru"
    page: int = 1

    @classmethod
    def from_query(cls, query):
        tab = query.get("tab", "dijual")
        sort = query.get("sort", "terbaru")
        try:
            page = max(1, int(query.get("page", 1)))
        except (ValueError, TypeError):
            page = 1
        return cls(
            tab if tab in {"dijual", "terjual"} else "dijual",
            sort if sort in {"terbaru", "harga_terendah", "harga_tertinggi"} else "terbaru",
            page,
        )


def listing_context(*, seller_id, viewer, query):
    selection = StorefrontSelection.from_query(query)
    result = for_profile(seller_id=seller_id, viewer=viewer, selection=selection)
    return {
        **result,
        "selection": selection,
        "sold_tab_query": urlencode({"tab": "terjual", "sort": selection.sort}),
        "available_tab_query": urlencode({"tab": "dijual", "sort": selection.sort}),
        # Tautan "Muat lebih banyak": tab dan urutan tetap, halamannya naik satu
        "more_query": urlencode({"tab": selection.tab, "sort": selection.sort, "page": result["next_page"]}),
    }
