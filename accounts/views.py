from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.shortcuts import redirect, render, resolve_url
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters, sensitive_variables
from django.views.decorators.http import require_http_methods, require_POST

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.db import DatabaseError

from accounts.services import CONFIRMATION_ERROR, ConfirmationThrottled, delete_confirmed_account

from accounts.forms import AccountDeletionForm, LoginForm, RegistrationForm
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


@sensitive_post_parameters()
@never_cache
@require_http_methods(["GET", "POST"])
def login_user(request):
    next_url = request.POST.get("next", request.GET.get("next", ""))
    if not url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure(),
    ):
        next_url = ""

    def success_url():
        if not has_complete_profile(request.user):
            return onboarding_url(safe_profile_next(request, next_url))
        return next_url or resolve_url(settings.LOGIN_REDIRECT_URL)

    if request.user.is_authenticated:
        target = success_url()
        if target == request.path:
            target = resolve_url(settings.LOGIN_REDIRECT_URL)
        return redirect(target)

    form = LoginForm(request, data=request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        return redirect(success_url())

    return render(request, "accounts/login.html", {"form": form, "next": next_url})


@sensitive_variables()
@sensitive_post_parameters()
@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def delete_account(request):
    if request.user.is_staff or request.user.is_superuser:
        return HttpResponseForbidden("Akun admin harus ditangani melalui prosedur admin terpisah.")
    form = AccountDeletionForm(request.POST if request.method == "POST" else None)
    status = 200
    if request.method == "POST":
        # Malformed/empty submissions must count toward the same per-account limit.
        form.is_valid()
        try:
            if delete_confirmed_account(
                request.user.pk, form.cleaned_data.get("username", ""),
                form.cleaned_data.get("password", ""),
            ):
                logout(request)
                messages.success(request, "Akun berhasil dihapus.")
                return redirect("main:show_main")
            form.add_error(None, CONFIRMATION_ERROR)
        except ConfirmationThrottled:
            status = 429
            form.add_error(None, "Terlalu banyak percobaan. Silakan coba lagi setelah 15 menit.")
        except DatabaseError:
            form.add_error(None, "Penghapusan gagal. Akun tetap tersedia. Silakan coba lagi.")
    return render(request, "accounts/delete.html", {"form": form}, status=status)


@never_cache
@require_POST
def logout_user(request):
    logout(request)
    messages.success(request, "Kamu berhasil keluar dari akun.")
    return redirect(settings.LOGOUT_REDIRECT_URL)
