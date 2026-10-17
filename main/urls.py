from django.urls import path
from main.views import AccountLoginView, AccountLogoutView, profile_create, profile_detail, profile_edit, profile_public, register, show_main

app_name = "main"

urlpatterns = [
    path("", show_main, name="show_main"),
    path("profile/create/", profile_create, name="profile_create"),
    path("profile/", profile_detail, name="profile"),
    path("profile/edit/", profile_edit, name="profile_edit"),
    path("profile/<int:user_id>/", profile_public, name="profile_public"),
    path("accounts/register/", register, name="register"),
    path("accounts/login/", AccountLoginView.as_view(), name="login"),
    path("accounts/logout/", AccountLogoutView.as_view(), name="logout"),
]
