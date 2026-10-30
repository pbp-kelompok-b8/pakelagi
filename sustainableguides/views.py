from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils.html import escape
import markdown
from .models import Guide
from .forms import GuideForm

# Create your views here.

#=x=x=x=x=x=x=x=x=x=x=x==x=x=x=x=x=x=x
# Public Access
#=x=x=x=x=x=x=x=x=x==x=x=x=x=x=x=x=x=x

def guide_list(request):
    published_guides = Guide.objects.filter(status='DISETUJUI', is_published=True).order_by('-date_published')
    
    # Untuk filter kategory
    category_filter = request.GET.get('category')
    if category_filter:
        published_guides = published_guides.filter(category=category_filter)
    
    # Untuk randomly get 1 Guide acak untuk featured
    featured_guide = published_guides.order_by('?').first()
    
    context = {
        'guides': published_guides,
        'featured_guide': featured_guide,
        'active_category': category_filter or 'SEMUA',
    }
    return render(request, 'sustainableguides/guide_list.html', context)

def guide_detail(request, id):
    guide = get_object_or_404(Guide, id=id, status='DISETUJUI', is_published=True)
    
    # Initialize Markdown format
    md = markdown.Markdown(extensions=['toc', 'tables', 'nl2br'])
    
    # KEAMANAN XSS: Escape tag HTML mentah sebelum di-convert ke Markdown,
    # lalu netralisir skema javascript: jika ada di dalam link Markdown
    safe_konten = escape(guide.konten)
    content_html = md.convert(safe_konten).replace('href="javascript:', 'href="#blocked-javascript:')
    
    # Ekstrak daftar isi untuk jadi bagian dari table of content
    table_of_contents = md.toc
    
    # Untuk Panduan Lainnya
    other_guides = Guide.objects.filter(status='DISETUJUI', is_published=True).exclude(id=guide.id).order_by('?')[:3]
    
    context = {
        'guide': guide,
        'content_html': content_html,
        'table_of_contents': table_of_contents,
        'other_guides': other_guides,
    }
    return render(request, 'sustainableguides/guide_detail.html', context)

#=x=x=x=x=x=x=x=x=x=x=x==x=x=x=x=x=x=x
# Member Access
#=x=x=x=x=x=x=x=x=x==x=x=x=x=x=x=x=x=x

@login_required(login_url='accounts:login')
def user_drafts(request, form=None):
    # Ambil draft User berdasarkan tanggal submit dan menghitung yang pending
    drafts = Guide.objects.filter(author=request.user).order_by('-date_submitted')
    pending_count = drafts.filter(status='PENDING').count()
    
    # Gunakan form yang dilempar dari submit_draft jika ada error validasi
    if form is None:
        form = GuideForm()
    
    context = {
        'drafts': drafts,
        'pending_count': pending_count,
        'form': form
    }
    return render(request, 'sustainableguides/user_drafts.html', context)

@login_required(login_url='accounts:login')
def submit_draft(request):
    if request.method == 'POST':
        form = GuideForm(request.POST)
        if form.is_valid():
            guide = form.save(commit=False)
            guide.author = request.user
            guide.status = 'PENDING'
            guide.save()
            messages.success(request, 'Draf panduan berhasil dikirim dan menunggu tinjauan admin.')
            return user_drafts(request)
        else:
            messages.error(request, 'Gagal mengirim draf. Periksa kembali isian form.')
            # Lempar form yang gagal validasi agar pesan error clean_<field> muncul di HTML
            return user_drafts(request, form=form)
            
    return user_drafts(request)
    
@login_required(login_url='accounts:login')
def edit_draft(request, id):
    guide = get_object_or_404(Guide, id=id, author=request.user)
    
    # Tolak jika status bukan pending
    if guide.status != 'PENDING':
        messages.error(request, "Draf yang sudah disetujui atau ditolak tidak dapat diubah lagi.")
        return redirect('sustainableguides:my_submissions')

    if request.method == 'POST':
        form = GuideForm(request.POST, instance=guide)
        if form.is_valid():
            form.save()
            messages.success(request, 'Draf panduan berhasil diperbarui.')
            return redirect('sustainableguides:my_submissions')
    else:
        form = GuideForm(instance=guide)

    context = {
        'form': form, 
        'guide': guide
    }
    return render(request, 'sustainableguides/edit_draft.html', context)

@login_required(login_url='accounts:login')
def delete_draft(request, id):
    guide = get_object_or_404(Guide, id=id, author=request.user)
    
    if request.method == 'POST':
        # Validasi Kunci
        if guide.status == 'PENDING':
            title = guide.title
            guide.delete()
            messages.success(request, f"Draf '{title}' berhasil dibatalkan dan dihapus.")
        else:
            messages.error(request, "Draf yang sudah ditinjau admin tidak dapat dihapus.")
            
    return user_drafts(request)