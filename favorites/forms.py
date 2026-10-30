from django import forms

from favorites.models import Favorite


class FavoriteNoteForm(forms.ModelForm):
    class Meta:
        model = Favorite
        fields = ["note"]
        labels = {"note": "Catatan pribadi"}
        widgets = {
            "note": forms.Textarea(attrs={"rows": 3, "maxlength": 1000, "class": "favorite-note-input"}),
        }
