from rest_framework import serializers

from listings.models import Listing
from profiles.models import Profile


class ListingCardSerializer(serializers.ModelSerializer):
    # Data satu kartu di katalog. Sama seperti kartu di web: tanpa deskripsi, kontak, dan koordinat.
    sustainability_tags = serializers.ListField(child=serializers.CharField(), read_only=True)
    is_favorited = serializers.SerializerMethodField()

    class Meta:
        model = Listing
        fields = (
            "id", "title", "brand", "category", "size", "condition", "price", "image_url", "city",
            "status", "sustainability_tags", "is_favorited", "created_at",
        )

    def get_is_favorited(self, listing):
        # Diisi with_favorite_state di view. Kalau tidak ada (misalnya listing baru dibuat), anggap False.
        return bool(getattr(listing, "is_favorited", False))


class ListingMineSerializer(ListingCardSerializer):
    # Baris di "Listing saya": kartu ditambah waktu terakhir diubah dan waktu terjual.
    class Meta(ListingCardSerializer.Meta):
        fields = ListingCardSerializer.Meta.fields + ("updated_at", "sold_at")


class ListingDetailSerializer(ListingCardSerializer):
    # Data halaman detail: semua isi kartu ditambah deskripsi, tag mentah, dan penjual.
    seller = serializers.SerializerMethodField()
    is_owner = serializers.SerializerMethodField()
    latitude = serializers.SerializerMethodField()
    longitude = serializers.SerializerMethodField()

    class Meta(ListingCardSerializer.Meta):
        fields = ListingCardSerializer.Meta.fields + (
            "description", "is_repairable", "is_upcycled", "is_locally_available", "extends_clothing_life",
            "sold_at", "updated_at", "seller", "is_owner", "latitude", "longitude",
        )

    def get_is_owner(self, listing):
        user = self.context["request"].user
        return user.is_authenticated and user.pk == listing.seller_id

    def get_seller(self, listing):
        # Hanya nama tampilan dan id. Kontak penjual diambil lewat API profil, yang punya aturan aksesnya sendiri.
        profile = Profile.objects.filter(user_id=listing.seller_id).first()
        name = ""
        if profile:
            name = profile.display_name.strip()
        return {
            "id": listing.seller_id,
            "display_name": name or "Penjual Pakelagi",
            "active_listings": Listing.objects.filter(
                seller_id=listing.seller_id, status=Listing.Status.AVAILABLE,
            ).count(),
        }

    # Koordinat hanya untuk pemilik (dipakai saat mengedit). Pengunjung lain cukup melihat nama kota.
    def get_latitude(self, listing):
        if self.get_is_owner(listing) and listing.latitude is not None:
            return str(listing.latitude)
        return None

    def get_longitude(self, listing):
        if self.get_is_owner(listing) and listing.longitude is not None:
            return str(listing.longitude)
        return None
