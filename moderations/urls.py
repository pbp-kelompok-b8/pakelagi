from django.urls import path
from .views import ringkasan_moderation, jurnal_moderation, review_jurnal_action, delete_jurnal_action, get_publish_modal, publish_jurnal_action, toggle_publish_action
app_name = 'moderations'

urlpatterns = [
    # Jika mengakses /moderation/ saja, otomatis arahkan ke /moderation/Ringkasan/
    path('', ringkasan_moderation, name='ringkasan'),
    
    # Halaman Utama Moderasi Jurnal (Menangani list, filter tab, dan preview kanan)
    path('guides/', jurnal_moderation, name='jurnal_list'),
    
    # Endpoint Aksi (POST) untuk Setujui / Tolak / Hapus
    path('jurnal/<int:id>/review/', review_jurnal_action, name='jurnal_review'),
    path('jurnal/<int:id>/delete/', delete_jurnal_action, name='jurnal_delete'),
    
    # Halaman Utama Moderasi Laporan (Menangani list, filter, dan preview kanan)
    path('reports/', report_moderation, name='reports_list')
    
    # Endpoint Aksi (POST) untuk Setujui / Tolak / Hapus / Publish
    path('guides/<int:id>/review/', review_jurnal_action, name='jurnal_review'),
    path('guides/<int:id>/delete/', delete_jurnal_action, name='jurnal_delete'),
    path('guides/<int:id>/publish-modal/', get_publish_modal, name='publish_modal'),
    path('guides/<int:id>/publish/', publish_jurnal_action, name='jurnal_publish'),
    path('guides/<int:id>/toggle-publish/', toggle_publish_action, name='jurnal_toggle_publish'),
]