from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from accounts.forms import LoginForm, RegistrationForm
from profiles.access import has_complete_profile, onboarding_url, safe_profile_next


@require_http_methods(["GET", "POST"])
def register(request):
    if request.user.is_authenticated:
        return redirect("main:show_main")

    form = RegistrationForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Akun berhasil dibuat. Selamat datang di Pakelagi!")
        return redirect("profiles:profile_create")

    return render(request, "accounts/register.html", {"form": form})


class AccountLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def get_success_url(self):
        if not has_complete_profile(self.request.user):
            target = safe_profile_next(self.request, self.get_redirect_url())
            return onboarding_url(target)
        return super().get_success_url()


class AccountLogoutView(LogoutView):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        messages.success(request, "Kamu berhasil keluar dari akun.")
        return response
