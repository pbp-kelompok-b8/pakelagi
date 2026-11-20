from django.urls import path

from listings.api import (ListingDetailAPI, ListingListCreateAPI, ListingMineAPI, ListingStatusAPI,
                          LocationSearchAPI)

app_name = "listings_api"

urlpatterns = [
    path("", ListingListCreateAPI.as_view(), name="list"),
    path("mine/", ListingMineAPI.as_view(), name="mine"),
    path("locations/", LocationSearchAPI.as_view(), name="locations"),
    path("<int:pk>/", ListingDetailAPI.as_view(), name="detail"),
    path("<int:pk>/status/", ListingStatusAPI.as_view(), name="status"),
]
