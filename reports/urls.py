from django.urls import path

from reports import views

app_name = "reports"

urlpatterns = [
    path("", views.report_list, name="list"),
    path("create/<int:listing_id>/", views.report_create, name="create"),
    path("<uuid:pk>/edit/", views.report_edit, name="edit"),
    path("<uuid:pk>/delete/", views.report_delete, name="delete"),
]