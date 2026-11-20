"""REST API listing untuk aplikasi mobile. Aturannya sama dengan halaman web di listings/views.py."""

from django.db.models import Count, Q
from django.forms.models import model_to_dict
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, BasePermission
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from favorites.presentation import with_favorite_state
from listings import nominatim
from listings.filters import filter_listings, get_catalog_filter
from listings.forms import ListingForm
from listings.models import Listing
from listings.serializers import ListingCardSerializer, ListingDetailSerializer, ListingMineSerializer
from listings.views import MINE_TABS, get_manageable_listing
from profiles.access import has_complete_profile


class HasCompleteProfile(BasePermission):
    message = "Lengkapi profil untuk mengelola listing."

    def has_permission(self, request, view):
        return has_complete_profile(request.user)


class ListingPagination(PageNumberPagination):
    page_size = 12


@method_decorator(never_cache, name="dispatch")
class ListingAPIView(APIView):
    # Dasar semua endpoint listing: login lewat session Django (sama seperti web) dan balasan selalu JSON.
    # GET terbuka untuk semua orang kecuali di view yang mengubah member_only menjadi True.
    authentication_classes = [SessionAuthentication]
    renderer_classes = [JSONRenderer]
    member_only = False

    def get_permissions(self):
        if self.member_only or self.request.method not in ("GET", "HEAD", "OPTIONS"):
            return [HasCompleteProfile()]
        return [AllowAny()]


def form_data(data):
    # Ubah body request menjadi dictionary biasa untuk ListingForm.
    # Form menerima teks, angka, dan boolean. List atau objek di dalam field ditolak.
    if hasattr(data, "dict"):
        data = data.dict()   # QueryDict dari form-encoded/multipart
    if not isinstance(data, dict):
        raise ValidationError({"non_field_errors": ["Data harus berupa objek JSON."]})
    salah = {}
    for name, value in data.items():
        if isinstance(value, (list, dict)):
            salah[name] = ["Harus berupa teks, angka, atau boolean."]
    if salah:
        raise ValidationError(salah)
    return dict(data)


def form_errors(form):
    # Error ListingForm dalam format DRF: {"field": ["pesan"]}. Error umum ("__all__") jadi non_field_errors.
    errors = {}
    for field, messages in form.errors.items():
        if field == "__all__":
            field = "non_field_errors"
        errors[field] = [str(message) for message in messages]
    return errors


def detail_response(request, listing, status_code=status.HTTP_200_OK):
    # Ambil ulang beserta status favorit, supaya isinya sama persis dengan GET detail.
    listing = with_favorite_state(Listing.objects.select_related("seller"), request.user).get(pk=listing.pk)
    serializer = ListingDetailSerializer(listing, context={"request": request})
    return Response(serializer.data, status=status_code)


class ListingListCreateAPI(ListingAPIView):
    # GET  /api/v1/listings/  katalog publik, parameter filter sama dengan halaman /listings/
    # POST /api/v1/listings/  menerbitkan listing baru (member berprofil lengkap)

    def get(self, request):
        catalog_filter = get_catalog_filter(request.query_params)
        available = Listing.objects.filter(status=Listing.Status.AVAILABLE)
        listings = with_favorite_state(filter_listings(available, catalog_filter), request.user)

        paginator = ListingPagination()
        page = paginator.paginate_queryset(listings, request, view=self)
        serializer = ListingCardSerializer(page, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        form = ListingForm(form_data(request.data))
        if not form.is_valid():
            raise ValidationError(form_errors(form))
        listing = form.save(commit=False)
        listing.seller = request.user   # penjual selalu akun yang login, tidak pernah dari input
        listing.save()
        return detail_response(request, listing, status.HTTP_201_CREATED)


class ListingDetailAPI(ListingAPIView):
    # GET    /api/v1/listings/<id>/  detail
    # PATCH  /api/v1/listings/<id>/  ubah sebagian field (pemilik atau admin)
    # DELETE /api/v1/listings/<id>/  hapus (pemilik atau admin)

    def get(self, request, pk):
        listing = get_object_or_404(with_favorite_state(Listing.objects.select_related("seller"), request.user), pk=pk)
        user = request.user
        is_owner = user.is_authenticated and user.pk == listing.seller_id

        # Sama seperti web: Hidden hanya terlihat oleh penjual dan admin
        if listing.status == Listing.Status.HIDDEN and not (is_owner or user.is_staff):
            raise Http404
        serializer = ListingDetailSerializer(listing, context={"request": request})
        return Response(serializer.data)

    def patch(self, request, pk):
        listing = get_manageable_listing(request, pk)

        # Field yang tidak dikirim memakai nilai lama, lalu semuanya divalidasi ulang oleh ListingForm.
        # status dan seller tidak ada di form, jadi kalau dikirim akan diabaikan.
        data = model_to_dict(listing, fields=ListingForm.Meta.fields)
        data.update(form_data(request.data))
        form = ListingForm(data, instance=listing)
        if not form.is_valid():
            raise ValidationError(form_errors(form))
        form.save()
        return detail_response(request, listing)

    def delete(self, request, pk):
        listing = get_manageable_listing(request, pk)
        listing.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ListingStatusAPI(ListingAPIView):
    # POST /api/v1/listings/<id>/status/  {"status": "Sold"} atau {"status": "Available"}, hanya pemilik

    def post(self, request, pk):
        listing = get_manageable_listing(request, pk, owner_only=True)

        new_status = None
        if isinstance(request.data, dict):
            new_status = request.data.get("status")
        if new_status not in (Listing.Status.AVAILABLE, Listing.Status.SOLD):
            raise ValidationError({"status": ["Status harus Available atau Sold."]})

        if listing.status == Listing.Status.HIDDEN:
            return Response(
                {"detail": "Listing yang disembunyikan moderator tidak bisa diubah statusnya."},
                status=status.HTTP_409_CONFLICT,
            )

        if listing.status != new_status:
            listing.status = new_status
            listing.save(update_fields=["status", "updated_at"])
        return detail_response(request, listing)


class ListingMineAPI(ListingAPIView):
    # GET /api/v1/listings/mine/?status=tersedia|terjual|disembunyikan  listing milik akun yang login
    member_only = True

    def get(self, request):
        mine = Listing.objects.filter(seller=request.user)
        # Dihitung sebelum difilter tab, supaya angka setiap tab selalu lengkap
        counts = mine.aggregate(
            all=Count("pk"),
            tersedia=Count("pk", filter=Q(status=Listing.Status.AVAILABLE)),
            terjual=Count("pk", filter=Q(status=Listing.Status.SOLD)),
            disembunyikan=Count("pk", filter=Q(status=Listing.Status.HIDDEN)),
        )

        tab = request.query_params.get("status", "")
        if tab not in MINE_TABS:
            tab = ""
        if tab:
            mine = mine.filter(status=MINE_TABS[tab])

        paginator = ListingPagination()
        page = paginator.paginate_queryset(mine.order_by("-updated_at", "-id"), request, view=self)
        serializer = ListingMineSerializer(page, many=True, context={"request": request})
        response = paginator.get_paginated_response(serializer.data)
        response.data["status"] = tab
        response.data["counts"] = counts
        return response


class LocationSearchAPI(ListingAPIView):
    # GET /api/v1/listings/locations/?city=...  saran kota dari Nominatim untuk form listing
    # Hanya member, karena setiap pencarian memakai jatah 1 request/detik ke Nominatim.
    member_only = True

    def get(self, request):
        query = " ".join(request.query_params.get("city", "").split())[:nominatim.MAX_QUERY_LENGTH]
        results, search_status = nominatim.search(query)
        return Response({
            "query": query,
            "status": search_status,
            "results": results,
            "attribution": "Data lokasi © OpenStreetMap contributors",
        })
