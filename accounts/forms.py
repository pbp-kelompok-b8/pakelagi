from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User


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


class AccountDeletionForm(forms.Form):
    username = forms.CharField(label="Username saat ini", max_length=150, strip=False,
                               widget=forms.TextInput(attrs={"autocomplete": "username"}))
    password = forms.CharField(label="Password saat ini", strip=False,
                               widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}))


class LoginForm(AuthenticationForm):
    error_messages = {
        "invalid_login": "Username atau kata sandi salah.",
        "inactive": "Username atau kata sandi salah.",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Username"
        self.fields["password"].label = "Kata sandi"
