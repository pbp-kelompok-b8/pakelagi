from django.db import models
from django.contrib.auth.models import User
from django.db.models import CheckConstraint, Q, F
from django.core.exceptions import ValidationError
from django.core.validators import MinLengthValidator
from listings.models import Listing
import uuid
# Create your models here.

ACTIVE_STATUS = ("open", "reviewing")

class Report(models.Model):
    """
    Laporan pelanggaran yang diajukan user terhadap sebuah listing.

    Alur status: ``open`` -> ``reviewing`` -> ``resolved`` / ``rejected``.
    Moderator memproses laporan dan dapat meninggalkan catatan internal
    pada ``moderator_note``.

    Aturan bisnis:
        - Satu user hanya boleh memiliki satu laporan *aktif* (status
          ``open`` atau ``reviewing``) per listing. Setelah laporan
          selesai, user boleh melapor lagi.
        - Jika reporter dihapus, laporannya ikut terhapus (CASCADE).
        - Jika listing dihapus, laporan tetap ada sebagai jejak moderasi.
        Relasi ``listing`` menjadi NULL (SET_NULL), dan nama listing tetap
        terbaca lewat ``listing_title``, salinan judul yang diambil saat
        laporan dibuat.

    Attributes:
        id (UUID): Primary key acak, tidak bisa diedit.
        reporter (User): User yang mengajukan laporan.
        listing (Listing): Listing yang dilaporkan.
        reason (str): Kategori pelanggaran, salah satu dari ``REASONS``.
        description (str): Penjelasan detail dari reporter.
        status (str): Status penanganan, salah satu dari ``STATUS``.
            Default ``open``.
        moderator_note (str): Catatan moderator. Boleh kosong.
        created_at (datetime): Waktu laporan dibuat (otomatis).
        updated_at (datetime | None): Waktu terakhir laporan diperbarui.
            ``None`` jika belum pernah diperbarui.

    Example:
        >>> Report.objects.create(
        ...     reporter=user,
        ...     listing=listing,
        ...     reason="counterfeit",
        ...     description="Barang ini replika, bukan original.",
        ... )
    """

    REASONS = [
        ('Counterfeit','Counterfeit'),
        ('Misleading','Misleading'),
        ('Offensive','Offensive'),
        ('Prohibited Item','Prohibited Item'),
        ('Other','Other')
    ]
    STATUS = [
        ('open','Open'),
        ('reviewing','Reviewing'),
        ('resolved','Resolved'),
        ('rejected','Rejected'),
    ]
        
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reporter = models.ForeignKey(
        User, related_name='submitted_reports', on_delete=models.CASCADE ,null=False, blank=False
    )
    listing = models.ForeignKey(
        Listing, related_name='reports', on_delete=models.SET_NULL, blank=True, null=True
    )
    listing_title = models.CharField("Judul listing", max_length=120, blank=True, editable=False)
    reason = models.CharField(max_length=20, choices=REASONS)
    description = models.TextField(blank=False, null=False, validators=[MinLengthValidator(10)])
    status = models.CharField(max_length=10, choices=STATUS, default='open')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(blank=True, null=True, auto_now=True)
    
    class Meta:
        ordering = ["-created_at"]
        constraints = [
            CheckConstraint(
                condition=Q(updated_at__isnull=True) | Q(updated_at__gte=F("created_at")),
                name="check_date_range",
            ),
            models.UniqueConstraint(
                fields=["reporter", "listing"],
                condition=Q(status__in=["open", "reviewing"]),
                name="unique_active_report_per_reporter_listing",
            ),
        ]
        
    def __str__(self):
        return f"Report #{self.pk}: {self.listing_title} ({self.status})"

    def clean(self):
        super().clean()
        if self.reporter_id is None:
            return

        # Aturan pembuatan: hanya saat report baru. Setelah itu listing boleh saja disembunyikan
        # (bahkan lewat report ini sendiri) tanpa membuat pelapor tidak bisa menyunting teksnya.
        if self._state.adding:
            if self.listing_id is None:
                raise ValidationError("Listing yang dilaporkan tidak ditemukan.")
            if self.listing.seller_id == self.reporter_id:
                raise ValidationError("Kamu tidak bisa melaporkan listing milikmu sendiri.")
            if self.listing.status == Listing.Status.HIDDEN:
                raise ValidationError("Listing ini sudah tidak tampil di katalog.")

        
        if self.listing_id and self.status in ACTIVE_STATUS:
            duplicate = Report.objects.filter(
                reporter_id=self.reporter_id, listing_id=self.listing_id, status__in=self.STATUS,
            ).exclude(pk=self.pk)
            if duplicate.exists():
                raise ValidationError("Kamu sudah melaporkan listing ini dan laporannya masih diproses.")


    def save(self, *args, **kwargs):
        if self.listing_id and not self.listing_title:
            self.listing_title = self.listing.title[:120]
        super().save(*args, **kwargs)

    @property
    def is_editable(self):
        return self.status == "open"
    
class ReportModeratorNote(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    moderator_id = models.ForeignKey(
        User, related_name='moderator_id', on_delete=models.CASCADE ,null=False, blank=False
    )
    report_id = models.ForeignKey(
        Report, related_name='report_id', on_delete=models.CASCADE, blank=False, null=False
    )
    note = models.TextField(blank=False, null=False, validators=[MinLengthValidator(10)])
    created_at = models.DateTimeField(auto_now_add=True)
    
