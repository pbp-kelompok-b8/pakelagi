from django.utils.html import strip_tags
from rest_framework import serializers

from reports.models import Report


class ReportSerializer(serializers.ModelSerializer):

    class Meta:
        model = Report
        fields = [
            "id", "reporter", "listing", "listing_title", "reason", "description", "status", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "reporter", "status"]
