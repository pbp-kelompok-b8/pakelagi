from django.urls import path
from profiles.views import profile_create, profile_detail, profile_edit, profile_public

app_name = "profiles"

urlpatterns = [
    path("create/", profile_create, name="profile_create"),
    path("", profile_detail, name="profile"),
    path("edit/", profile_edit, name="profile_edit"),
    path("<int:user_id>/", profile_public, name="profile_public"),
]
