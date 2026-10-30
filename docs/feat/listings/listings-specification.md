# Pakelagi - Spesifikasi Fitur Clothing Listings

| Metadata | Nilai |
|---|---|
| Modul | Modul 1 - Clothing Listings |
| Penanggung jawab | Anggota 1 - Nugraha Kautsarrizqi Caksana |
| Model utama | `Listing` |
| Django app | `listings` (model, form, view, template, test, dan perintah seed milik modul ini) |
| Acuan | `docs/pakelagi-specification.md` dan bagian "Modul 1" di `README.md` |

> Dokumen ini menjelaskan apa yang sudah dibangun pada modul Clothing Listings. Jika ada pertentangan dengan spesifikasi induk, spesifikasi induk yang berlaku.

---

## 1. Tujuan

Clothing Listings adalah inti Pakelagi: katalog pakaian preloved tempat penjual memasang barangnya dan pembeli mencarinya. Transaksi berlangsung di luar Pakelagi, jadi aplikasi hanya mempertemukan pembeli dengan penjual. Kondisi barang dijelaskan dengan skala empat tingkat, lokasi hanya berupa kota atau area umum, dan penjual dihubungi langsung lewat kontak profilnya.

---

## 2. Aktor dan hak akses

| Aktor | Boleh | Tidak boleh |
|---|---|---|
| Tamu (belum login) | Melihat katalog dan detail listing yang berstatus `Available` atau `Sold` | Melihat kontak penjual, membuat atau mengubah listing |
| Member (sudah login, profil lengkap) | Membuat listing, mengubah dan menghapus listing miliknya, menandai `Sold` atau `Available`, melihat kontak penjual, memakai saran lokasi | Mengubah listing orang lain |
| Pemilik listing | Semua hak member pada listing miliknya, termasuk melihat listing `Hidden` miliknya | Mengubah status listing yang disembunyikan moderator |
| Admin | Mengubah atau menghapus listing mana pun, menyembunyikan listing lewat halaman admin Django | - |

Listing berstatus `Hidden` (hasil moderasi) tidak muncul di katalog dan menghasilkan 404 bagi tamu maupun member lain. Hanya pemilik dan admin yang masih bisa melihatnya.

---

## 3. Model `Listing`

| Field | Tipe | Keterangan |
|---|---|---|
| `seller` | ForeignKey ke User | Selalu diisi dari akun yang login, bukan dari input form |
| `title` | CharField (120) | Minimal 5 karakter |
| `description` | TextField | Wajib |
| `category` | CharField (pilihan) | Top, Bottom, Dress, Outerwear, Modest Wear |
| `brand` | CharField (80) | Opsional |
| `size` | CharField (pilihan) | XS, S, M, L, XL, XXL, Free Size |
| `condition` | CharField (pilihan) | Like New, Good, Fair, Needs Repair |
| `price` | PositiveIntegerField | 0 sampai Rp 100.000.000 (batas menjaga nilai muat di integer 32-bit PostgreSQL) |
| `image_url` | URLField (2048) | Satu tautan http atau https, bukan unggahan |
| `city` | CharField (100) | Kota atau area umum, ditolak jika berisi pola alamat rumah |
| `latitude`, `longitude` | Decimal, opsional | Dibulatkan sekitar 1 km, hanya terisi jika penjual memilih saran lokasi |
| `is_repairable`, `is_upcycled`, `is_locally_available`, `extends_clothing_life` | Boolean | Tag keberlanjutan: fakta yang dipilih penjual, bukan klaim dampak lingkungan |
| `status` | CharField (pilihan) | `Available` (default), `Sold`, `Hidden` |
| `sold_at` | DateTimeField, opsional | Dicatat otomatis hanya saat status berpindah ke `Sold` |
| `created_at`, `updated_at` | DateTimeField | Otomatis |

Aturan data:
- Urutan bawaan: terbaru lebih dulu, `id` sebagai pembeda.
- Indeks `(status, -created_at)` karena katalog selalu menyaring `Available` lalu mengurutkan dari yang terbaru.
- `save()` mengisi `sold_at` hanya sekali, saat transisi ke `Sold`, bukan setiap kali listing diedit.

---

## 4. Fitur

### 4.1 Katalog publik (`/listings/`)
- Hanya listing `Available` yang tampil.
- Pencarian kata kunci pada judul atau brand (maksimal 5 kata, setiap kata harus cocok).
- Filter: kategori (tab), ukuran, kondisi, rentang harga (termasuk tombol cepat), kota, dan tag keberlanjutan.
- Pengurutan: terbaru, harga terendah, harga tertinggi.
- Pagination 12 listing per halaman, dengan tautan yang selalu membawa pencarian dan filter aktif.
- Chip filter aktif yang bisa diklik untuk menghapus satu filter.
- Semua nilai dari URL dibersihkan: nilai yang tidak dikenal dibuang, angka dibatasi, dan hasilnya tidak pernah error 500.

### 4.2 Detail listing (`/listings/<id>/`)
- Foto, harga, ukuran, kondisi, tag keberlanjutan, kota, dan deskripsi.
- Profil singkat penjual dan "lainnya dari penjual ini" (maksimal 4).
- Kontak penjual hanya tampil untuk member yang login, dan hanya pada barang yang masih `Available` milik orang lain.
- Jika gambar gagal dimuat, tampil placeholder lokal.

### 4.3 Membuat dan mengubah listing (`/listings/create/`, `/listings/<id>/edit/`)
- Form tujuh bagian: foto, tentang pakaian, kondisi, harga, lokasi, tag keberlanjutan, deskripsi.
- Kategori, ukuran, dan kondisi tampil sebagai chip atau kartu, bukan dropdown.
- Setelah berhasil, pengguna diarahkan ke halaman detail dengan pesan sukses.

### 4.4 Menghapus listing (`/listings/<id>/delete/`)
GET menampilkan halaman konfirmasi, POST menghapus. Pemilik atau admin yang boleh menghapus.

### 4.5 Mengubah status (`/listings/<id>/status/`)
Hanya lewat POST. Pemilik menandai listing `Sold` atau `Available` lagi. Listing yang disembunyikan moderator tidak bisa diubah statusnya oleh pemilik.

### 4.6 Listing saya (`/listings/mine/`)
Daftar listing milik sendiri dengan tab Semua, Tersedia, Terjual, dan Disembunyikan beserta jumlahnya, 6 listing per halaman.

### 4.7 Saran lokasi (Nominatim)
Saat penjual mengetik di kolom kota, HTMX memanggil `/listings/location-search/` setelah berhenti mengetik 500 ms. Server meminta ke Nominatim dan menampilkan maksimal 6 saran dengan nama kota, kecamatan, dan provinsi. Memilih saran mengisi kota dan koordinat. Jika layanan gagal, penjual tetap bisa mengetik kotanya sendiri. Rinciannya ada di bagian 6.

### 4.8 Etalase profil
Modul Profil menampilkan listing `Available` dan `Sold` milik pengguna lewat `listings/storefront.py` dan memakai kartu listing yang sama dengan katalog. Listing `Hidden` tidak pernah ditampilkan.

### 4.9 Moderasi lewat admin Django
`ListingAdmin` menyediakan daftar, filter, pencarian, dan aksi "Sembunyikan listing terpilih (moderasi)" yang mengubah status menjadi `Hidden`. Field `sold_at`, `created_at`, dan `updated_at` hanya bisa dibaca.

---

## 5. URL

| URL | Nama | Metode | Akses |
|---|---|---|---|
| `/listings/` | `listings:list` | GET | Publik |
| `/listings/<id>/` | `listings:detail` | GET | Publik (Hidden: pemilik dan admin) |
| `/listings/create/` | `listings:create` | GET, POST | Member |
| `/listings/<id>/edit/` | `listings:edit` | GET, POST | Pemilik atau admin |
| `/listings/<id>/delete/` | `listings:delete` | GET, POST | Pemilik atau admin |
| `/listings/<id>/status/` | `listings:status` | POST | Pemilik |
| `/listings/mine/` | `listings:mine` | GET | Member |
| `/listings/location-search/` | `listings:location_search` | GET | Member dengan profil lengkap |

---

## 6. Integrasi API publik: Nominatim

| Item | Penerapan |
|---|---|
| Layanan | Nominatim (OpenStreetMap) Search API, `format=jsonv2`, `countrycodes=id` |
| Pemanggil | Server Django (`listings/nominatim.py`), bukan JavaScript di browser |
| Batas kecepatan | Maksimal 1 request per detik (`cache.add` sebagai penjaga) |
| Cache | Hasil disimpan agar query yang sama tidak dikirim ulang |
| Cooldown | Jika Nominatim membalas 403 atau 429, request dihentikan sementara |
| Panjang query | Minimal 3 karakter bukan spasi, maksimal 100 |
| Hasil | Maksimal 6 saran, hanya jenis tempat yang relevan (kota, kecamatan, kelurahan, dan sejenisnya), hanya di dalam wilayah Indonesia |
| Privasi | Koordinat dibulatkan 0,01 derajat (sekitar 1 km) |
| Kegagalan | Status `OK`, `SHORT`, `THROTTLED`, atau `UNAVAILABLE`; penjual tetap bisa mengisi kota manual |
| Atribusi | "OpenStreetMap contributors" di form dan footer |

Dalam test, respons Nominatim di-mock sehingga test tidak memerlukan internet.

---

## 7. Interaktivitas (HTMX dan JavaScript)

- **Katalog:** pencarian, filter, pengurutan, dan pagination mengganti hanya bagian hasil lewat `hx-get` dan `hx-target`, dengan `hx-push-url` agar URL tetap bisa dibagikan.
- **Respons parsial:** view memeriksa header `HX-Request`. Jumlah pakaian dikirim ulang sebagai `hx-swap-oob`. Saat tombol back (`HX-History-Restore-Request`) dikirim halaman penuh.
- **Form listing:** saran lokasi lewat HTMX, lalu JavaScript kecil mengisi kota dan koordinat saat saran diklik (event delegation) dan membuang koordinat lama jika kota diketik ulang manual.
- **Header responsif:** menu mobile dan tautan akun dibuat dengan fungsi bernama dan pendengar yang dipasang sekali, karena HTMX menjalankan ulang `<script>` saat riwayat dipulihkan.
- Token CSRF untuk request HTMX diatur global di `base.html`.

---

## 8. Form dan validasi

`ListingForm` adalah `ModelForm` dengan daftar field eksplisit. `seller`, `status`, dan `sold_at` sengaja tidak ada di form.

| Aturan | Tempat |
|---|---|
| Judul 5 sampai 120 karakter | Model |
| Harga 0 sampai Rp 100.000.000 | Model (validator) |
| URL gambar hanya http atau https | `validate_http_url` |
| Kota tidak boleh berisi pola alamat rumah (Jl., Gang, No., RT, RW) | `validate_no_home_address` (regex dengan batas kata, sehingga "Jalancagak" dan "Nobel" tetap diterima) |
| Koordinat harus angka terbatas, berada di Indonesia, lalu dibulatkan | `clean()` di form |
| Koordinat dibuang diam-diam jika tidak valid atau kota diubah manual | `clean()` di form |

---

## 9. Struktur berkas

| Berkas | Isi |
|---|---|
| `listings/models.py` | Model `Listing` |
| `listings/forms.py` | `ListingForm` |
| `listings/views.py` | Semua view dan pagination |
| `listings/filters.py` | Pencarian, filter, pengurutan, dan penyusunan URL |
| `listings/nominatim.py` | Klien Nominatim |
| `listings/validators.py` | Validator URL dan alamat rumah |
| `listings/storefront.py` | Data etalase untuk modul Profil |
| `listings/admin.py` | Moderasi lewat admin Django |
| `listings/templatetags/listing_extras.py` | Filter `rupiah` |
| `listings/seed_data.py`, `management/commands/seed_listings.py` | Data contoh |
| `templates/listings/` | `list`, `detail`, `form`, `mine`, `confirm_delete`, dan komponen (`results`, `filters`, `count`, `listing_card`, `field`, `location_results`) |
| `static/css/listings.css` | Gaya khusus modul, melengkapi Tailwind |

---

## 10. Keamanan dan privasi

- **Otorisasi:** `@member_required` pada halaman yang mengubah data. Pemeriksaan kepemilikan memakai 404 (bukan 403) agar orang luar tidak bisa menebak listing mana yang ada.
- **Metode HTTP:** aksi yang mengubah data hanya menerima POST (`@require_POST`), halaman baca hanya GET (`@require_GET`).
- **CSRF:** middleware Django, `{% csrf_token %}` di setiap form, dan header global untuk HTMX.
- **XSS:** autoescape Django, tanpa `|safe` pada data pengguna. URL gambar dibatasi ke http dan https.
- **Mass assignment:** daftar field form eksplisit.
- **Privasi kontak:** kontak penjual hanya untuk member login, dan halaman detail memakai `Cache-Control: private, no-store` agar tidak tersimpan di cache bersama.
- **Privasi lokasi:** hanya kota atau area umum, tanpa alamat rumah, koordinat dibulatkan sekitar 1 km.
- **Input dari URL:** nilai filter dibersihkan dan dibatasi, dan halaman di bawah 1 dianggap halaman 1.
- **Saran lokasi:** hanya untuk member berprofil lengkap (403 jika tidak) supaya jatah request ke Nominatim tidak dihabiskan satu orang.

---

## 11. Dependensi dengan modul lain

| Modul | Hubungan |
|---|---|
| Profil dan akun | `member_required`, kontak penjual, nama tampilan, dan etalase profil |
| Reports | Halaman detail menampilkan tautan "Laporkan listing ini", dan moderator dapat menyembunyikan atau memulihkan listing dari laporan |
| Favorites | Kartu listing dan halaman detail memuat tombol favorit |
| Sustainable Guides | Tidak ada hubungan langsung |

---

## 12. Testing

Seluruh test berada di app `listings` dan tidak memerlukan internet.

| Berkas | Jumlah test | Yang diuji |
|---|---|---|
| `test_models.py` | 16 | Aturan model, `sold_at`, tag |
| `test_catalog.py` | 14 | Halaman katalog dan pagination |
| `test_detail.py` | 28 | Detail, privasi kontak, listing Hidden |
| `test_manage.py` | 69 | Form, validator, buat, ubah, hapus, status, otorisasi |
| `test_filters.py` | 54 | Pencarian, filter, pengurutan, input aneh, HTMX |
| `test_location.py` | 59 | Nominatim (mock), saran lokasi, throttle, privasi |
| `test_storefront.py` | 37 | Etalase profil |
| `test_seed.py` | 30 | Perintah seed dan halaman dengan data contoh |
| `test_admin.py` | 4 | Moderasi lewat admin |
| `test_scripts.py` | 2 | Skrip template aman saat riwayat HTMX dipulihkan |
| **Total** | **313** | Cakupan sekitar 99% |

Menjalankan:

```bash
python manage.py test listings
```

---

## 13. Seed data

```bash
python manage.py seed_listings
```

Membuat 5 penjual contoh, 50 listing tersedia (10 per kategori), dan 10 listing terjual. Aman dijalankan berulang, dan `--reset` hanya menghapus listing milik akun contoh. Akun contoh tidak punya kata sandi dan memakai kontak `@example.com`. Rincian lengkap ada di `README.md`.

---

## 14. AI Disclosure

Selama pengerjaan proyek ini, saya menggunakan Claude AI sebagai alat bantu belajar dan debugging:

- [Chat 1 - Model: Claude Sonnet 5.5 Medium](https://claude.ai/share/4e2dbd60-0b73-47b4-9f86-1d239a4c347a) digunakan untuk menanyakan syntax kode, misalnya fungsinya untuk apa dan apa yang terjadi kalau baris itu tidak ada.
- [Chat 2 - Model: Claude Sonnet 5.5 Medium](https://claude.ai/share/b3bdbd47-aed5-4bf9-ae52-c8ff5932aa86) sama seperti chat 1, hanya saja dilakukan lebih awal.
- [Chat 3 - Model: Claude Sonnet 5.5 Medium](https://claude.ai/share/2096d16e-4498-451b-8a88-27331591c1f7) digunakan untuk membahas gaya penulisan kode (styling code).
- **Claude Code - Model: Claude Sonnet 5.5 High** digunakan sepanjang sesi pengerjaan modul Clothing Listings di repositori ini: membantu membangun modul secara bertahap, menulis test, meninjau kode, dan menjelaskan kode yang saya tanyakan.

Hasil dari Claude Code tidak saya pakai begitu saja. Saya juga membuat, memperbaiki, dan menyesuaikan kembali kodenya sendiri, menjalankan dan memeriksa hasilnya, serta melakukan seluruh commit dan push sendiri.
