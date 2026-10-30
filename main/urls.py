from django.urls import path
from main.views import category_index, show_main

app_name = "main"

urlpatterns = [
    path("", show_main, name="show_main"),
    path("categories/", category_index, name="category_index"),
]
