# Pakelagi

Platform web listing pakaian preloved untuk komunitas Indonesia — Proyek Tengah Semester PBP 2026.

---

## 1. Deskripsi Aplikasi

**Pakelagi** adalah platform web tempat masyarakat Indonesia dapat menemukan dan memasang iklan pakaian *preloved* (bekas layak pakai) dengan harga terjangkau.

Ceritanya sederhana: banyak orang punya pakaian yang sudah tidak dipakai tetapi masih bagus, sementara di sisi lain banyak orang mencari pakaian murah yang sesuai ukuran, kondisi, dan lokasinya. Keduanya sulit bertemu. Penjual individu tidak punya tempat sederhana untuk memajang barangnya, dan pembeli kesulitan menyaring pilihan berdasarkan harga, ukuran, kondisi, serta kota. Di saat yang sama, informasi tentang penggunaan kembali pakaian nyaris tidak pernah muncul dalam pengalaman belanja biasa.

Pakelagi mempertemukan keduanya lewat katalog listing yang bisa dicari dan difilter, dilengkapi informasi kondisi barang, tag keberlanjutan, dan *sustainable guide*.

Penting untuk dicatat: Pakelagi adalah **platform listing, bukan toko online penuh**. Pengguna menemukan barang dan menghubungi penjual melalui kontak yang dipilih penjual, sedangkan transaksi, pembayaran, pengiriman, dan serah terima berlangsung di luar aplikasi.

### Manfaat bagi masyarakat

- **Ekonomi** — pakaian layak pakai jadi lebih terjangkau, dan penjual individu punya lapak gratis tanpa perlu membuka toko online.
- **Lingkungan** — memperpanjang usia pakai pakaian dan mengurangi limbah tekstil dari budaya *fast fashion*.
- **Edukasi** — *sustainable guide* mengajarkan perawatan, perbaikan, *reuse*, dan belanja yang lebih sadar.
- **Lokal** — filter kota membantu pengguna menemukan penjual terdekat sehingga serah terima lebih mudah.
- **Kepercayaan** — informasi kondisi barang yang transparan, kontak penjual hanya untuk member terdaftar, serta fitur pelaporan dan moderasi.

### Yang **tidak** termasuk MVP

Pembayaran/checkout/keranjang, pemesanan dan status transaksi, integrasi kurir, chat internal, kalkulator emisi karbon, alamat pickup presisi, dan upload berkas gambar (listing memakai satu URL gambar).

---

## 2. Anggota Kelompok

| No | Nama                                     | NPM            | Modul                |
| -- | ---------------------------------------- | -------------- | -------------------- |
| 1  | _Nugraha Kautsarrizqi Caksana_         | `2506541250` | Clothing Listings    |
| 2  | _Victoriano Iman Santosa_              | `2506544353` | User Profiles        |
| 3  | _David Liman_                          | `2506601956` | Saved Favorites      |
| 4  | _Muhammad Raihan Al Qadri Kusumaputra_ | `2506602334` | Sustainable Guides   |
| 5  | _Clevraldo Limuel_                     | `2506656583` | Reports & Moderation |

---

## 3. Daftar Modul dan Pembagian Kerja

Setiap modul wajib memiliki Models, Views, Templates, Forms, operasi CRUD lengkap, filter autentikasi, dan **minimal satu interaksi sisi klien** melalui HTMX atau respons parsial.

### Modul 1 — Clothing Listings (Anggota 1)

Model `Listing`. Inti aplikasi: katalog listing pakaian preloved dengan pencarian (judul/brand), filter (kategori, ukuran, kondisi, rentang harga, kota, tag keberlanjutan), dan pagination. Member mengelola listing miliknya sendiri (buat, lihat, ubah, hapus, ubah status `Available`/`Sold`); admin dapat memoderasi dan menyembunyikan (`Hidden`) semua listing. Termasuk integrasi Nominatim pada form listing dan filter katalog berbasis HTMX.

### Modul 2 — User Profiles (Anggota 2)

Model `Profile` (relasi 1–1 dengan Django `User`). Member mengatur display name, bio singkat, kota umum, serta metode kontak (`email` / `instagram` / `other`). Aturan privasi: contact value **hanya** ditampilkan kepada member yang sudah login, dan tidak boleh berisi alamat rumah.

### Modul 3 — Saved Favorites (Anggota 3)

Model `Favorite`. Member menambah listing ke favorit, melihat daftarnya, menulis catatan pribadi, dan menghapusnya. Daftar favorit bersifat privat per member, dan kombinasi `user`+`listing` harus unik. Tombol favorite bekerja via HTMX tanpa reload halaman.

### Modul 4 — Sustainable Guides (Anggota 4)

Model `Guide`. Admin melakukan CRUD artikel tentang slow fashion, perawatan pakaian, perbaikan, *reuse*, dan *conscious shopping*. Guest dan member dapat membaca guide yang berstatus published (`is_published`).

### Modul 5 — Reports & Moderation (Anggota 5)

Model `Report`. Member melaporkan listing bermasalah (`Counterfeit`, `Misleading`, `Offensive`, `Prohibited Item`, `Other`), melihat report miliknya, serta memperbarui/menghapus report yang masih terbuka. Admin membaca semua report, memperbarui status (`Open` → `Reviewing` → `Resolved`/`Rejected`), menambahkan catatan moderasi privat, dan mengambil tindakan pada listing terkait.

> Kategori, ukuran, kondisi, status, alasan report, dan tag keberlanjutan memakai pilihan terkontrol (*choices*) pada model/form — tidak perlu modul terpisah.

---

## 4. Public API yang Digunakan

**Nominatim (OpenStreetMap) — Search API**

| Item            | Tautan                                                   |
| --------------- | -------------------------------------------------------- |
| Dokumentasi API | https://nominatim.org/release-docs/latest/api/Search/    |
| Usage Policy    | https://operations.osmfoundation.org/policies/nominatim/ |

**Cara pakai.** Pada form listing, seller mengetik kota atau area pickup umum. Server Django mengirim query ke Search API dengan `format=jsonv2` dan `countrycodes=id` (dibatasi Indonesia) serta jumlah hasil kecil. Seller memilih hasil yang sesuai, lalu aplikasi menyimpan **nama area, latitude, dan longitude** pada listing. Katalog memakai field kota untuk filter; koordinat tidak dipakai untuk menunjukkan alamat presisi.

**Kepatuhan terhadap Usage Policy:**

- Request dikirim dari server Django dengan User-Agent/Referer yang mengidentifikasi Pakelagi.
- Rate limit maksimal **satu request per detik** dijaga di sisi server.
- Hasil query di-cache agar query yang sama tidak dikirim berulang.
- Atribusi OpenStreetMap/Nominatim ditampilkan di UI.
- **Fallback:** jika Nominatim tidak tersedia, seller tetap bisa mengisi kota secara manual tanpa alamat lengkap. Dalam testing, respons Nominatim di-*mock* agar test tidak bergantung pada internet.

---

## 5. Jenis / Peran Pengguna

| Peran            | Kebutuhan                                              | Akses utama                                                                                                                                          |
| ---------------- | ------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Guest**  | Menemukan pakaian dan membaca informasi slow fashion   | Melihat listing berstatus`Available`, membaca guide yang dipublikasikan, dan membuka halaman detail. **Tidak** dapat melihat kontak penjual. |
| **Member** | Menjual pakaian, menyimpan pilihan, melaporkan masalah | Semua akses guest; CRUD listing miliknya, profile, favorite, dan report; dapat melihat kontak penjual                                                |
| **Admin**  | Menjaga kualitas dan keamanan konten                   | Mengelola semua listing, guide, report, dan user melalui halaman moderasi                                                                            |

Satu akun member berperan sekaligus sebagai penjual dan pencari barang — **tidak ada** akun buyer dan seller yang terpisah.

---

## 6. Tautan Deployment PWS

```
PWS: http://david-liman-pakelagi.pws.cs.ui.ac.id
```

---

## 7. Tautan Desain Figma

```
Figma: https://www.figma.com/design/dCekkdFnlpwdcTY6vaXyrX/Web-Design?m=auto&t=WEkEhoembXHyU27W-1
```

---

## 8. Cara Menjalankan Project

### Prasyarat

- Python 3.11+ (lingkungan pengembangan memakai 3.14)
- `pip`

### Instalasi lokal

```bash
# 1. Clone repository
git clone https://github.com/pbp-kelompok-b8/pakelagi.git
cd pakelagi

# 2. Buat dan aktifkan virtual environment
python -m venv env

# Windows (Git Bash)
source env/Scripts/activate
# Windows (PowerShell)
env\Scripts\Activate.ps1
# macOS/Linux
source env/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Salin file environment lalu sesuaikan nilainya
cp .env.example .env   # buat .env.example jika belum ada

# 5. Jalankan migration
python manage.py migrate

# 6. (Opsional) buat superuser untuk akses admin/moderasi
python manage.py createsuperuser

# 7. Jalankan development server
python manage.py runserver
```

Aplikasi berjalan di `http://127.0.0.1:8000/`.

Secara default (`PRODUCTION` tidak diset atau `false`), project memakai **SQLite** (`db.sqlite3`) agar mudah dijalankan lokal tanpa setup PostgreSQL. Di production/PWS, set `PRODUCTION=true` beserta `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` pada `.env` agar aplikasi memakai **PostgreSQL**.

### Seed data

```bash
python manage.py loaddata fixtures/seed_listings.json
```

> ⚠️ Fixture seed data (`fixtures/seed_listings.json`, minimal 50 listing sesuai §14 spesifikasi) **belum dibuat** — akan ditambahkan bertahap seiring modul masing-masing anggota selesai. Update perintah di atas begitu path fixture final tersedia.

---

## Informasi Tambahan

- **Repository Git:** [github.com/pbp-kelompok-b8/pakelagi](https://github.com/pbp-kelompok-b8/pakelagi)
- **Target deployment:** PWS dengan PostgreSQL
- **Seed data:** minimal 50 listing (10 per kategori) pada deployment pertama
- **Target test coverage:** 80%, fokus pada permission dan alur CRUD

### Milestone

| Waktu                                | Hasil                                                                                   |
| ------------------------------------ | --------------------------------------------------------------------------------------- |
| Checkpoint 1 — 16 September 2026    | Repository bersama, README awal, ide, peran, modul, API, pembagian anggota              |
| Checkpoint 2 — 28 Sep – 2 Okt 2026 | Template dasar, design system, integrasi awal, deployment pertama ke PWS                |
| Pengumpulan akhir — 23 Oktober 2026 | Semua modul terintegrasi, ≥50 listing, testing lulus, deployment aktif, README lengkap |

---

_Spesifikasi lengkap: [Pakelagi — Spesifikasi Produk dan Teknis](https://hackmd.io/@xFcOTexpRnub0Hpvz_22tA/rk2xpawYMl)_
