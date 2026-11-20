from django.db import transaction
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from rest_framework import mixins, status, viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import BasePermission
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response

from favorites.models import Favorite
from favorites.querysets import editable_favorites, visible_favorites
from favorites.serializers import FavoriteCreateSerializer, FavoriteSerializer
from favorites.services import save_favorite
from listings.models import Listing
from profiles.access import has_complete_profile


class HasCompleteProfile(BasePermission):
    message = "Lengkapi profil untuk mengakses favorit."

    def has_permission(self, request, view):
        return has_complete_profile(request.user)


class FavoritePagination(PageNumberPagination):
    page_size = 20


@method_decorator(never_cache, name="dispatch")
class FavoriteViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.UpdateModelMixin,
    mixins.DestroyModelMixin, viewsets.GenericViewSet,
):
    authentication_classes = [SessionAuthentication]
    permission_classes = [HasCompleteProfile]
    renderer_classes = [JSONRenderer]
    serializer_class = FavoriteSerializer
    pagination_class = FavoritePagination

    def get_queryset(self):
        user = self.request.user
        if self.action == "destroy":
            # The owner can remove an old favorite without reading a hidden listing.
            return Favorite.objects.filter(user=user)
        if self.action == "partial_update":
            return editable_favorites(user)
        favorites = visible_favorites(user)
        if self.action == "list":
            category = self.request.query_params.get("category", "")
            if category:
                if category not in Listing.Category.values:
                    raise ValidationError({"category": "Kategori tidak valid."})
                favorites = favorites.filter(listing__category=category)
        return favorites

    def get_serializer_class(self):
        if self.request.method == "POST":
            return FavoriteCreateSerializer
        return super().get_serializer_class()

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        favorite, created = save_favorite(request.user, serializer.validated_data["listing_id"])
        return Response(
            FavoriteSerializer(favorite).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @transaction.atomic
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)
