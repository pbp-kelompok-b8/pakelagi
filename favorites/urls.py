from django.urls import path

from favorites import views

app_name = "favorites"

urlpatterns = [
    path("", views.favorite_list, name="list"),
    path("listings/<int:listing_id>/add/", views.favorite_add, name="add"),
    path("listings/<int:listing_id>/remove/", views.favorite_remove, name="remove"),
    path("<int:pk>/edit/", views.favorite_edit, name="edit"),
]
