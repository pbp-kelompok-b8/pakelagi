from django.shortcuts import render

# Create your views here.
# TODO : show_reports
def show_reports(request):
    title_query = request.GET.get("title", "").strip()
    return render()

# TODO : create_reports
def create_reports():
    pass