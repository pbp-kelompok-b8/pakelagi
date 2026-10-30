from functools import wraps
from urllib.parse import urlencode, urlsplit

from django.http import HttpResponse
from django.urls import reverse
from django.utils.cache import patch_vary_headers

from profiles.access import member_required, safe_profile_next


def favorite_member_required(view):
    protected = member_required(view)

    @wraps(view)
    def wrapped(request, *args, **kwargs):
        response = protected(request, *args, **kwargs)
        if response.status_code == 302 and urlsplit(response.url).path in {
            reverse("accounts:login"), reverse("profiles:profile_create"),
        }:
            if request.method == "POST":
                # Setelah login kembali ke halaman GET, bukan mengulang endpoint POST.
                target = safe_profile_next(request, request.POST.get("next")) or reverse("favorites:list")
                response["Location"] = urlsplit(response.url).path + "?" + urlencode({"next": target})
            if request.headers.get("HX-Request") == "true":
                destination = response.url
                response = HttpResponse()
                response["HX-Redirect"] = destination
        response["Cache-Control"] = "private, no-store"
        patch_vary_headers(response, ["Cookie", "HX-Request", "HX-History-Restore-Request"])
        return response

    return wrapped
