from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from listings.models import Listing
from listings.seed_data import AVAILABLE, CITIES, SAMPLE_USERNAME_PREFIX, SELLERS, SOLD
from profiles.models import Profile


class Command(BaseCommand):
    help = (
        "Mengisi data contoh: 5 akun penjual contoh, 50 listing tersedia (10 per kategori), dan 10 listing terjual. "
        "Aman dijalankan berulang: data yang sama diperbarui, bukan digandakan."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Hapus dulu semua listing milik akun contoh (berawalan sample_), lalu buat ulang. Listing pengguna asli tidak disentuh.",
        )

    @transaction.atomic   # kalau ada yang gagal di tengah jalan, semuanya dibatalkan, bukan setengah terisi
    def handle(self, *args, **options):
        sellers = self.create_sellers()

        if options["reset"]:
            deleted, _ = Listing.objects.filter(seller__in=sellers.values()).delete()
            self.stdout.write(f"Reset: {deleted} listing akun contoh dihapus.")

        created = 0
        updated = 0
        # enumerate memberi nomor urut (index), dipakai untuk menyebar tanggal dibuat supaya tidak semuanya sama
        for index, data in enumerate(AVAILABLE + SOLD):
            was_created = self.save_listing(sellers[data["seller"]], data, index)
            if was_created:
                created += 1
            else:
                updated += 1

        total_available = Listing.objects.filter(seller__in=sellers.values(), status=Listing.Status.AVAILABLE).count()
        total_sold = Listing.objects.filter(seller__in=sellers.values(), status=Listing.Status.SOLD).count()
        self.stdout.write(self.style.SUCCESS(
            f"Selesai: {created} listing baru, {updated} diperbarui. "
            f"Akun contoh sekarang punya {total_available} listing tersedia dan {total_sold} terjual."
        ))
        self.stdout.write("Akun contoh (sample_*) tidak punya kata sandi, jadi tidak bisa dipakai login.")

    def create_sellers(self):
        # Kembalikan dictionary: kunci penjual -> objek User
        sellers = {}
        for key, (display_name, bio) in SELLERS.items():
            user, _ = User.objects.get_or_create(username=SAMPLE_USERNAME_PREFIX + key)

            # Akun contoh tidak boleh bisa login: tidak ada kata sandi yang bisa ditebak
            user.set_unusable_password()
            user.is_staff = False
            user.is_superuser = False
            user.save()

            # Kontak memakai example.com, domain yang memang dicadangkan untuk contoh. Bukan data pribadi siapa pun.
            Profile.objects.update_or_create(
                user=user,
                defaults={
                    "display_name": display_name,
                    "bio": bio,
                    "contact_type": "email",
                    "contact_value": f"{key}@example.com",
                },
            )
            sellers[key] = user
        return sellers

    def save_listing(self, seller, data, index):
        city_label, latitude, longitude = CITIES[data["city"]]

        # Listing dikenali dari penjual + judulnya, jadi menjalankan perintah ini lagi tidak membuat data ganda
        listing, was_created = Listing.objects.update_or_create(
            seller=seller,
            title=data["title"],
            defaults={
                "description": data["description"],
                "category": data["category"],
                "brand": data["brand"],
                "size": data["size"],
                "condition": data["condition"],
                "price": data["price"],
                "image_url": data["image_url"],
                "city": city_label,
                "latitude": Decimal(latitude),
                "longitude": Decimal(longitude),
                "is_repairable": data["is_repairable"],
                "is_upcycled": data["is_upcycled"],
                "is_locally_available": data["is_locally_available"],
                "extends_clothing_life": data["extends_clothing_life"],
                "status": Listing.Status.SOLD if data["sold_days_ago"] is not None else Listing.Status.AVAILABLE,
            },
        )

        # Tanggal dibuat disebar ke belakang (0 sampai 28 hari lalu) supaya katalog tidak terlihat seragam.
        # Tanggal terjual dibuat sesuai sold_days_ago. Keduanya lewat update() karena auto_now_add / save() mengisinya sendiri.
        created_at = timezone.now() - timedelta(days=(index * 7) % 29, hours=(index * 5) % 24)
        fields = {"created_at": created_at}
        if data["sold_days_ago"] is not None:
            fields["sold_at"] = timezone.now() - timedelta(days=data["sold_days_ago"])
        Listing.objects.filter(pk=listing.pk).update(**fields)

        return was_created
