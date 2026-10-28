from django.urls import path
from .views import *

app_name = 'moderations'

urlpatterns = [
    # Jika mengakses /moderation/ saja, otomatis arahkan ke /moderation/Ringkasan/
    path('', ringkasan_moderation, name='ringkasan'),
    
    # Halaman Utama Moderasi Jurnal (Menangani list, filter tab, dan preview kanan)
    path('jurnal/', jurnal_moderation, name='jurnal_list'),
    
    # Endpoint Aksi (POST) untuk Setujui / Tolak / Hapus
    path('jurnal/<int:id>/review/', review_jurnal_action, name='jurnal_review'),
    path('jurnal/<int:id>/delete/', delete_jurnal_action, name='jurnal_delete'),
    
    # Halaman Utama Moderasi Laporan (Menangani list, filter, dan preview kanan)
    path('reports/', report_moderation, name='reports_list')
    
]