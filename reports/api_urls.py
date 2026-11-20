from django.urls import path
from reports import api_views

app_name = "reports_api"
urlpatterns = [
    path("", api_views.report_list, name="report-list"),
    path("/<uuid:report_id>/", api_views.report_detail, name="report-detail"),
]