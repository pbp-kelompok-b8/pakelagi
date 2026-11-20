from django.shortcuts import render, redirect, get_object_or_404
from profiles.access import has_complete_profile, member_required
from django.contrib import messages
from .models import Guide
from .forms import GuideForm
from .rendering import render_guide_markdown
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import BasePermission, SAFE_METHODS
from .serializers import GuideSerializer

# Create your views here.

#=x=x=x=x=x=x=x=x=x=x=x==x=x=x=x=x=x=x
# Public Access
#=x=x=x=x=x=x=x=x=x==x=x=x=x=x=x=x=x=x

def guide_list(request):
    published_guides = Guide.objects.published().order_by('-date_published')
    
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
    guide = get_object_or_404(Guide.objects.published(), id=id)
    content_html, table_of_contents = render_guide_markdown(guide.konten)
    
    # Untuk Panduan Lainnya
    other_guides = Guide.objects.published().exclude(id=guide.id).order_by('?')[:3]
    
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

@member_required
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

@member_required
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
    
@member_required
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

@member_required
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

#=x=x=x=x=x=x=x=x=x=x=x==x=x=x=x=x=x=x
# REST API Views (Django REST Framework)
#=x=x=x=x=x=x=x=x=x==x=x=x=x=x=x=x=x=x

class HasCompleteProfile(BasePermission):
    message = 'Lengkapi profil untuk mengelola panduan.'

    def has_permission(self, request, view):
        return has_complete_profile(request.user)


class HasCompleteProfileOrReadOnly(HasCompleteProfile):
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS or super().has_permission(request, view)


class GuideAPIView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [HasCompleteProfileOrReadOnly]


class GuideListCreateAPIView(GuideAPIView):
    """
    GET: Menampilkan daftar panduan yang telah terbit (publik, bisa difilter ?category=...).
    POST: Membuat draf panduan baru dengan status PENDING (profil lengkap).
    """

    def get(self, request):
        guides = Guide.objects.published().order_by('-date_published')
        category = request.query_params.get('category')
        if category:
            guides = guides.filter(category=category)
        serializer = GuideSerializer(guides, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = GuideSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(author=request.user, status='PENDING')
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MyGuideSubmissionsAPIView(GuideAPIView):
    """
    GET: Menampilkan riwayat panduan sendiri (profil lengkap).
    """
    permission_classes = [HasCompleteProfile]

    def get(self, request):
        drafts = Guide.objects.filter(author=request.user).order_by('-date_submitted')
        serializer = GuideSerializer(drafts, many=True)
        return Response({
            'count': drafts.count(),
            'pending_count': drafts.filter(status='PENDING').count(),
            'results': serializer.data,
        }, status=status.HTTP_200_OK)


class GuideDetailAPIView(GuideAPIView):
    """
    GET: Publik jika sudah terbit; selain itu, hanya pemilik berprofil lengkap atau superuser.
    PUT / PATCH: Memperbarui draf panduan (hanya pemilik dan wajib masih berstatus PENDING).
    DELETE: Menghapus draf panduan (hanya pemilik dan wajib masih berstatus PENDING).
    """

    def get_object(self, id):
        return get_object_or_404(Guide, id=id)

    def get(self, request, id):
        user = request.user
        guides = Guide.objects.published()
        if user.is_authenticated and user.is_superuser:
            guides = Guide.objects.all()
        elif has_complete_profile(user):
            guides = guides | Guide.objects.filter(author=user)
        guide = get_object_or_404(guides, id=id)
        serializer = GuideSerializer(guide)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def _check_modify_permission(self, request, guide):
        if guide.author != request.user:
            return Response(
                {"detail": "Anda tidak memiliki izin untuk mengubah atau menghapus draf milik pengguna lain."},
                status=status.HTTP_403_FORBIDDEN
            )
        if guide.status != 'PENDING':
            return Response(
                {"detail": "Draf yang sudah disetujui atau ditolak tidak dapat diubah atau dihapus lagi."},
                status=status.HTTP_400_BAD_REQUEST
            )
        return None

    def put(self, request, id):
        guide = self.get_object(id)
        error_response = self._check_modify_permission(request, guide)
        if error_response:
            return error_response

        serializer = GuideSerializer(guide, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, id):
        guide = self.get_object(id)
        error_response = self._check_modify_permission(request, guide)
        if error_response:
            return error_response

        serializer = GuideSerializer(guide, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, id):
        guide = self.get_object(id)
        error_response = self._check_modify_permission(request, guide)
        if error_response:
            return error_response

        guide.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)