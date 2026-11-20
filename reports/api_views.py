from collections.abc import Mapping

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.views.decorators.cache import never_cache
from rest_framework import serializers, status
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import (
    api_view, authentication_classes, permission_classes,
)
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from listings.models import Listing
from reports.forms import ReportForm
from reports.models import Report, ReportModeratorNote
from reports.permissions import HasCompleteProfile
from reports.serializers import ReportSerializer


def report_queryset(user, *, read=False):
    if read and user.is_superuser:
        return Report.objects.all()
    return Report.objects.filter(reporter=user)


def positive_id(field, value):
    try:
        return serializers.IntegerField(min_value=1, max_value=2**63 - 1).run_validation(value)
    except ValidationError as exc:
        raise ValidationError({field: exc.detail}) from exc


def report_input(request, *, create=False):
    data = request.data
    if not isinstance(data, Mapping):
        raise ValidationError({"__all__": ["Kirim objek JSON."]})
    text_fields = {"reason", "description"}
    allowed = text_fields | {"listing"} if create else text_fields
    errors = {field: ["Field ini tidak dapat diisi."] for field in data if field not in allowed}
    errors.update({field: ["Masukkan teks."] for field in text_fields & data.keys()
                   if not isinstance(data[field], str)})
    if errors:
        raise ValidationError(errors)
    return dict(data.items())


def validated_form(data, report):
    form = ReportForm(data, instance=report)
    if not form.is_valid():
        raise ValidationError(form.errors)
    return form


@never_cache
@api_view(["GET", "HEAD", "POST"])
@authentication_classes([SessionAuthentication])
@permission_classes([HasCompleteProfile])
def report_list(request):
    if request.method in ("GET", "HEAD"):
        reports = report_queryset(request.user, read=True).order_by("listing_title", "id")
        if request.user.is_superuser and "reporter" in request.query_params:
            reporter_id = positive_id("reporter", request.query_params["reporter"])
            reports = reports.filter(reporter_id=reporter_id)
        return Response(ReportSerializer(reports, many=True).data)

    data = report_input(request, create=True)
    listing_id = positive_id("listing", data.pop("listing", serializers.empty))
    listing = get_object_or_404(Listing.objects.exclude(status=Listing.Status.HIDDEN), pk=listing_id)
    form = validated_form(data, Report(reporter=request.user, listing=listing))
    report = form.save_new()
    if report is None:
        raise ValidationError(form.errors)
    return Response(ReportSerializer(report).data, status=status.HTTP_201_CREATED)


@never_cache
@api_view(["GET", "HEAD", "PUT", "PATCH", "DELETE"])
@authentication_classes([SessionAuthentication])
@permission_classes([HasCompleteProfile])
def report_detail(request, report_id):
    if request.method in ("GET", "HEAD"):
        report = get_object_or_404(report_queryset(request.user, read=True), pk=report_id)
        return Response(ReportSerializer(report).data)

    return change_report(request, report_id)


@transaction.atomic
def change_report(request, report_id):
    # Serialize writes with status changes before checking if the report is still open.
    report = get_object_or_404(report_queryset(request.user).select_for_update(), pk=report_id)
    if not report.is_editable:
        raise PermissionDenied("Laporan yang sudah ditinjau moderator tidak bisa diubah atau dihapus.")

    if request.method == "DELETE":
        # An open report can already have moderator notes; deletion would cascade to them.
        if ReportModeratorNote.objects.filter(report_id=report).exists():
            raise PermissionDenied("Laporan ini tidak bisa dihapus.")
        report.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    data = report_input(request)
    if request.method == "PATCH":
        data = {"reason": report.reason, "description": report.description, **data}
    form = validated_form(data, report)
    form.save(commit=False).save(update_fields=["reason", "description", "updated_at"])
    return Response(ReportSerializer(report).data)