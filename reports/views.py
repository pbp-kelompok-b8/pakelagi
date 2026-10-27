from django.contrib import messages
from django.core.paginator import Paginator
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.db.models import Count, Q
from django.urls import reverse
from django.utils.cache import patch_vary_headers
from django.views.decorators.http import require_GET, require_http_methods
from django.db import IntegrityError, transaction

from listings.models import Listing
from profiles.access import member_required
from profiles.models import Profile
from reports.forms import ReportForm
from reports.models import Report

REPORTS_PAGE_SIZE = 10


def is_htmx_partial(request):
    # Same rule as the catalog: browser "back" needs the full page, not a fragment.
    return (request.headers.get("HX-Request") == "true"
            and request.headers.get("HX-History-Restore-Request") != "true")


def get_editable_report(request, pk):
    # Someone else's report -> 404 (not 403), so IDs can't be guessed.
    # Returns (report, None) if it can be changed, else (None, redirect response).
    report = get_object_or_404(Report, pk=pk, reporter=request.user)
    if not report.is_editable:
        messages.error(request, "Laporan yang sudah ditinjau moderator tidak bisa diubah atau dihapus.")
        return None, redirect("reports:list")
    return report, None

def render_reports(request, form=None, listing=None, report=None):
    # Satu halaman untuk tiga keadaan: daftar saja, form buat, atau form ubah.
    # defer() menjaga catatan moderator tetap di luar memori, jadi tidak mungkin bocor lewat template.
    reports = (Report.objects.filter(reporter=request.user)
               .select_related("listing").defer("moderator_note"))
    counts = reports.aggregate(total=Count("pk"), open=Count("pk", filter=Q(status="open")))
    page = Paginator(reports, REPORTS_PAGE_SIZE).get_page(request.GET.get("page"))

    seller_profile = None
    if listing:
        seller_profile = Profile.objects.filter(user_id=listing.seller_id).first()

    return render(request, "reports/list.html", {
        "page": page,
        "counts": counts,
        "form": form,
        "listing": listing,
        "report": report,
        "seller_name": seller_profile.display_name if seller_profile else "Penjual Pakelagi",
    })


@member_required
@require_GET
def report_list(request):
    return render_reports(request)


@member_required
@require_http_methods(["GET", "POST"])
def report_create(request, listing_id):
    listing = get_object_or_404(Listing, pk=listing_id)
    if listing.status == Listing.Status.HIDDEN:
        raise Http404
    if listing.seller_id == request.user.pk:
        messages.error(request, "Kamu tidak bisa melaporkan listing milikmu sendiri.")
        return redirect("listings:detail", pk=listing.pk)

    # Instance terisi lebih dulu supaya Report.clean() (listing sendiri, hidden, duplikat) ikut berjalan.
    form = ReportForm(
        request.POST if request.method == "POST" else None,
        instance=Report(reporter=request.user, listing=listing),
    )
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                form.save()
        except IntegrityError:
            form.add_error(None, "Kamu sudah melaporkan listing ini dan laporannya masih diproses.")
        else:
            messages.success(request, "Laporan terkirim. Moderator akan meninjaunya.")
            return redirect("reports:list")
    return render_reports(request, form=form, listing=listing)


@member_required
@require_http_methods(["GET", "POST"])
def report_edit(request, pk):
    report, blocked = get_editable_report(request, pk)
    if blocked:
        return blocked

    form = ReportForm(request.POST or None, instance=report)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Laporan diperbarui.")
        return redirect("reports:list")
    return render_reports(request, form=form, listing=report.listing, report=report)

@member_required
@require_http_methods(["GET", "POST"])
def report_delete(request, pk):
    report, blocked = get_editable_report(request, pk)
    if blocked:
        return blocked

    if request.method == "POST":
        title = report.listing.title if report.listing else report.listing_title
        report.delete()
        messages.success(request, f"Laporan untuk “{title}” dihapus.")
        return redirect("reports:list")
    return render(request, "reports/confirm_delete.html", {"report": report})