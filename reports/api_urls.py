from django.urls import path
from reports import api_views

app_name = "api"
urlpatterns = [
    path("", api_views.report_list, name="report-list"),
]