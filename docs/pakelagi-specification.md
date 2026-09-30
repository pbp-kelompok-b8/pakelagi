# Pakelagi — Spesifikasi Produk dan Teknis
## Catatan

Spesifikasi ini adalah acuan ruang lingkup dan kriteria penerimaan MVP. Detail implementasi dapat berkembang selama tidak bertentangan dengan tujuan, aturan akses, dan batasan produk yang tercantum di sini.

| Metadata | Nilai |
|---|---|
| Status | MVP untuk Proyek Tengah Semester PBP 2026 |
| Tanggal spesifikasi | 16 September 2026 |
| Nama kerja | Pakelagi |
| Bahasa aplikasi dan dokumen | Bahasa Indonesia |
| Target deployment | PWS dengan PostgreSQL |

> Dokumen ini adalah sumber kebenaran untuk ruang lingkup, istilah domain, modul, dan kriteria penerimaan Pakelagi. Informasi kelompok dan tautan proyek mengikuti README.

## 1. Ringkasan

Pakelagi adalah platform web untuk komunitas Indonesia yang ingin menemukan dan memasang iklan pakaian preloved dengan harga terjangkau. Platform ini membantu memperpanjang usia pakaian dan mempromosikan slow fashion melalui informasi kondisi barang, tag keberlanjutan, serta panduan konsumsi yang lebih sadar.

Pakelagi adalah **platform listing**, bukan toko online penuh. Pengguna dapat menemukan barang dan menghubungi penjual melalui kontak yang dipilih penjual, tetapi transaksi, pembayaran, pengiriman, dan serah terima berlangsung di luar aplikasi.

## 2. Masalah dan tujuan

### Masalah

- Pengguna sulit menemukan pakaian preloved yang sesuai harga, ukuran, kondisi, dan lokasi.
- Penjual individu membutuhkan tempat sederhana untuk menampilkan pakaian yang sudah tidak digunakan.
- Informasi tentang penggunaan kembali pakaian sering tidak terlihat dalam pengalaman belanja biasa.

### Tujuan MVP

1. Menyediakan katalog listing pakaian preloved yang dapat dicari dan difilter.
2. Memudahkan member membuat, mengubah, melihat, dan menghapus listing miliknya.
3. Menampilkan lokasi umum penjual agar pengguna dapat menemukan pilihan lokal.
4. Menyediakan favorit agar member dapat menyimpan barang untuk dilihat kembali.
5. Mempromosikan slow fashion melalui tag transparan dan sustainable guide.
6. Menyediakan moderasi dasar melalui pelaporan listing.

### Non-goals

Fitur berikut tidak termasuk MVP:

- pembayaran, checkout, dan keranjang belanja;
- pemesanan, reservasi, dan status transaksi;
- pengiriman atau integrasi kurir;
- chat internal;
- kalkulator emisi atau klaim penghematan karbon;
- alamat pickup yang tepat atau alamat rumah;
- upload berkas gambar; listing menggunakan satu URL gambar.

## 3. Pengguna dan peran

| Peran | Kebutuhan | Akses utama |
|---|---|---|
| Guest | Menemukan pakaian dan membaca informasi slow fashion | Melihat listing yang tersedia, panduan yang dipublikasikan, dan halaman detail |
| Member | Menjual pakaian, menyimpan pilihan, dan melaporkan masalah | Semua akses guest; CRUD listing milik sendiri, profile, favorite, dan report; melihat kontak penjual |
| Admin | Menjaga kualitas dan keamanan konten | Mengelola semua listing, guide, report, dan user melalui halaman moderasi |

Satu akun member dapat berperan sebagai penjual dan pencari barang. Tidak ada akun buyer dan seller yang terpisah.

## 4. Ruang lingkup fitur MVP

### 4.1 Beranda

- Menjelaskan tujuan Pakelagi secara singkat.
- Menampilkan tombol menuju katalog listing.
- Menampilkan beberapa listing terbaru atau unggulan.
- Menampilkan ajakan untuk mendaftar sebagai member.
- Menampilkan tautan ke sustainable guide.

### 4.2 Katalog listing

- Menampilkan hanya listing berstatus `Available` kepada publik.
- Mendukung pencarian berdasarkan judul atau brand.
- Mendukung filter kategori, ukuran, kondisi, rentang harga, kota, dan tag keberlanjutan.
- Menggunakan pagination agar halaman tetap ringan.
- Member dapat menekan tombol favorite tanpa reload halaman melalui HTMX.

### 4.3 Detail listing

- Menampilkan gambar, judul, harga, kategori, ukuran, kondisi, brand, deskripsi, kota, dan tag keberlanjutan.
- Menampilkan nama/display name penjual.
- Menampilkan kontak penjual hanya kepada member yang sudah login.
- Menampilkan tombol report kepada member.
- Tidak menampilkan alamat lengkap.

### 4.4 Pengelolaan listing

Member dapat:

- membuat listing;
- melihat seluruh listing miliknya, termasuk yang `Sold` atau `Hidden`;
- mengubah listing miliknya;
- menghapus listing miliknya;
- mengubah status listing miliknya menjadi `Available` atau `Sold`.

Admin dapat menyembunyikan listing yang melanggar aturan. Listing berstatus `Hidden` tidak tampil pada katalog publik.

### 4.5 Profile dan kontak

Member dapat mengatur display name, bio singkat, kota umum, dan metode kontak. Contact value hanya ditampilkan kepada member login dan tidak boleh berisi alamat rumah. Halaman profil publik menampilkan ringkasan listing pemilik berstatus `Available` (Dijual) dan `Sold` (Terjual); listing `Hidden` maupun listing yang disembunyikan moderator tidak ditampilkan.

### 4.6 Favorite

Member dapat menambahkan listing ke favorite, melihat daftar favorite, mengubah catatan pribadi, dan menghapus favorite. Favorite milik satu member bersifat privat.

### 4.7 Sustainable guide

Member dapat mengirim draf tips perawatan pakaian dan melihat draf miliknya. Draf berstatus `Pending` dapat diedit atau dihapus oleh pengirim sebelum keputusan moderator. Admin meninjau lalu menyetujui atau menolak draf; persetujuan tidak otomatis menerbitkan guide. Admin menentukan kapan guide dipublikasikan, dan dapat membuat, membaca, mengubah, serta menghapus artikel tentang slow fashion, perawatan pakaian, perbaikan, reuse, dan conscious shopping. Guest dan member hanya dapat membaca guide yang telah dipublikasikan.

### 4.8 Report dan moderasi

Member dapat membuat report untuk listing, melihat report miliknya, memperbarui atau menghapus report yang masih terbuka. Admin dapat membaca semua report, memperbarui statusnya, menambahkan catatan moderasi, dan mengambil tindakan pada listing terkait.

### 4.9 Integrasi lokasi dengan Nominatim

Pada form listing, seller mencari kota atau area pickup umum melalui Nominatim. Aplikasi menyimpan nama kota/area, latitude, dan longitude untuk ditampilkan dan difilter.

Pakelagi menggunakan [Nominatim Search API](https://nominatim.org/release-docs/latest/api/Search/) dengan batas negara Indonesia (`countrycodes=id`). Implementasi wajib mengikuti [Nominatim Usage Policy](https://operations.osmfoundation.org/policies/nominatim/): memakai User-Agent/Referer yang mengidentifikasi aplikasi, mencantumkan atribusi OpenStreetMap, melakukan caching, dan membatasi request maksimal satu per detik. Jika API gagal, seller tetap dapat menyimpan kota secara manual tanpa alamat lengkap.

## 5. Pembagian modul untuk lima anggota

Setiap modul memiliki Models, Views, Templates, Forms, operasi CRUD, filter autentikasi, dan minimal satu interaksi sisi klien melalui HTMX atau respons parsial.

| Modul | Penanggung jawab | Data utama | Ruang CRUD |
|---|---|---|---|
| Clothing Listings | Anggota 1 — Nugraha Kautsarrizqi Caksana (`2506541250`) | `Listing` | Member mengelola listing sendiri; admin dapat memoderasi semua listing |
| User Profiles | Anggota 2 — Victoriano Iman Santosa (`2506544353`) | `Profile` | Member mengelola profile dan contact preference sendiri; ringkasan listing Available dan Sold milik pengguna dapat dilihat publik |
| Saved Favorites | Anggota 3 — David Liman (`2506601956`) | `Favorite` | Member menambah, melihat, memberi catatan, dan menghapus favorite sendiri |
| Sustainable Guides | Anggota 4 — Muhammad Raihan Al Qadri Kusumaputra (`2506602334`) | `Guide` | Member mengirim dan mengelola draf Pending miliknya; admin meninjau draf serta mengelola publikasi guide; publik membaca guide yang dipublikasikan |
| Reports & Moderation | Anggota 5 — Clevraldo Limuel (`2506656583`) | `Report` | Member membuat/mengelola report sendiri; admin meninjau dan memperbarui status |

Anggota 1 — Clothing Listings: Nugraha Kautsarrizqi Caksana (`2506541250`).

Kategori, ukuran, kondisi, status, alasan report, dan tag keberlanjutan menggunakan pilihan terkontrol pada model/form. Tidak perlu membuat modul terpisah untuk masing-masing pilihan tersebut.

## 6. Model domain

### 6.1 Entitas dan hubungan

```text
User (Django auth)
├── 1—1 Profile
├── 1—N Listing
├── 1—N Favorite ── N—1 Listing
└── 1—N Report ──── N—1 Listing

Admin User ── mengelola ── Guide
Member ── mengirim ── Guide draft (Pending)
Admin User ── memoderasi ── Listing dan Report
```

### 6.2 `Profile`

| Field | Tipe/aturan |
|---|---|
| `user` | One-to-one ke Django `User`, wajib unik |
| `display_name` | teks pendek, wajib |
| `bio` | teks pendek/panjang, opsional |
| `city` | teks pendek, opsional |
| `contact_type` | `email`, `instagram`, atau `other` |
| `contact_value` | teks/URL kontak, opsional |
| `created_at`, `updated_at` | timestamp |

### 6.3 `Listing`

| Field | Tipe/aturan |
|---|---|
| `seller` | ForeignKey ke `User`, wajib |
| `title` | teks 5–120 karakter, wajib |
| `description` | teks, wajib |
| `category` | `Top`, `Bottom`, `Dress`, `Outerwear`, `Modest Wear` |
| `brand` | teks pendek, opsional |
| `size` | `XS`, `S`, `M`, `L`, `XL`, `XXL`, `Free Size` |
| `condition` | `Like New`, `Good`, `Fair`, `Needs Repair` |
| `price` | integer Rupiah, wajib, minimal 0 |
| `image_url` | URL HTTP/HTTPS, wajib |
| `city` | kota/area umum, wajib |
| `latitude`, `longitude` | koordinat Nominatim, opsional bila input manual |
| `is_repairable` | boolean tag, default false |
| `is_upcycled` | boolean tag, default false |
| `is_locally_available` | boolean tag, default true |
| `extends_clothing_life` | boolean tag, default true |
| `status` | `Available`, `Sold`, `Hidden` |
| `created_at`, `updated_at` | timestamp |

Constraint penting:

- Harga tidak boleh negatif.
- Hanya seller pemilik atau admin yang boleh mengubah/menghapus listing.
- Listing `Hidden` tidak boleh muncul pada katalog publik.
- `image_url` harus menggunakan skema HTTP atau HTTPS.
- Form tidak menerima alamat rumah atau alamat pickup yang presisi.

### 6.4 `Favorite`

| Field | Tipe/aturan |
|---|---|
| `user` | ForeignKey ke `User`, wajib |
| `listing` | ForeignKey ke `Listing`, wajib |
| `note` | catatan pribadi, opsional |
| `created_at`, `updated_at` | timestamp |

Constraint: kombinasi `user` dan `listing` harus unik. Member hanya boleh membaca dan mengubah favorite miliknya.

### 6.5 `Guide`

| Field | Tipe/aturan |
|---|---|
| `title` | teks pendek, wajib |
| `slug` | slug unik, wajib |
| `summary` | ringkasan pendek, wajib |
| `body` | isi guide, wajib |
| `cover_url` | URL HTTP/HTTPS, opsional |
| `submission_status` | `Pending`, `Approved`, `Rejected`; berlaku untuk draf kiriman member |
| `review_note` | catatan moderator untuk pengirim, opsional |
| `is_published` | boolean, default false |
| `author` | ForeignKey ke admin/user pembuat |
| `created_at`, `updated_at` | timestamp |

### 6.6 `Report`

| Field | Tipe/aturan |
|---|---|
| `reporter` | ForeignKey ke `User`, wajib |
| `listing` | ForeignKey ke `Listing`, wajib |
| `reason` | `Counterfeit`, `Misleading`, `Offensive`, `Prohibited Item`, `Other` |
| `description` | penjelasan, wajib |
| `status` | `Open`, `Reviewing`, `Resolved`, `Rejected` |
| `moderator_note` | catatan admin, opsional dan privat |
| `created_at`, `updated_at` | timestamp |

## 7. User stories

### Guest

- Sebagai guest, saya ingin melihat katalog agar dapat menemukan pakaian preloved tanpa membuat akun.
- Sebagai guest, saya ingin memfilter berdasarkan harga, ukuran, kondisi, kategori, kota, dan tag agar hasil pencarian relevan.
- Sebagai guest, saya ingin membaca sustainable guide agar memahami slow fashion.
- Sebagai guest, saya ingin mengetahui bahwa kontak seller hanya tersedia untuk member agar aturan privasi jelas.

### Member

- Sebagai member, saya ingin membuat listing agar pakaian yang tidak saya gunakan dapat ditemukan orang lain.
- Sebagai member, saya ingin mengubah atau menghapus listing milik saya agar informasinya tetap akurat.
- Sebagai member, saya ingin menandai listing sebagai sold agar tidak terus ditawarkan.
- Sebagai member, saya ingin menyimpan listing dan menulis catatan pribadi agar dapat membandingkannya nanti.
- Sebagai member, saya ingin melihat kontak seller setelah login agar dapat melanjutkan komunikasi di luar aplikasi.
- Sebagai member, saya ingin melaporkan listing bermasalah agar admin dapat meninjaunya.

### Admin

- Sebagai admin, saya ingin menyembunyikan listing bermasalah agar katalog tetap aman.
- Sebagai admin, saya ingin meninjau report dan mengubah statusnya agar proses moderasi terlacak.
- Sebagai admin, saya ingin mengelola guide agar konten slow fashion tetap relevan.

## 8. Halaman dan URL yang direncanakan

| Halaman | URL contoh | Akses |
|---|---|---|
| Beranda | `/` | Semua |
| Katalog listing | `/listings/` | Semua |
| Detail listing | `/listings/<id>/` | Semua |
| Buat listing | `/listings/create/` | Member |
| Edit listing | `/listings/<id>/edit/` | Pemilik/Admin |
| Hapus listing | `/listings/<id>/delete/` | Pemilik/Admin |
| Profil saya | `/profile/` | Member |
| Edit profil | `/profile/edit/` | Pemilik |
| Profil publik pengguna | `/profile/<user_id>/` | Semua; ringkasan listing Available dan Sold |
| Favorite saya | `/favorites/` | Member |
| Edit catatan favorite | `/favorites/<id>/edit/` | Pemilik |
| Daftar guide | `/guides/` | Semua |
| Detail guide | `/guides/<slug>/` | Semua untuk guide published |
| Draf guide saya | `/guides/my-submissions/` | Member |
| Kirim draf guide | `/guides/submit/` | Member |
| Edit draf Pending | `/guides/submissions/<id>/edit/` | Pengirim selama Pending |
| Daftar report saya | `/reports/` | Member |
| Buat report | `/reports/create/<listing_id>/` | Member |
| Moderasi | `/moderation/` | Admin |
| Kelola guide | `/moderation/guides/` | Admin |
| Kelola report | `/moderation/reports/` | Admin |

Template wajib memakai struktur bersama, minimal `base.html`, header/navbar, footer, halaman error, serta partial untuk kartu listing dan hasil filter.

## 9. Interaktivitas HTMX

### Filter katalog

- Form filter memakai method `GET` ke `/listings/`.
- HTMX menargetkan partial `#listing-results`.
- Filter tidak memuat ulang seluruh halaman.
- URL filter boleh diperbarui agar hasil dapat dibagikan atau di-refresh.
- Jika tidak ada hasil, tampilkan empty state yang jelas.

### Favorite toggle

- Tombol favorite mengirim request `POST` dengan CSRF token.
- Response hanya mengganti tombol atau counter terkait.
- Guest diarahkan ke login.
- Request duplikat tidak boleh membuat favorite ganda.

### Fallback

Setiap aksi HTMX tetap memiliki fallback HTML biasa agar fungsi utama dapat dipakai tanpa JavaScript penuh.

Template dasar `base.html` mengatur CSRF token/header untuk request HTMX secara global, sehingga request yang mengubah data tetap dilindungi Django CSRF.

## 10. Integrasi Nominatim

### Alur

1. Member mengetik kota atau area pickup umum pada form listing.
2. Antarmuka menerapkan debouncing agar pencarian hanya dikirim setelah pengguna berhenti mengetik sejenak. Server mengirim query ke endpoint Search API dengan `format=jsonv2`, `countrycodes=id`, dan jumlah hasil kecil.
3. Member memilih hasil yang sesuai.
4. Aplikasi menyimpan nama area, latitude, dan longitude pada listing.
5. Katalog memakai field kota untuk filter; koordinat tidak digunakan untuk menunjukkan alamat presisi.

### Batasan operasional

- Request dilakukan dari server Django dengan User-Agent yang menjelaskan Pakelagi.
- Hasil query di-cache agar query yang sama tidak dikirim berulang kali.
- Rate limit maksimal satu request per detik dijaga di sisi server.
- UI menampilkan atribusi OpenStreetMap/Nominatim yang sesuai.
- Jika Nominatim tidak tersedia, input kota manual tetap dapat digunakan.
- Respons API tidak boleh membuat halaman error atau mengekspos secret.

## 11. Design system

Bootstrap digunakan melalui CDN untuk layout responsive. CSS custom hanya untuk identitas Pakelagi dan komponen yang tidak tercakup Bootstrap.

| Token | Nilai awal | Penggunaan |
|---|---|---|
| Forest green | `#315C4B` | Tombol utama, link aktif, identitas reuse |
| Terracotta | `#B9674E` | Accent, badge, call-to-action sekunder |
| Warm cream | `#F7F2EA` | Background utama |
| Charcoal | `#25312D` | Teks utama |
| Muted sage | `#DCE7DE` | Surface dan highlight |

Prinsip UI:

- mobile-first dan usable pada layar kecil;
- kontras teks dan background memadai;
- setiap input memiliki label dan pesan error;
- gambar memiliki alt text;
- status memakai teks selain warna;
- tombol dan link dapat digunakan dengan keyboard;
- kartu listing menonjolkan harga, kondisi, kota, dan status.

Tag keberlanjutan harus ditampilkan sebagai fakta yang dipilih seller, bukan sebagai klaim angka dampak lingkungan.

## 12. Keamanan dan privasi

- Gunakan Django authentication dan `login_required` untuk aksi member.
- Terapkan ownership check pada setiap update/delete; jangan hanya mengandalkan ID dari URL.
- Gunakan CSRF protection pada seluruh form POST.
- Validasi semua input melalui Django Forms.
- Validasi URL gambar dan kontak agar hanya HTTP/HTTPS.
- Jangan menaruh password, secret key, atau kredensial database di repository.
- Jangan menampilkan contact value kepada guest.
- Jangan menyimpan atau menampilkan alamat rumah.
- Gunakan escaping bawaan template Django untuk konten user.
- Gunakan pesan sukses/error yang tidak membocorkan detail internal.

## 13. Rencana testing

Gunakan Django `TestCase` dan test client bawaan sebagai baseline.

### Test minimum

- model menerima data valid dan menolak harga negatif;
- URL gambar dan pilihan status tervalidasi;
- guest dapat membaca listing published/available dan guide published;
- halaman profil publik hanya menampilkan listing Available dan Sold, bukan Hidden;
- member dapat mengirim draf guide, mengubah/menghapus draf Pending miliknya, dan tidak dapat menerbitkan guide;
- admin dapat menyetujui/menolak draf guide dan mengatur publikasinya secara terpisah;
- guest tidak dapat membuat, mengubah, atau menghapus data member;
- member hanya dapat mengubah atau menghapus listing/profile/favorite/report miliknya;
- admin dapat memoderasi semua listing dan report;
- seluruh operasi CRUD pada lima modul berjalan;
- filter kombinasi menghasilkan data yang benar;
- favorite unik per member-listing;
- listing hidden tidak tampil di katalog publik;
- contact seller tidak tampil untuk guest;
- endpoint HTMX mengembalikan partial yang sesuai;
- respons Nominatim di-mock dalam test, sehingga test tidak bergantung pada internet;
- gambar yang gagal dimuat menampilkan placeholder lokal;
- kegagalan Nominatim memiliki fallback ke input kota manual.

Target coverage: minimal 80% sebagai sasaran kelompok, dengan fokus pada permission dan alur CRUD.

## 14. Seed data dan deployment

Listing memakai satu URL gambar eksternal dan tidak menerima upload berkas. Jika URL tidak valid atau gambar gagal dimuat, template menampilkan placeholder lokal yang relevan agar katalog dan detail tetap utuh. URL gambar pada data demo harus diperiksa agar dapat diakses.

Deployment pertama wajib memiliki minimal 50 data listing utama. Data boleh sintetis, tetapi harus realistis dan diberi keterangan internal bahwa data tersebut adalah sample.

Distribusi awal yang disarankan:

- 10 Top;
- 10 Bottom;
- 10 Dress;
- 10 Outerwear;
- 10 Modest Wear;
- variasi ukuran, kondisi, harga, kota, dan tag keberlanjutan;
- semua listing sample menggunakan image URL yang valid;
- gunakan akun sample, bukan data kontak pribadi anggota.

Checklist deployment:

- PostgreSQL digunakan pada environment deployment;
- secret key, database URL, allowed hosts, dan konfigurasi production berasal dari environment variable;
- migration berhasil dijalankan;
- static files berhasil dikumpulkan;
- `DEBUG` nonaktif pada production;
- halaman utama, login, katalog, detail, form CRUD, guide, favorite, report, dan moderasi dapat dibuka;
- fixture/seed data dapat diulang tanpa membuat data duplikat yang tidak terkendali;
- URL PWS ditambahkan ke README setelah tersedia.

## 15. Milestone

| Waktu | Hasil yang harus tersedia |
|---|---|
| Checkpoint 1 — 16 September 2026 | Repository bersama, README awal, ide, peran, modul, API, dan pembagian anggota |
| Checkpoint 2 — 28 September–2 Oktober 2026 | Template dasar, design system, integrasi awal, dan deployment pertama ke PWS |
| Pengumpulan akhir — 23 Oktober 2026 | Semua modul terintegrasi, data awal minimal 50 listing, testing lulus, deployment aktif, README lengkap |

Urutan kerja paling aman:

1. Sepakati wireframe, istilah, field, dan ownership.
2. Buat project Django, koneksi PostgreSQL, template dasar, dan design tokens.
3. Buat model inti, migration, authentication, dan fixture sample.
4. Integrasikan modul listing dengan katalog/filter HTMX.
5. Integrasikan profile, favorite, guide, report, dan moderasi.
6. Tambahkan Nominatim, test suite, dan fallback.
7. Deploy lebih awal, lalu lakukan integrasi dan regression test.

## 16. Kriteria penerimaan

Pakelagi dianggap memenuhi spesifikasi apabila:

- guest dapat menemukan listing available melalui katalog dan filter;
- member dapat melakukan CRUD pada data yang menjadi tanggung jawabnya;
- ownership dan akses admin diterapkan tanpa celah IDOR sederhana;
- favorite, report, guide, dan moderasi terintegrasi dengan listing;
- interaksi filter dan favorite memakai HTMX dengan fallback;
- Nominatim digunakan secara bertanggung jawab dan memiliki fallback;
- setidaknya 50 listing tersedia setelah deployment;
- UI responsive, memiliki struktur template bersama, dan memenuhi dasar aksesibilitas;
- test untuk alur penting lulus dengan target coverage 80%;
- aplikasi berjalan di PWS menggunakan PostgreSQL.

## 17. Checklist README kelompok

- [ ] Deskripsi aplikasi dan manfaat bagi masyarakat
- [ ] Nama dan NPM lima anggota
- [ ] Daftar lima modul dan pembagian kerja
- [ ] Peran pengguna: guest, member, admin
- [ ] Dokumentasi [Nominatim Search API](https://nominatim.org/release-docs/latest/api/Search/)
- [ ] Tautan [Nominatim Usage Policy](https://operations.osmfoundation.org/policies/nominatim/)
- [ ] Tautan repository Git
- [ ] Tautan deployment PWS
- [ ] Tautan desain Figma
- [ ] Cara menjalankan project dan melakukan seed data

Informasi proyek saat ini (ikuti README untuk pembaruan):

- Repository: https://github.com/pbp-kelompok-b8/pakelagi
- Deployment PWS: http://david-liman-pakelagi.pws.cs.ui.ac.id
- Figma: https://www.figma.com/design/dCekkdFnlpwdcTY6vaXyrX/Web-Design?m=auto&t=WEkEhoembXHyU27W-1

## 18. Informasi yang masih harus diisi kelompok

```text
Anggota 1: Nugraha Kautsarrizqi Caksana — 2506541250 — Clothing Listings
Anggota 2: Victoriano Iman Santosa — 2506544353 — User Profiles
Anggota 3: David Liman — 2506601956 — Saved Favorites
Anggota 4: Muhammad Raihan Al Qadri Kusumaputra — 2506602334 — Sustainable Guides
Anggota 5: Clevraldo Limuel — 2506656583 — Reports & Moderation

Repository: https://github.com/pbp-kelompok-b8/pakelagi
Figma: https://www.figma.com/design/dCekkdFnlpwdcTY6vaXyrX/Web-Design?m=auto&t=WEkEhoembXHyU27W-1
PWS deployment: http://david-liman-pakelagi.pws.cs.ui.ac.id
```
