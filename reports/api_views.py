from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import (
    api_view, authentication_classes, permission_classes,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from reports.models import Report
from reports.permissions import IsSuperOrAdminOrReadOnly
from reports.serializers import ReportSerializer


@api_view(["GET", "HEAD", "POST"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsSuperOrAdminOrReadOnly])
def report_list(request):
    if request.method in ("GET", "HEAD"):
        reports = Report.objects.select_related("reporter", "listing").order_by("listing_title", "id")
        reporter = request.query_params.get("reporter", "").strip()
        if reporter:
            reports = reports.filter(reporter__id=reporter)
        serializer = ReportSerializer(
            reports, many=True, context={"request": request},
        )
        return Response(serializer.data)

    serializer = ReportSerializer(data=request.data, context={"request": request})
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data, status=status.HTTP_201_CREATED)

@api_view(["GET", "HEAD", "PUT", "PATCH", "DELETE"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsSuperOrAdminOrReadOnly])
def report_detail(request, project_id):
    report = get_object_or_404(
        Report.objects.select_related("reporter", "listing"), pk=project_id,
    )
    if request.method in ("GET", "HEAD"):
        serializer = ReportSerializer(report, context={"request": request})
        return Response(serializer.data)

    if request.method == "DELETE":
        report.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = ReportSerializer(
        report, data=request.data, partial=request.method == "PATCH",
        context={"request": request},
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)