from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from profiles.forms import ProfileForm
from profiles.models import Profile
from profiles.access import member_required, safe_profile_next


@login_required
@require_http_methods(["GET", "POST"])
def profile_create(request):
    profile = Profile.objects.filter(user=request.user).first()
    if profile and profile.display_name.strip():
        return redirect("profiles:profile")
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
        return redirect(target or "profiles:profile")
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
    from profiles.storefront import listing_context
    from profiles.profile_contacts import contact_context

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
