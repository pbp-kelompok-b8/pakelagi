"""JSON profile endpoints, independent of the HTML storefront."""

from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework.response import Response

from accounts.api import AccountsAPIView, error
from profiles.forms import ProfileForm
from profiles.models import Profile
from profiles.access import has_complete_profile
from profiles.profile_contacts import contact_context


PROFILE_FIELDS = tuple(ProfileForm.Meta.fields)


def owner_data(profile, user):
    return {
        "profile": {
            "user_id": user.pk,
            **{field: getattr(profile, field) for field in PROFILE_FIELDS},
            "created_at": profile.created_at.isoformat().replace("+00:00", "Z"),
            "updated_at": profile.updated_at.isoformat().replace("+00:00", "Z"),
        },
        "account": {"username": user.username, "email": user.email},
    }


def validate_input(data, *, partial=False):
    if not isinstance(data, dict):
        return error("validation_error", "Request harus berupa objek JSON.", 400)
    fields = {field: ["Field harus berupa string."]
              for field in (*PROFILE_FIELDS, "email")
              if field in data and not isinstance(data[field], str)}
    if partial:
        for field in ("remove_avatar", "remove_cover"):
            if field in data and not isinstance(data[field], bool):
                fields[field] = ["Field harus berupa boolean."]
    if fields:
        return error("validation_error", "Periksa kembali data yang dikirim.", 400, fields)


class PublicProfileView(AccountsAPIView):
    http_method_names = ["get", "options"]

    def get(self, request, user_id):
        profile = Profile.objects.filter(user_id=user_id).first()
        if not profile or not profile.display_name.strip():
            return error("not_found", "Profil tidak ditemukan.", 404)
        contact = None
        if has_complete_profile(request.user) and (profile.contact_value or profile.phone_number):
            seller = contact_context(request, profile)["seller_contact"]
            contact = {
                "type": profile.contact_type or None,
                "value": profile.contact_value or None,
                "url": seller["url"] or None,
                "phone_number": profile.phone_number or None,
            }
        return Response({
            "profile": {"user_id": profile.user_id, **{
                field: getattr(profile, field) for field in
                ("display_name", "bio", "city", "avatar_url", "cover_url")
            }},
            "contact": contact,
        })


class OwnProfileView(AccountsAPIView):
    http_method_names = ["get", "patch", "options"]

    def get(self, request):
        if not request.user.is_authenticated:
            return error("not_authenticated", "Silakan login terlebih dahulu.", 401)
        profile = Profile.objects.filter(user=request.user).first()
        if not profile or not profile.display_name.strip():
            response = error("profile_incomplete", "Lengkapi profil terlebih dahulu.", 403)
            response.data["next"] = "/api/v1/profiles/"
            return response
        return Response(owner_data(profile, request.user))

    @transaction.atomic
    def patch(self, request):
        if request.user.is_authenticated:
            # Serialize read/merge/save on the account, including its private email.
            request.user = get_user_model().objects.select_for_update().get(pk=request.user.pk)
        access = self.get(request)
        if access.status_code != 200:
            return access
        profile = Profile.objects.get(user=request.user)
        payload = request.data
        invalid = validate_input(payload, partial=True)
        if invalid is not None:
            return invalid
        data = {field: getattr(profile, field) for field in PROFILE_FIELDS}
        data["email"] = request.user.email
        data.update({field: value for field, value in payload.items()
                     if field in (*PROFILE_FIELDS, "email", "remove_avatar", "remove_cover")})
        for action, field in (("remove_avatar", "avatar_url"), ("remove_cover", "cover_url")):
            if data.get(action) is True:
                data[field] = ""
        form = ProfileForm(data, instance=profile, user=request.user)
        if not form.is_valid():
            return error("validation_error", "Periksa kembali data yang dikirim.", 400,
                         {field: list(messages) for field, messages in form.errors.items()})
        return Response(owner_data(form.save(), request.user))


class CreateProfileView(AccountsAPIView):
    @transaction.atomic
    def post(self, request):
        if not request.user.is_authenticated:
            return error("not_authenticated", "Silakan login terlebih dahulu.", 401)
        # Lock the account even when its one-to-one profile does not exist yet.
        request.user = get_user_model().objects.select_for_update().get(pk=request.user.pk)
        existing = Profile.objects.filter(user=request.user).first()
        if existing and existing.display_name.strip():
            return error("profile_already_complete", "Profil sudah lengkap.", 409)
        payload = request.data
        invalid = validate_input(payload)
        if invalid is not None:
            return invalid
        data = {field: payload[field] for field in (*PROFILE_FIELDS, "email") if field in payload}
        form = ProfileForm(data, instance=existing, user=request.user)
        if not form.is_valid():
            return error("validation_error", "Periksa kembali data yang dikirim.", 400,
                         {field: list(messages) for field, messages in form.errors.items()})
        profile = form.save()
        return Response(owner_data(profile, request.user), status=200 if existing else 201)
