from django.db import models
from django.conf import settings
from django.utils import timezone
from profiles.validators import validate_external_https_url
# Create your models here.

class Guide(models.Model):
    # Pilihan Status
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('DISETUJUI', 'Disetujui'),
        ('DITOLAK', 'Ditolak'),
    )
    
    # Pilihan Kategori
    CATEGORY_CHOICES = (
        ('PERAWATAN', 'Perawatan'),
        ('PERBAIKAN', 'Perbaikan'),
        ('REUSE', 'Reuse'),
        ('SLOW_FASHION', 'Slow Fashion'),
        ('CONSCIOUS_SHOPPING', 'Conscious Shopping'),
    )
    # Untuk relasi dengan User Author
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='guides')
    # Bagian Content yang akan ditampilkan
    title = models.CharField("Judul", max_length=255)
    ringkasan = models.CharField("Ringkasan", max_length=300, help_text="ringkasan mengenai guides yang kamu buat")
    image_url = models.URLField("Url Thumbnail (Opsional)", max_length=2048, blank=True, validators=[validate_external_https_url])
    konten = models.TextField("Isi Guides", help_text="mengimplementasikan Markdown file")
    category = models.CharField("Kategori", max_length=25, choices=CATEGORY_CHOICES, default='PERAWATAN')
    # Bagian sistem, status, etc
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='PENDING')
    is_published = models.BooleanField(default=False)
    rejected_notes = models.TextField("Catatan Penolakan", blank=True, null=True)
    #Penanggalan
    date_submitted = models.DateTimeField(auto_now_add=True)
    date_published = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        db_table = "sustainable_guide"
        ordering = ['-date_submitted'] # Urutkan dari yang paling baru dikirim
        
    def __str__(self):
        return f"{self.title} - {self.get_status_display()}"
    
    #secara otomatis menghitung reading time
    @property
    def reading_time(self):
        word_count = len(self.konten.split())
        minutes = round(word_count/200)
        return max(1, minutes) #setidaknya ada 1 menit waktu membaca
    
    @property
    def author_name(self):
        # Jika penulisnya adalah admin, otomatis namanya "Tim Pakelagi"
        if self.author.is_superuser:
            return "Tim Pakelagi"
        
        # Jika member biasa
        if hasattr(self.author, 'profile') and self.author.profile.display_name:
            return self.author.profile.display_name
            
        # Kontigensi jika display_name kosong
        return self.author.username
    
    #untuk ubah status ketika disetujui
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)