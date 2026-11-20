from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny
from rest_framework.renderers import JSONRenderer

from main.categories import category_cards
from main.serializers import CategorySerializer


class CategoryList(ListAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    renderer_classes = [JSONRenderer]
    serializer_class = CategorySerializer
    pagination_class = None

    def get_queryset(self):
        return category_cards()
