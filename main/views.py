from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from main.forms import LoginForm, ProfileForm, RegistrationForm
from main.models import Profile
from main.access import has_complete_profile, member_required, onboarding_url, safe_profile_next


def show_main(request):
    return render(request, "index.html")


@require_http_methods(["GET", "POST"])
def register(request):
    if request.user.is_authenticated:
        return redirect("main:show_main")

    form = RegistrationForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Akun berhasil dibuat. Selamat datang di Pakelagi!")
        return redirect("main:profile_create")

    return render(request, "accounts/register.html", {"form": form})


@login_required
@require_http_methods(["GET", "POST"])
def profile_create(request):
    profile = Profile.objects.filter(user=request.user).first()
    if profile and profile.display_name.strip():
        return redirect("main:profile")
    return profile_form(request, profile)


def profile_form(request, profile):
    form = ProfileForm(
        request.POST if request.method == "POST" else None,
        instance=profile, user=request.user,
    )
    target = safe_profile_next(request, request.POST.get("next") or request.GET.get("next"))
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Profil berhasil disimpan.")
        return redirect(target or "main:profile")
    return render(request, "profiles/form.html", {"form": form, "next": target})


@member_required
@require_http_methods(["GET"])
def profile_detail(request):
    return render_storefront(request, request.user.profile)


@require_http_methods(["GET"])
def profile_public(request, user_id):
    profile = get_object_or_404(Profile, user_id=user_id)
    if not profile.display_name.strip():
        from django.http import Http404
        raise Http404
    return render_storefront(request, profile)


def render_storefront(request, profile):
    from django.utils.cache import patch_vary_headers
    from main.storefront import listing_context
    from main.profile_contacts import contact_context

    context = {
        "profile": profile,
        **contact_context(request, profile),
        **listing_context(seller_id=profile.user_id, viewer=request.user, query=request.GET),
    }
    partial = request.headers.get("HX-Request") == "true" and request.headers.get("HX-History-Restore-Request") != "true"
    response = render(request, "profiles/listings.html" if partial else "profiles/detail.html", context)
    patch_vary_headers(response, ["HX-Request", "HX-History-Restore-Request", "Cookie"])
    response["Cache-Control"] = "private, no-store"
    return response


@member_required
@require_http_methods(["GET", "POST"])
def profile_edit(request):
    return profile_form(request, request.user.profile)


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
