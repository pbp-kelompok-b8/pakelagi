from django.urls import path
from accounts.views import AccountLoginView, AccountLogoutView, register

app_name = "accounts"

urlpatterns = [
    path("register/", register, name="register"),
    path("login/", AccountLoginView.as_view(), name="login"),
    path("logout/", AccountLogoutView.as_view(), name="logout"),
]
