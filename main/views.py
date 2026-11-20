from urllib.parse import urlencode

from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_GET

from main.categories import category_cards


def show_main(request):
    return render(request, "index.html")


@require_GET
def category_index(request):
    catalog_url = reverse("listings:list")
    categories = [{
        **card,
        "href": catalog_url + "?" + urlencode({"category": card["value"]}),
    } for card in category_cards()]
    return render(request, "categories/index.html", {"categories": categories})
