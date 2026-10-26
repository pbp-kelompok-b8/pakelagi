from django.urls import path

from listings.views import listing_list

app_name = "listings"

urlpatterns = [
    path("", listing_list, name="list"),
]
