"""Storefront seam; replace the empty adapter when the listing module exists."""
from dataclasses import dataclass
from urllib.parse import urlencode


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


class EmptyListingAdapter:
    """Deliberately no invented listings, favorites, routes or model dependencies."""

    def for_profile(self, *, seller_id, viewer, selection):
        return {"available_count": 0, "sold_count": 0, "listings": (), "sold_preview": ()}


def listing_context(*, seller_id, viewer, query):
    selection = StorefrontSelection.from_query(query)
    result = EmptyListingAdapter().for_profile(seller_id=seller_id, viewer=viewer, selection=selection)
    return {
        **result,
        "selection": selection,
        "sold_tab_query": urlencode({"tab": "terjual", "sort": selection.sort}),
        "available_tab_query": urlencode({"tab": "dijual", "sort": selection.sort}),
    }
