from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.views.decorators.http import require_POST, require_GET
from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils.html import strip_tags
from django.contrib import messages
from django.db import transaction
from django.urls import reverse
import markdown
from sustainableguides.models import Guide
from listings.models import Listing
from reports.models import Report, ReportModeratorNote
from reports.forms import ReportModerationForm
from django.utils import timezone
from sustainableguides.models import Guide
from sustainableguides.rendering import render_guide_markdown
# Create your views here.

# =x=x=x=x=x=x=x==x=x=x=x=
# Helper Function untuk Authorization
# =x=x=x=x=x=x=x==x=x=x=x=
def is_admin(user):
    return user.is_authenticated and user.is_superuser

# =x=x=x=x=x=x=x==x=x=x=x=
# Landing Page
# =x=x=x=x=x=x=x==x=x=x=x=
@user_passes_test(is_admin, login_url='accounts:login')
def ringkasan_moderation(request):
    return render(request, 'moderations/ringkasan.html')

# =x=x=x=x=x=x=x==x=x=x=x=
# Moderasi untuk jurnal
# =x=x=x=x=x=x=x==x=x=x=x=

@user_passes_test(is_admin, login_url='accounts:login')
def jurnal_moderation(request):
    # Fungsi ini untuk menampilkan dashboard moderasi panduan
    all_guides = Guide.objects.select_related('author').order_by('-date_submitted')
    
    # Hitung untuk tiap jenis item
    count_pending = all_guides.filter(status='PENDING').count()
    count_approved = all_guides.filter(status='DISETUJUI').count()
    count_published = all_guides.published().count()
    count_rejected = all_guides.filter(status='DITOLAK').count()
    waiting_publish_guides = all_guides.filter(status='DISETUJUI').filter(
        Q(is_published=False) | Q(date_published__gt=timezone.now())
    )
    
    # Tangkap parameter filter tab dari URL (Default: 'pending' / DRAF MASUK)
    active_tab = request.GET.get('tab', 'pending').lower()
    
    if active_tab == 'approved':
        filtered_guides = all_guides.filter(status='DISETUJUI')
    elif active_tab == 'published':
        filtered_guides = all_guides.published()
    elif active_tab == 'rejected':
        filtered_guides = all_guides.filter(status='DITOLAK')
    else:
        active_tab = 'pending'
        filtered_guides = all_guides.filter(status='PENDING')
        
    # Tentukan draf mana yang ditampilkan di panel preview sebelah kanan
    selected_id = request.GET.get('id')
    if selected_id:
        selected_guide = all_guides.filter(id=selected_id).first()
    else:
        # Otomatis pilih item pertama dari tab yang sedang aktif jika belum ada yang diklik
        selected_guide = filtered_guides.first()
        if active_tab == 'pending' and not selected_guide:
            selected_guide = waiting_publish_guides.first()
        
    # Render Markdown untuk draf yang sedang dipilih di panel kanan
    selected_content_html = ""
    if selected_guide:
        selected_content_html, _ = render_guide_markdown(selected_guide.konten)
    
    context = {
        'active_tab': active_tab,
        'guides': filtered_guides,
        'waiting_publish_guides': waiting_publish_guides,
        'pending_guides': all_guides.filter(status='PENDING'),
        'approved_guides': all_guides.filter(status='DISETUJUI'),
        'rejected_guides': all_guides.filter(status='DITOLAK'),
        'count_pending': count_pending,
        'count_approved': count_approved,
        'count_published': count_published,
        'count_rejected': count_rejected,
        'selected_guide': selected_guide,
        'selected_content_html': selected_content_html,
    }
    return render(request, 'moderations/jurnal.html', context)

@user_passes_test(is_admin, login_url='accounts:login')
def review_jurnal_action(request, id):
    # Untuk handle POST Setuju or Tolak draf
    guide = get_object_or_404(Guide, id=id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        notes = strip_tags(request.POST.get('rejected_notes', '')).strip()

        direct_publish = request.POST.get('direct_publish') == 'true'
        
        if action == 'approve':
            guide.status = 'DISETUJUI'
            if direct_publish:
                guide.is_published = True
                guide.date_published = timezone.now()
            else:
                guide.is_published = False
            guide.save()
            if direct_publish:
                messages.success(request, f"Panduan '{guide.title}' disetujui dan langsung diterbitkan.")
                return redirect(f'/moderation/guides/?tab=published&id={guide.id}')
            else:
                messages.success(request, f"Draf '{guide.title}' disetujui (Menunggu jadwal terbit).")
                return redirect(f'/moderation/guides/?tab=approved&id={guide.id}')

        elif action == 'reject':
            if not notes:
                messages.error(request, "Catatan untuk pengirim wajib diisi bila menolak draf.")
                return redirect(f"/moderation/guides/?tab=pending&id={guide.id}")
                
            guide.status = 'DITOLAK'
            guide.rejected_notes = notes
            guide.is_published = False
            guide.save()
            messages.error(request, f"Draf '{guide.title}' telah ditolak.")
            return redirect(f'/moderation/guides/?tab=rejected&id={guide.id}')
        
    return redirect('moderations:jurnal_list')

@user_passes_test(is_admin, login_url='accounts:login')
def delete_jurnal_action(request, id):
    # Fungsi untuk handle delete post
    guide = get_object_or_404(Guide, id=id)
    
    if request.method == 'POST':
        title = guide.title
        guide.delete()
        messages.success(request, f"Panduan '{title}' berhasil dihapus secara permanen.")
        
    next_tab = request.GET.get('tab', 'pending')
    return redirect(f"/moderation/jurnal/?tab={next_tab}")

# Fungsi untuk publishing
@user_passes_test(is_admin, login_url='accounts:login')
def get_publish_modal(request, id):
    guide = get_object_or_404(Guide, id=id)
    context = {
        'guide': guide,
        'active_tab': request.GET.get('tab', 'approved')
    }
    return render(request, 'moderations/components/publish_modal.html', context)

@user_passes_test(is_admin, login_url='accounts:login')
def publish_jurnal_action(request, id):
    guide = get_object_or_404(Guide, id=id)
    if request.method == 'POST':
        if guide.status != 'DISETUJUI':
            messages.error(request, "Hanya panduan yang disetujui yang bisa diterbitkan.")
            return redirect('moderations:jurnal_list')

        publish_type = request.POST.get('publish_type')
        
        if publish_type == 'now':
            guide.is_published = True
            guide.date_published = timezone.now()
            guide.save()
            messages.success(request, f"Panduan '{guide.title}' berhasil diterbitkan sekarang!")
        
        elif publish_type == 'schedule':
            try:
                schedule_date = forms.DateTimeField().clean(request.POST.get('schedule_date'))
                if schedule_date <= timezone.now():
                    raise ValidationError("Waktu publikasi harus di masa mendatang.")
            except ValidationError:
                messages.error(request, "Isi tanggal dan waktu publikasi yang valid di masa mendatang.")
            else:
                guide.is_published = True
                guide.date_published = schedule_date
                guide.save()
                messages.success(request, f"Panduan '{guide.title}' dijadwalkan terbit pada {schedule_date}.")
    next_tab = request.GET.get('tab', 'approved')
    return redirect(f"/moderation/guides/?tab={next_tab}&id={guide.id}")

# Untuk toggle langsung di publish atau nggak
@user_passes_test(is_admin, login_url='accounts:login')
def toggle_publish_action(request, id):
    guide = get_object_or_404(Guide, id=id)
    if request.method == 'POST':
        if guide.status == 'DISETUJUI':
            # Balikkan statusnya (True jadi False, False jadi True)
            guide.is_published = not guide.is_published
            if guide.is_published:
                guide.date_published = timezone.now()
            guide.save()
            
            kata_status = "diterbitkan" if guide.is_published else "ditarik dari publikasi"
            messages.success(request, f"Status panduan '{guide.title}' diubah: {kata_status}.")
        else:
            messages.error(request, "Hanya panduan berstatus Disetujui yang bisa diubah status terbitnya.")

    next_tab = request.GET.get('tab', 'approved')
    return redirect(f"/moderation/guides/?tab={next_tab}&id={guide.id}")


# =x=x=x=x=x=x=x==x=x=x=x=
# Moderasi untuk Laporan
# =x=x=x=x=x=x=x==x=x=x=x=
@user_passes_test(is_admin, login_url='accounts:login')
@require_GET
def report_moderation(request):
# Fungsi ini untuk menampilkan dashboard moderasi laporan
    all_reports = Report.objects.order_by('updated_at')
    
    # Kumpulan report untuk masing-masing status
    report_open = all_reports.filter(status='open')
    report_reviewing = all_reports.filter(status='reviewing')
    report_resolved = all_reports.filter(status='resolved')
    report_rejected = all_reports.filter(status='rejected')
    
    # Hitung untuk tiap jenis item berdasarkan status laporan
    count_open = report_open.count()
    count_reviewing = report_reviewing.count()
    count_resolved = report_resolved.count()
    count_rejected = report_rejected.count()
    
    # Tangkap parameter filter tab dari URL (Default: 'open' / LAPORAN MASIH TERBUKA)
    active_tab = request.GET.get('tab', 'open').lower()
    
    if active_tab == 'reviewing':
        filtered_reports = report_reviewing
    elif active_tab == 'resolved':
        filtered_reports = report_resolved
    elif active_tab == 'rejected':
        filtered_reports = report_rejected
    else:
        active_tab = 'open'
        filtered_reports = report_open
        
    # Tentukan draf mana yang ditampilkan di panel preview sebelah kanan
    try:
        selected_report = all_reports.filter(id=request.GET.get('id')).first()
    except (ValueError, ValidationError):  # id bukan UUID valid
            selected_report = None
    if selected_report == None: 
        # Otomatis pilih item pertama dari tab yang sedang aktif jika belum ada yang diklik
        selected_report = filtered_reports.first()
        
    context = {
        'active_tab': active_tab,
        'guides': filtered_reports,
        'pending_guides': all_reports.filter(status='PENDING'),
        'approved_guides': all_reports.filter(status='DISETUJUI'),
        'rejected_guides': all_reports.filter(status='DITOLAK'),
        'count_open': count_open,
        'count_reviewing': count_reviewing,
        'count_resolved': count_resolved,
        'count_rejected': count_rejected,
        'selected_report': selected_report,
    }
    return render(request, 'moderations/reports.html', context)

@user_passes_test(is_admin, login_url='accounts:login')
@require_POST
def review_report_action(request, pk):
    report = get_object_or_404(Report, pk=pk)
    status = request.POST.get("status")
    note_text = request.POST.get("moderator_note", "").strip()[:1000]
    if status not in dict(Report.STATUS):
        messages.error(request, "Status tidak valid.")
    elif status == "rejected" and not note_text:
        messages.error(request, "Catatan moderator wajib diisi bila laporan ditolak.")
    else:
        report.status= status
        ReportModeratorNote.objects.create(report_id=report.pk, moderator_id=request.user.pk, note=note_text )
        report.save(update_fields=["status", "updated_at"])
        messages.success(request, "Keputusan tersimpan.")
        return redirect(f"{reverse('moderations:reports_list')}?tab={status}&id={report.pk}")
    return redirect(f"{reverse('moderations:reports_list')}?tab={report.status}&id={report.pk}")

@user_passes_test(is_admin, login_url='accounts:login')
@require_POST
def report_listing_action(request, pk):
    report = get_object_or_404(Report.objects.select_related("listing"), pk=pk)
    action = request.POST.get("action")
    if report.listing and action in ("hide", "restore"):
        report.listing.status = Listing.Status.HIDDEN if action == "hide" else Listing.Status.AVAILABLE
        report.listing.save(update_fields=["status", "updated_at"])
        messages.success(request, "Listing disembunyikan." if action == "hide" else "Listing dipulihkan.")
    return redirect(f"{reverse('moderations:reports_list')}?tab={report.status}&id={report.pk}")

@user_passes_test(is_admin, login_url='accounts:login')
@require_GET
def report_moderator_note_details(request, report_id):
    report = get_object_or_404(Report, report_id)
    notes = ReportModeratorNote.objects.filter(report=report).select_related('moderator').order_by('-created_at')
    return render(request, 'moderations/components/notes_popover.html', {
        'report': report,
        'notes': notes
    })