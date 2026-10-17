from django.urls import path
from main.views import AccountLoginView, AccountLogoutView, register, show_main

app_name = "main"

urlpatterns = [
    path("", show_main, name="show_main"),
    path("accounts/register/", register, name="register"),
    path("accounts/login/", AccountLoginView.as_view(), name="login"),
    path("accounts/logout/", AccountLogoutView.as_view(), name="logout"),
]
