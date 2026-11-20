from django.urls import path

from profiles.api import CreateProfileView, OwnProfileView, PublicProfileView

app_name = "profiles_api"
urlpatterns = [
    path("", CreateProfileView.as_view(), name="create"),
    path("me/", OwnProfileView.as_view(), name="me"),
    path("<int:user_id>/", PublicProfileView.as_view(), name="public"),
]
