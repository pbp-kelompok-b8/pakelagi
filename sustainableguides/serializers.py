from rest_framework import serializers
from django.utils.html import strip_tags
from .models import Guide
from .rendering import render_guide_markdown

class GuideSerializer(serializers.ModelSerializer):
    author_name = serializers.ReadOnlyField()
    moderator_name = serializers.ReadOnlyField()
    reading_time = serializers.ReadOnlyField()
    is_scheduled = serializers.ReadOnlyField()
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    content_html = serializers.SerializerMethodField()
    table_of_contents = serializers.SerializerMethodField()
    rejected_notes = serializers.SerializerMethodField()

    class Meta:
        model = Guide
        fields = [
            'id',
            'author',
            'author_name',
            'approved_by',
            'moderator_name',
            'category',
            'category_display',
            'title',
            'ringkasan',
            'konten',
            'content_html',
            'table_of_contents',
            'image_url',
            'reading_time',
            'status',
            'status_display',
            'is_published',
            'is_scheduled',
            'rejected_notes',
            'date_submitted',
            'date_published',
        ]
        read_only_fields = [
            'id',
            'author',
            'approved_by',
            'status',
            'is_published',
            'date_submitted',
            'date_published',
        ]

    def _get_rendered_markdown(self, obj):
        if not hasattr(obj, '_rendered_md'):
            obj._rendered_md = render_guide_markdown(obj.konten)
        return obj._rendered_md

    def get_content_html(self, obj):
        html, _ = self._get_rendered_markdown(obj)
        return html

    def get_table_of_contents(self, obj):
        _, toc = self._get_rendered_markdown(obj)
        return toc

    def get_rejected_notes(self, obj):
        return obj.rejected_notes if obj.status == 'DITOLAK' else None

    def validate_title(self, value):
        cleaned = strip_tags(value).strip()
        if not cleaned:
            raise serializers.ValidationError("Judul panduan tidak boleh kosong atau hanya berisi tag HTML.")
        return cleaned

    def validate_ringkasan(self, value):
        cleaned = strip_tags(value).strip()
        if not cleaned:
            raise serializers.ValidationError("Ringkasan tidak boleh kosong atau hanya berisi tag HTML.")
        return cleaned

    def validate_konten(self, value):
        cleaned = strip_tags(value).strip()
        if not cleaned:
            raise serializers.ValidationError("Isi panduan tidak boleh kosong atau hanya berisi tag HTML.")
        return cleaned

    def validate_image_url(self, value):
        if value:
            value = value.strip()
            if not value.startswith("https://"):
                raise serializers.ValidationError("Tautan gambar sampul harus berawalan https://")
        return value