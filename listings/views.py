from django.shortcuts import render
from django.views.decorators.http import require_GET

from listings.models import Listing


@require_GET
def listing_list(request):
    # Katalog publik: hanya Available. Sold dan Hidden tidak pernah tampil di sini.
    listings = Listing.objects.filter(status=Listing.Status.AVAILABLE)
    return render(request, "listings/list.html", {
        "listings": listings,
        "total_count": listings.count(),
    })
