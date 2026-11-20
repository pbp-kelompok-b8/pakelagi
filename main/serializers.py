from django.templatetags.static import static
from rest_framework import serializers


class CategorySerializer(serializers.Serializer):
    value = serializers.CharField()
    label = serializers.CharField()
    slug = serializers.SlugField()
    count = serializers.IntegerField()
    image_url = serializers.SerializerMethodField()
    image_mobile_url = serializers.SerializerMethodField()

    def get_image_url(self, category):
        return self.context["request"].build_absolute_uri(static(category["image"]))

    def get_image_mobile_url(self, category):
        return self.context["request"].build_absolute_uri(static(category["image_mobile"]))
