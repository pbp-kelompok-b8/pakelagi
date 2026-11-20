from django.urls import path

from favorites.api import FavoriteViewSet

app_name = "favorites_api"

urlpatterns = [
    path("", FavoriteViewSet.as_view({"get": "list", "post": "create"}), name="list"),
    path("<int:pk>/", FavoriteViewSet.as_view({
        "get": "retrieve", "patch": "partial_update", "delete": "destroy",
    }), name="detail"),
]
