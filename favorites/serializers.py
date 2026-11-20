from rest_framework import serializers

from favorites.models import Favorite
from favorites.services import save_favorite_note
from listings.models import Listing


class FavoriteListingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Listing
        fields = ("id", "title", "price", "category", "image_url", "status")


class FavoriteSerializer(serializers.ModelSerializer):
    listing = FavoriteListingSerializer(read_only=True)

    class Meta:
        model = Favorite
        fields = ("id", "listing", "note", "created_at", "updated_at")

    def update(self, instance, validated_data):
        if "note" in validated_data:
            save_favorite_note(instance, validated_data["note"])
        return instance


class FavoriteCreateSerializer(serializers.Serializer):
    listing_id = serializers.IntegerField(min_value=1, max_value=2**63 - 1)
