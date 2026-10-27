from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
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
    
    #Untuk randomly get 1 Guide acak untuk featured
    
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
    
    # Convert teks markdown ke HTML
    content_html = md.convert(guide.konten)
    
    #Ekstrak daftar isi untuk jadi bagian dari table of content
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
def user_drafts(request):
    # Ambil draft User
    drafts = Guide.objects.filter(author=request.user).order_by('-date_submitted')
    pending_count = drafts.filter(status='PENDING').count()
    
    if request.method == 'POST':
        form = GuideForm(request.POST)
        if form.is_valid():
            new_guide = form.save(commit=False)
            new_guide.author = request.user # Set author jadi user
            new_guide.status = 'PENDING'
            new_guide.save()
            messages.success(request, "Draf panduan berhasil dibuat menunggu approval admin")
            return redirect('sustainableguides:drafts')
    else:
        form = GuideForm()
        
    context = {
        'drafts': drafts,
        'pending_count': pending_count,
        'form': form,
    }
    return render(request, 'sustainableguides/user_drafts.html', context)
    
@login_required(login_url='accounts:login')
def edit_draft(request, id):
    guide = get_object_or_404(Guide, id=id, author=request.user, status='PENDING')
    
    if request.method == 'POST':
        form = GuideForm(request.POST, instance=guide)
        if form.is_valid():
            form.save()
            messages.success(request, "Draf berhasil diperbarui.")
            return redirect('sustainableguides:drafts')
    else:
        form = GuideForm(instance=guide)
        
    context = {
        'form': form, 
        'guide': guide
    }
        
    return render(request, 'sustainableguides/edit_draft.html', context)

@login_required(login_url='accounts:login')
def delete_draft(request, id):
    guide = get_object_or_404(Guide, id=id, author=request.user, status='PENDING')
    
    if request.method == 'POST':
        guide.delete()
        messages.success(request, "Draf berhasil dihapus.")
        
    return redirect('sustainableguides:drafts')


