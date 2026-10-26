from django.db import models
from django.contrib.auth.models import User
from django.db.models import CheckConstraint, Q, F
from listings.models import Listing
import uuid
# Create your models here.

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
        - Jika reporter atau listing dihapus, laporan ikut terhapus
          (CASCADE).

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
        ('counterfeit','Counterfeit'),
        ('misleading','Misleading'),
        ('offensive','Offensive'),
        ('prohibited_item','Prohibited Item'),
        ('other','Other'),
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
        Listing, related_name='reports', on_delete=models.CASCADE, blank=False, null=False
    )
    reason = models.CharField(max_length=20, choices=REASONS)
    description = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS, default='open')
    moderator_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    
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
    
    
