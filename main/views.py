from django.shortcuts import render
from django.views.decorators.http import require_GET


def show_main(request):
    return render(request, "index.html")


@require_GET
def category_index(request):
    return render(request, "categories/index.html")
