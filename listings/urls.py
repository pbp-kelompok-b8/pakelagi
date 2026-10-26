from django.urls import path

from listings import views

app_name = "listings"

urlpatterns = [
    path("", views.listing_list, name="list"),
    path("create/", views.listing_create, name="create"),
    path("mine/", views.listing_mine, name="mine"),
    path("location-search/", views.location_search, name="location_search"),
    path("<int:pk>/", views.listing_detail, name="detail"),
    path("<int:pk>/edit/", views.listing_edit, name="edit"),
    path("<int:pk>/delete/", views.listing_delete, name="delete"),
    path("<int:pk>/status/", views.listing_set_status, name="status"),
]
