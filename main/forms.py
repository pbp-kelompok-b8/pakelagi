import re
from urllib.parse import urlsplit

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.db import transaction

from main.models import Profile


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(
        label="Email akun (opsional)",
        required=False,
        help_text="Email ini bersifat privat dan belum diverifikasi, bukan kontak publik.",
        widget=forms.EmailInput(attrs={"autocomplete": "email"}),
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Username"
        self.fields["username"].error_messages["unique"] = (
            "Username ini sudah digunakan. Silakan pilih username lain."
        )
        self.fields["password1"].label = "Kata sandi"
        self.fields["password2"].label = "Konfirmasi kata sandi"
        self.fields["password2"].help_text = "Masukkan kembali kata sandi yang sama."

    error_messages = {
        **UserCreationForm.error_messages,
        "password_mismatch": "Konfirmasi kata sandi tidak sama.",
    }


class ProfileForm(forms.ModelForm):
    email = forms.EmailField(
        label="Email akun (opsional)", required=False,
        help_text="Email ini bersifat privat dan belum diverifikasi, bukan kontak publik.",
    )

    class Meta:
        model = Profile
        fields = ("display_name", "bio", "city", "contact_type", "contact_value")

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields["email"].initial = user.email

    def clean(self):
        cleaned = super().clean()
        for field in ("city", "contact_value"):
            value = cleaned.get(field, "")
            if re.search(r"\b(jalan|jl\.?|gang|gg\.?|nomor|no\.?|rt|rw)\s*\.?\s*\S+", value, re.I):
                self.add_error(field, "Jangan cantumkan alamat rumah; gunakan kota/area umum atau kontak saja.")
        contact = cleaned.get("contact_value", "")
        try:
            parsed = urlsplit(contact)
            if parsed.scheme and parsed.scheme.lower() not in {"http", "https"}:
                self.add_error("contact_value", "URL kontak harus menggunakan http atau https.")
            elif parsed.scheme or contact.startswith("//"):
                forms.URLField().clean(contact)
        except (ValueError, forms.ValidationError):
            self.add_error("contact_value", "Masukkan URL kontak yang valid menggunakan http atau https.")
        return cleaned

    @transaction.atomic
    def save(self):
        self.instance.user = self.user
        profile = super().save()
        self.user.email = self.cleaned_data["email"]
        self.user.save(update_fields=["email"])
        return profile


class LoginForm(AuthenticationForm):
    error_messages = {
        "invalid_login": "Username atau kata sandi salah.",
        "inactive": "Username atau kata sandi salah.",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Username"
        self.fields["password"].label = "Kata sandi"
