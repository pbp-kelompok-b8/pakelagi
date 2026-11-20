from django.db.models import Count
from django.utils.text import slugify

from listings.models import Listing


def category_cards():
    counts = dict(
        Listing.objects.filter(status=Listing.Status.AVAILABLE).order_by()
        .values("category").annotate(count=Count("id")).values_list("category", "count")
    )
    cards = []
    for value, label in Listing.Category.choices:
        slug = slugify(value)
        cards.append({
            "value": value,
            "label": label,
            "slug": slug,
            "count": counts.get(value, 0),
            "image": f"images/categories/{slug}.svg",
            "image_mobile": f"images/categories/{slug}-mobile.svg",
        })
    return cards
