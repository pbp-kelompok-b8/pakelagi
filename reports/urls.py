from django.urls import path
from reports.views import show_reports, create_reports

app_name = "reports"

urlpatterns = [
    path("", show_reports, name="show_reports"),
    path("create/<uuid:listing_id>/", create_reports, name="create_reports"),
]
