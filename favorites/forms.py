from django import forms

from favorites.models import Favorite


class FavoriteNoteForm(forms.ModelForm):
    class Meta:
        model = Favorite
        fields = ["note"]
        widgets = {
            "note": forms.Textarea(attrs={"rows": 4, "maxlength": 1000, "class": "w-full border border-line p-3"}),
        }
