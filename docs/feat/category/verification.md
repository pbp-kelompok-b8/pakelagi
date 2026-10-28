# Halaman Kategori dan verifikasi katalog

## Implementasi baru

- Route publik `main:category_index` di `/categories/`, hanya menerima GET.
- View `main.views.category_index` memakai `Listing.Category.choices` sebagai
  sumber kategori dan urutan. Tidak ada model, aplikasi, atau migration baru.
- Count seluruh listing Available dihitung dalam satu query agregasi kategori.
  Sold/Hidden tidak dihitung. Kategori tanpa barang tetap tampil dengan 0 item.
- Setiap kartu membuka katalog existing dengan query kategori yang di-encode;
  Modest Wear round-trip dengan benar. Filter kunjungan sebelumnya tidak dibawa.
- Breadcrumb, pengantar, lima kartu artwork 4:5, dan tautan seluruh katalog
  memakai `base.html`, font, serta token warna proyek.
- Grid lima kolom pada layar lebar, tiga pada tablet, dua pada mobile, dan satu
  pada layar sangat sempit. Caption ditumpuk pada mobile. Kartu merupakan link
  HTML native yang dapat difokuskan dan dibuka menggunakan Enter.
- Menu Kategori desktop/mobile dan link footer menuju `/categories/`.
  Header menandai menu Kategori aktif hanya pada halaman tersebut.

## Existing yang dipertahankan

Tab kategori, parser URL, fallback HTML, dan partial HTMX katalog sudah tersedia
pada baseline `dev` (`8d76bdf`). Implementasi ini tidak mengklaimnya sebagai kode
baru, tidak membangun ulang filter, dan tidak mengubah CRUD Listing.

`listings/test_categories.py` tetap menguji kategori resmi, Semua dan kategori
tidak dikenal, tab aktif, Sold/Hidden, preservasi filter, reset pagination,
encoding Modest Wear, history restore, Vary, dan empty state.

`templates/index.html` tidak diubah. Baseline beranda masih berisi hero dan
section janji, belum memiliki section kategori bergambar. Integrasi section
Home tetap perlu dikoordinasikan dengan pemilik beranda, bukan prasyarat
halaman Kategori mandiri ini.

Favorites tetap pada branch terpisah, tidak ikut dibawa ke `feat/category`.

## Desain dan sumber artwork

Spesifikasi merujuk Figma `dCekkdFnlpwdcTY6vaXyrX`, node desktop `223:963` dan
mobile `223:964`. Akses Figma dari lingkungan implementasi mendapat HTTP 403;
karena itu struktur dan layout mengikuti spesifikasi tertulis, bukan hasil
pembacaan/export node Figma. Pemeriksaan visual persis terhadap Figma masih
perlu dilakukan ketika akses tersedia.

Kelima SVG dalam `static/images/categories/` adalah ilustrasi lokal orisinal
untuk proyek ini, bukan aset unduhan Figma atau foto pihak ketiga. Gambar
dekoratif memakai alt kosong karena kategori sudah menjadi label link. Tidak
ada URL aset sementara MCP atau dependency gambar eksternal pada runtime.

## Verifikasi otomatis

```bash
python manage.py test main.test_categories
python manage.py test listings.test_categories listings.test_filters listings.test_catalog
python manage.py test
python manage.py makemigrations --check --dry-run
```

Hasil pada branch Category:

- Baseline katalog awal: 68 test lulus.
- Baseline setelah test regresi kategori pertama: 73 test lulus.
- Halaman baru dan regression katalog: 87 test lulus.
- Suite Django penuh: 396 test lulus. Angka ini tidak mencakup aplikasi Favorites
  yang sengaja berada di branch terpisah.
- Tidak ada perubahan model tanpa migration; tidak diperlukan migration baru.

Test navigasi lama pada `listings.test_manage` diperbarui dari ekspektasi anchor
`/listings/#kategori` ke halaman baru. Anchor dan tab di katalog tetap ada.
Warning direktori `staticfiles/` yang belum dibuat juga ada pada baseline.

## Verifikasi browser opsional

```bash
python -m pip install playwright
python -m playwright install chromium
python manage.py test main.category_browser_checks
```

Playwright adalah alat test opsional, bukan dependency runtime. Suite memakai
database test dan server lokal sementara; HTMX resmi diambil dari CDN pada
setup. Override keamanan async Django hanya aktif selama kelas browser test
untuk penggunaan API sync Playwright, bukan pada aplikasi produksi.

Empat skenario Chromium lulus:

1. Navbar desktop → halaman Kategori → setiap kartu → katalog yang benar,
   termasuk count di atas satu halaman pagination, kategori kosong,
   Back/Forward/refresh, serta link seluruh katalog.
2. Grid pada lebar 1440/768/390/320, rasio gambar 4:5, tidak ada overflow
   horizontal, menu mobile, fokus keyboard, dan Enter pada Modest Wear.
3. Semua kartu dan link seluruh katalog berfungsi tanpa JavaScript.
4. Count berubah setelah status listing diperbarui; filter ukuran serta tab
   HTMX katalog tetap berfungsi setelah navigasi dari halaman Kategori.

Screenshot desktop/mobile ditinjau dari folder sementara di luar repository.
Untuk menghasilkan screenshot sendiri, set `PAKELAGI_BROWSER_SCREENSHOTS` ke
folder di luar repository sebelum menjalankan suite browser. Tidak ada database,
screenshot, file environment, atau hasil coverage yang dimasukkan ke commit.

Pemeriksaan ini bukan audit aksesibilitas menyeluruh, pengujian lintas browser,
atau bukti kesamaan pixel dengan Figma yang belum dapat diakses.
