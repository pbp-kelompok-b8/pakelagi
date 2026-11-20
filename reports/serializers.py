from django.utils.html import strip_tags
from rest_framework import serializers

from reports.models import Report


class ReportSerializer(serializers.ModelSerializer):

    class Meta:
        model = Report
        fields = [
            "id", "reporter", "listing", "listing_title", "reason", "description", "status", "created_at", "updated_at",
        ]
        read_only_fields = ["id"]

    def validate_title(self, value):
        value = strip_tags(value).strip()
        if not value:
            raise serializers.ValidationError("Title cannot be empty.")
        return value