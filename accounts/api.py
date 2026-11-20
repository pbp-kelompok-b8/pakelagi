"""Session-based JSON endpoints; HTML account views remain independent."""

from django.contrib.auth import login, logout
from django.db import DatabaseError
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import APIException, ParseError, PermissionDenied
from rest_framework.parsers import JSONParser
from rest_framework.permissions import AllowAny
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.forms import AccountDeletionForm, LoginForm, RegistrationForm
from accounts.services import CONFIRMATION_ERROR, ConfirmationThrottled, delete_confirmed_account
from profiles.access import has_complete_profile


def error(code, message, status, fields=None):
    detail = {"code": code, "message": message}
    if fields:
        detail["fields"] = fields
    return Response({"error": detail}, status=status)


def account_session(user):
    complete = has_complete_profile(user)
    return {
        "account": {"id": user.pk, "username": user.username, "email": user.email},
        "profile_complete": complete,
        "next": "/api/v1/profiles/me/" if complete else "/api/v1/profiles/",
    }


class AccountSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        # Check the raw Django request, without parsing a malformed JSON body.
        super().enforce_csrf(request._request)


class AccountsAPIView(APIView):
    authentication_classes = [AccountSessionAuthentication]
    permission_classes = [AllowAny]
    parser_classes = [JSONParser]
    renderer_classes = [JSONRenderer]
    http_method_names = ["post", "options"]

    def initial(self, request, *args, **kwargs):
        # SessionAuthentication alone skips CSRF for anonymous requests.
        AccountSessionAuthentication().enforce_csrf(request)
        super().initial(request, *args, **kwargs)

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response["Cache-Control"] = "private, no-store"
        return response

    def handle_exception(self, exc):
        if isinstance(exc, DatabaseError):
            return error("server_error", "Operasi gagal. Silakan coba lagi.", 500)
        if isinstance(exc, APIException):
            code = "csrf_failed" if isinstance(exc, PermissionDenied) else exc.default_code
            messages = {
                "csrf_failed": "Verifikasi CSRF gagal.",
                "parse_error": "JSON tidak valid.",
                "method_not_allowed": "Method tidak didukung.",
                "unsupported_media_type": "Gunakan Content-Type application/json.",
            }
            return error(code, messages.get(code, "Request tidak dapat diproses."), exc.status_code)
        return super().handle_exception(exc)


class RegisterView(AccountsAPIView):
    def post(self, request):
        if request.user.is_authenticated:
            return error("already_authenticated", "Akun sudah login.", 403)
        data = request.data
        if not isinstance(data, dict):
            return error("validation_error", "Periksa kembali data yang dikirim.", 400)
        invalid = {name: ["Field harus berupa string."] for name in (
            "username", "email", "password", "password_confirmation"
        ) if name in data and not isinstance(data[name], str)}
        if invalid:
            return error("validation_error", "Periksa kembali data yang dikirim.", 400, invalid)
        form = RegistrationForm({
            "username": data.get("username", ""), "email": data.get("email", ""),
            "password1": data.get("password", ""),
            "password2": data.get("password_confirmation", ""),
        })
        if not form.is_valid():
            names = {"password1": "password", "password2": "password_confirmation"}
            fields = {names.get(key, key): list(value) for key, value in form.errors.items()}
            return error("validation_error", "Periksa kembali data yang dikirim.", 400, fields)
        user = form.save()
        login(request, user)
        return Response(account_session(user), status=201)


class LoginView(AccountsAPIView):
    def post(self, request):
        if request.user.is_authenticated:
            return Response(account_session(request.user))
        data = request.data
        if not isinstance(data, dict) or any(
            not isinstance(data.get(field), str) for field in ("username", "password")
        ):
            return error("invalid_credentials", "Username atau kata sandi salah.", 401)
        form = LoginForm(request, data=data)
        if not form.is_valid():
            return error("invalid_credentials", "Username atau kata sandi salah.", 401)
        user = form.get_user()
        login(request, user)
        return Response(account_session(user))


class LogoutView(AccountsAPIView):
    def post(self, request):
        logout(request)
        return Response(status=204)


class DeleteView(AccountsAPIView):
    def post(self, request):
        if not request.user.is_authenticated:
            return error("not_authenticated", "Silakan login terlebih dahulu.", 401)
        if request.user.is_staff or request.user.is_superuser:
            return error("self_deletion_forbidden", "Akun admin tidak dapat dihapus mandiri.", 403)
        try:
            data = request.data
        except ParseError:
            data = {}
        if not isinstance(data, dict) or any(
            not isinstance(data.get(field), str) for field in ("username", "password")
        ):
            data = {}
        form = AccountDeletionForm(data)
        form.is_valid()
        try:
            deleted = delete_confirmed_account(
                request.user.pk, form.cleaned_data.get("username", ""),
                form.cleaned_data.get("password", ""),
            )
        except ConfirmationThrottled:
            return error("confirmation_throttled", "Terlalu banyak percobaan. Coba setelah 15 menit.", 429)
        except DatabaseError:
            return error("server_error", "Penghapusan gagal. Akun tetap tersedia. Silakan coba lagi.", 500)
        if not deleted:
            return error("confirmation_failed", CONFIRMATION_ERROR, 400)
        logout(request)
        return Response(status=204)
