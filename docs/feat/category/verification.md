# Verifikasi kategori katalog

Tab kategori, parser URL, fallback HTML, dan partial HTMX sudah tersedia pada
baseline `dev` (`8d76bdf`). Branch ini menambahkan cakupan regresi, bukan mengklaim
implementasi katalog existing sebagai fitur baru.

`listings/test_categories.py` mencakup setiap pilihan resmi kategori, Semua dan
kategori tidak dikenal, tab aktif pada halaman penuh/partial, pengecualian
Sold/Hidden, preservasi seluruh filter lain, reset pagination pada link kategori,
encoding Modest Wear, history restore, Vary, dan empty state.

Verifikasi otomatis:

```bash
python manage.py test listings.test_categories listings.test_filters listings.test_catalog
```

Hasil saat implementasi: 73 test lulus. Baseline sebelum penambahan: 68 test lulus.
Tidak ada perubahan aplikasi Favorites pada branch ini.

## Pemeriksaan browser yang masih diperlukan

- Klik kategori dengan filter lain, lalu refresh dan Back/Forward.
- Ulangi tanpa JavaScript.
- Periksa keyboard, fokus, tab aktif, dan layout layar kecil.

Test Django tidak menggantikan pemeriksaan interaksi browser ini.
