from django import forms
from .models import Guide

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