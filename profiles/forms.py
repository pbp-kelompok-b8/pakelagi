import re
from urllib.parse import urlsplit

from django import forms
from django.db import transaction

from profiles.models import Profile
from profiles.validators import normalize_instagram_contact


from accounts.services import update_account_email


class ProfileForm(forms.ModelForm):
    remove_avatar = forms.BooleanField(label="Hapus foto profil", required=False)
    remove_cover = forms.BooleanField(label="Hapus foto sampul", required=False)
    avatar_url = forms.CharField(label="URL foto profil", required=False, max_length=2048, widget=forms.URLInput)
    cover_url = forms.CharField(label="URL foto sampul", required=False, max_length=2048, widget=forms.URLInput)
    email = forms.EmailField(
        label="Email akun (opsional)", required=False,
        help_text="Email ini bersifat privat dan belum diverifikasi, bukan kontak publik.",
    )

    class Meta:
        model = Profile
        fields = ("display_name", "bio", "city", "avatar_url", "cover_url", "phone_number", "contact_type", "contact_value")

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields["email"].initial = user.email

    def clean_phone_number(self):
        value = self.cleaned_data["phone_number"]
        if value.startswith("08"):
            value = "+62" + value[1:]
        if value and not re.fullmatch(r"\+[1-9][0-9]{1,14}", value):
            raise forms.ValidationError("Gunakan nomor 08 atau format internasional + dengan maksimal 15 digit.")
        return value

    def clean(self):
        cleaned = super().clean()
        for field in ("city", "contact_value"):
            value = cleaned.get(field, "")
            if re.search(r"\b(jalan|jl\.?|gang|gg\.?|nomor|no\.?|rt|rw)\s*\.?\s*\S+", value, re.I):
                self.add_error(field, "Jangan cantumkan alamat rumah; gunakan kota/area umum atau kontak saja.")
        contact = cleaned.get("contact_value", "")
        contact_type = cleaned.get("contact_type", "")
        if contact_type and not contact and "contact_value" not in self.errors:
            self.add_error("contact_value", "Isi kontak sesuai metode yang dipilih.")
        if contact and not contact_type and "contact_type" not in self.errors:
            self.add_error("contact_type", "Pilih metode kontak.")
        if contact_type == "instagram" and contact:
            try:
                cleaned["contact_value"] = normalize_instagram_contact(contact)
            except forms.ValidationError as error:
                self.add_error("contact_value", error)
        if contact_type == "email" and contact:
            try:
                forms.EmailField().clean(contact)
            except forms.ValidationError:
                self.add_error("contact_value", "Masukkan alamat email kontak yang valid.")
        try:
            parsed = urlsplit(contact)
            if parsed.scheme and parsed.scheme.lower() not in {"http", "https"}:
                self.add_error("contact_value", "URL kontak harus menggunakan http atau https.")
            elif parsed.scheme or contact.startswith("//"):
                forms.URLField().clean(contact)
                if parsed.username is not None or parsed.password is not None:
                    self.add_error("contact_value", "URL kontak tidak boleh memuat kredensial.")
        except (ValueError, forms.ValidationError):
            self.add_error("contact_value", "Masukkan URL kontak yang valid menggunakan http atau https.")
        return cleaned

    @transaction.atomic
    def save(self):
        self.instance.user = self.user
        for action, field in (("remove_avatar", "avatar_url"), ("remove_cover", "cover_url")):
            if self.cleaned_data.get(action):
                setattr(self.instance, field, "")
        profile = super().save()
        update_account_email(self.user, self.cleaned_data["email"])
        return profile
