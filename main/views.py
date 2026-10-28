from urllib.parse import urlencode

from django.db.models import Count
from django.shortcuts import render
from django.urls import reverse
from django.utils.text import slugify
from django.views.decorators.http import require_GET

from listings.models import Listing


def show_main(request):
    return render(request, "index.html")


@require_GET
def category_index(request):
    # Sama dengan katalog publik: hanya Available, tidak mengikuti filter kunjungan sebelumnya.
    counts = dict(
        Listing.objects.filter(status=Listing.Status.AVAILABLE).order_by()
        .values("category").annotate(count=Count("id")).values_list("category", "count")
    )
    catalog_url = reverse("listings:list")
    categories = [{
        "value": value,
        "label": label,
        "slug": slugify(value),
        "count": counts.get(value, 0),
        "image": f"images/categories/{slugify(value)}.svg",
        "image_mobile": f"images/categories/{slugify(value)}-mobile.svg",
        "href": catalog_url + "?" + urlencode({"category": value}),
    } for value, label in Listing.Category.choices]
    return render(request, "categories/index.html", {"categories": categories})
