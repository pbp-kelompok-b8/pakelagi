from django import forms
from .models import Guide
from django.core.exceptions import ValidationError
from django.utils.html import strip_tags

class GuideForm(forms.ModelForm):
    class Meta:
        model = Guide
        fields = ['category', 'title', 'ringkasan', 'konten', 'image_url']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={
                'placeholder': 'Masukkan Judul',
                'class': 'form-input'
            }),
            'ringkasan': forms.Textarea(attrs={
                'placeholder': 'Ceritakan sedikit panduanmu',
                'rows': 2,
                'class': 'form-input'
            }),
            'konten': forms.Textarea(attrs={
                'placeholder': 'Tuliskan Panduanmu',
                'rows': 10,
                'class': 'form-input font-mono text-sm' #font-mono untuk bantu visualisasi input format .md
            }),
            'image_url': forms.URLInput(attrs={
                'placeholder': 'https://...',
                'class': 'form-input'
            }),
        }
        
    def clean_title(self):
        title = strip_tags(self.cleaned_data.get("title", "")).strip()
        if not title:
            raise ValidationError("Judul panduan tidak boleh kosong atau hanya berisi tag HTML.")
        return title

    def clean_ringkasan(self):
        ringkasan = strip_tags(self.cleaned_data.get("ringkasan", "")).strip()
        if not ringkasan:
            raise ValidationError("Ringkasan tidak boleh kosong atau hanya berisi tag HTML.")
        return ringkasan

    def clean_konten(self):
        konten = strip_tags(self.cleaned_data.get("konten", "")).strip()
        if not konten:
            raise ValidationError("Isi panduan tidak boleh kosong atau hanya berisi tag HTML.")
        return konten

    def clean_image_url(self):
        image_url = self.cleaned_data.get("image_url", "")
        if image_url:
            image_url = image_url.strip()
            if not image_url.startswith("https://"):
                raise ValidationError("Tautan gambar sampul harus berawalan https://")
        return image_url