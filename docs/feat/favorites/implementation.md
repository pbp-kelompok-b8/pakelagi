# Favorites

## Scope dan branch

- `feat/category`: test regresi untuk perilaku kategori katalog yang sudah ada.
- `feat/favorites`: aplikasi Favorites dan integrasinya, dimulai dari `dev`
  (`8d76bdf`), bukan dari `feat/category`.
- Tidak ada perubahan pencarian, aturan harga/ukuran/kota, pagination umum,
  CRUD listing, atau integrasi lokasi.
- Branch dan PR tetap terpisah. Implementasi ini belum di-push atau dibuatkan PR;
  tidak ada merge otomatis ke `dev`.

## Aturan domain

Mengikuti `CONTEXT.md` dan kebijakan `profiles.access.member_required`:

- Member harus login dan memiliki nama tampilan profil yang tidak kosong.
- Favorit dan catatan hanya dapat dibaca/diubah pemiliknya.
- Hanya listing Available milik orang lain yang dapat ditambahkan.
- Sold tetap tersimpan, tampil dengan label Terjual, dan dapat dihapus atau
  diperbarui catatannya. Tidak dapat ditambahkan sebagai favorit baru.
- Hidden tidak tampil, tidak dihitung, dan tidak dapat dibuka melalui editor
  catatan, termasuk pada partial HTMX. Favoritnya tetap tersimpan di database;
  endpoint remove tetap dapat membersihkannya tanpa mengekspos detail listing.
- Kombinasi user/listing unik di database. Add dan remove bersifat idempoten.
- Catatan opsional, maksimal 1.000 karakter, selalu di-escape oleh template.
- Penghapusan akun atau listing menghapus Favorite terkait melalui CASCADE.
- Favorit bukan pesanan, reservasi, atau konfirmasi transaksi.

## Endpoint

| Method | URL | Fungsi |
| --- | --- | --- |
| GET | `/favorites/` | Daftar privat dan filter `?category=`. |
| POST | `/favorites/listings/<listing_id>/add/` | Menyimpan listing yang memenuhi aturan. |
| POST | `/favorites/listings/<listing_id>/remove/` | Menghapus favorit milik pengguna aktif. |
| GET/POST | `/favorites/<favorite_id>/edit/` | Membaca/mengubah catatan pribadi. |

Semua mutasi memerlukan CSRF. User dan listing tidak dapat diganti lewat form
catatan. Parameter `next` divalidasi menggunakan helper proyek untuk mencegah
open redirect. Setelah login/onboarding dari POST, pengguna diarahkan kembali ke
halaman GET, bukan ke endpoint mutasi.

## Integrasi HTML dan HTMX

- Katalog, detail listing, dan etalase memakai komponen tombol hati yang sama.
- Form GET katalog hanya membungkus sidebar. Pencarian, kategori aktif, dan
  pengurutan dihubungkan melalui atribut HTML `form`; pengurutan HTMX juga
  menyertakan `#catalog-filters`. Kartu dan form POST berada di luar form GET.
- Status favorit disiapkan lewat anotasi `Exists`, tanpa query per kartu.
  Guest tidak menjalankan query Favorite.
- POST tombol mengganti komponen tombol saja dan tidak mengubah URL kategori.
  Event `favoriteChanged` memperbarui kontrol lain untuk listing yang sama.
- Tombol request dinonaktifkan sementara. Status hati tidak berubah secara
  optimistis; kegagalan menampilkan pesan retry/refresh. Add/remove eksplisit
  memungkinkan retry tanpa membalik keadaan secara tidak sengaja.
- Kategori favorit mengganti hasil dan memperbarui URL. Remove memperbarui
  daftar, jumlah, serta empty state; kategori terpilih tetap dipertahankan.
- Editor catatan dapat tampil inline. ID field dibedakan untuk setiap favorit.
- Request biasa tetap menghasilkan halaman/redirect HTML. History restore
  menghasilkan halaman lengkap. Sesi HTMX yang habis memakai `HX-Redirect`
  untuk navigasi login/onboarding penuh, bukan menyisipkan halaman login.
- Respons personal memakai `Cache-Control: private, no-store` dan `Vary: Cookie`;
  respons yang bervariasi menurut HTMX juga memuat kedua header HTMX pada Vary.
  Halaman personal tidak disimpan dalam snapshot history HTMX.
- Link Favorit pada header desktop/mobile dan footer menuju route yang nyata.

## Setup dan verifikasi

Gunakan Python dari virtual environment proyek:

```bash
python manage.py migrate
python manage.py test favorites
python manage.py test listings.test_filters listings.test_catalog
python manage.py test
python manage.py makemigrations --check --dry-run
```

Migration baru hanya `favorites/migrations/0001_initial.py`. Migration aplikasi
lain tidak diubah. Migration sudah diterapkan pada database pengembangan lokal;
database dan hasil screenshot tidak dimasukkan ke commit.

### Browser opsional

Pemeriksaan Chromium terpisah dari discovery test Django biasa agar Playwright
tidak menjadi dependency runtime:

```bash
python -m pip install playwright
python -m playwright install chromium
python manage.py test favorites.browser_checks
```

Suite ini memakai database test dan server lokal sementara. Library HTMX resmi
diambil dari CDN saat setup; diperlukan koneksi jaringan. Override keamanan
async Django hanya berlaku selama kelas test karena API sync Playwright
menjalankan event loop pada thread test, bukan pada aplikasi produksi.

Untuk menyimpan screenshot, set environment variable
`PAKELAGI_BROWSER_SCREENSHOTS` ke folder di luar repository. Tidak perlu
memasukkan paket browser ke `requirements.txt` runtime.

## Hasil verifikasi

- Baseline katalog sebelum perubahan: 68 test lulus.
- Branch Category: 73 test katalog/kategori lulus.
- Test kategori dari branch Category juga dijalankan ulang pada implementasi
  Favorites: 5 test lulus tanpa memasukkan commit Category ke branch ini.
- Favorites: 49 test lulus, mencakup constraint, permission, CSRF, privasi antar
  akun, Hidden, Sold, semua kategori, validasi/escaping catatan, partial,
  redirect, cache, struktur form, dan jumlah query.
- Browser Chromium: 6 skenario lulus. Mencakup filter dan sort setelah form
  dipisah, Back/Forward/refresh, URL tombol hati, editor inline, penghapusan
  terakhir, mobile 390px tanpa overflow horizontal, Enter pada tombol,
  fallback tanpa JavaScript, sesi habis, kegagalan jaringan/retry, kontrol
  ganda, serta penghapusan favorit Sold.
- Suite Django penuh: 426 test lulus.
- `makemigrations --check --dry-run`: tidak ada perubahan model tanpa migration.

Pemeriksaan ini bukan audit aksesibilitas menyeluruh atau pengujian lintas
browser. Warning direktori `staticfiles/` yang belum dibuat juga muncul pada
baseline test; bukan kegagalan Favorites.

## Sebelum PR

Tinjau perubahan bersama pemilik katalog dan etalase, terutama batas form serta
pemakaian kartu bersama. Terapkan urutan integrasi tim tanpa membawa commit
Category ke PR Favorites secara tidak sengaja. Periksa ulang `git diff` dan
status migration pada lingkungan deployment sebelum rilis.
