from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from django.db import transaction
from django.urls import reverse
import markdown
from sustainableguides.models import Guide
from listings.models import Listing
from reports.models import Report, ReportModeratorNote
from reports.forms import ReportModerationForm
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
    count_published = all_guides.filter(status='DISETUJUI', is_published=True).count()
    count_rejected = all_guides.filter(status='DITOLAK').count()
    
    # Tangkap parameter filter tab dari URL (Default: 'pending' / DRAF MASUK)
    active_tab = request.GET.get('tab', 'pending').lower()
    
    if active_tab == 'approved':
        filtered_guides = all_guides.filter(status='DISETUJUI')
    elif active_tab == 'published':
        filtered_guides = all_guides.filter(status='DISETUJUI', is_published=True)
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
        
    # Render Markdown untuk draf yang sedang dipilih di panel kanan
    selected_content_html = ""
    if selected_guide:
        md = markdown.Markdown(extensions=['toc', 'tables', 'nl2br'])
        selected_content_html = md.convert(selected_guide.konten)
    
    context = {
        'active_tab': active_tab,
        'guides': filtered_guides,
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
        notes = request.POST.get('rejected_notes', '').strip()

        if action == 'approve':
            guide.status = 'DISETUJUI'
            guide.save()
            messages.success(request, f"Panduan '{guide.title}' telah disetujui dan diterbitkan.")
            return redirect('/moderation/jurnal/?tab=published')

        elif action == 'reject':
            if not notes:
                messages.error(request, "Catatan untuk pengirim wajib diisi bila menolak draf.")
                return redirect(f"/moderation/jurnal/?tab=pending&id={guide.id}")
                
            guide.status = 'DITOLAK'
            guide.rejected_notes = notes
            guide.is_published = False
            guide.save()
            messages.error(request, f"Draf '{guide.title}' telah ditolak.")
            return redirect('/moderation/jurnal/?tab=rejected')

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

# =x=x=x=x=x=x=x==x=x=x=x=
# Moderasi untuk Laporan
# =x=x=x=x=x=x=x==x=x=x=x=
@user_passes_test(is_admin, login_url='accounts:login')
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
    selected_id = request.GET.get('id')
    if selected_id:
        selected_report = all_reports.filter(id=selected_id).first()
    else:
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
def review_report_action(request, pk):
    report = get_object_or_404(Report, pk=pk)
    
    if request.method == "POST":
        action = request.POST.get("action")
        toggle = request.POST.get("toggle")
        note = request.POST.get("moderator_note")
        
        if action == "review":
            report.status = "reviewing"
            success_msg = "Laporan berhasil masuk ke tahap review"
        elif action == "resolve":
            report.status = "resolved"
            success_msg = "Laporan berhasil diselesaikan"
        elif action == "reject":
            report.status = "rejected"
            success_msg = "Laporan berhasil ditolak"
        else:
            return redirect("moderations:reports_list")
        report.save()
        
        if note:
            ReportModeratorNote.objects.create(
                report=report,
                moderator=request.user,
                note=note
            )
        
        if toggle:
            listing = report.listing 
            listing.status = Listing.Status.HIDDEN
            listing.save()
        
        messages.success(request, success_msg)
        redirect_url = reverse("moderations:reports_list")
        return redirect(f"{redirect_url}?tab={report.status}")
    
    return redirect("moderations:reports_list")