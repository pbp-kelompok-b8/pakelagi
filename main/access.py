from functools import wraps
from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

from main.models import Profile


def has_complete_profile(user):
    if not user.is_authenticated:
        return False
    profile = Profile.objects.filter(user=user).first()
    return bool(profile and profile.display_name.strip())


def onboarding_url(target=""):
    url = reverse("main:profile_create")
    return url + "?" + urlencode({"next": target}, safe="/") if target else url


def safe_profile_next(request, target):
    if not target or not url_has_allowed_host_and_scheme(
        target, allowed_hosts={request.get_host()}, require_https=request.is_secure(),
    ):
        return ""
    # Auth/onboarding destinations cannot be useful return targets and may loop.
    from urllib.parse import urlsplit
    path = urlsplit(target).path
    if path in {reverse("main:profile_create"), reverse("main:login"),
                reverse("main:register"), reverse("main:logout")}:
        return ""
    return target


def member_required(view):
    @login_required
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not has_complete_profile(request.user):
            return redirect(onboarding_url(request.get_full_path()))
        return view(request, *args, **kwargs)
    return wrapped
