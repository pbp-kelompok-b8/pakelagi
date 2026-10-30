# Pakelagi — Spesifikasi Fitur Report & Moderasi

| Metadata | Nilai |
|---|---|
| Modul | Modul 5 — Reports & Moderation |
| Penanggung jawab | Anggota 5 — Clevraldo Limuel (`2506656583`) |
| Model utama | `Report` |
| Django app | `reports` (model, form, view, template, test milik modul ini) |
| Acuan | `docs/pakelagi-specification.md` §4.8, §6.6, §8, §9, §12, §13 |

> Dokumen ini merinci spesifikasi induk untuk modul Report. Jika ada pertentangan, spesifikasi induk menang. Poin bertanda **[Usulan]** adalah keputusan desain yang belum ditetapkan di spesifikasi induk dan perlu disepakati kelompok.

---

## 1. Tujuan

Memberi member jalan untuk melaporkan listing yang bermasalah, dan memberi admin alat untuk meninjau laporan, mencatat keputusan, serta mengambil tindakan pada listing terkait. Fitur ini adalah satu-satunya mekanisme moderasi MVP, jadi harus sederhana, terlacak, dan tidak bisa disalahgunakan.

**Di luar cakupan:** laporan terhadap user atau guide, notifikasi email, banding oleh penjual, sistem poin pelanggaran, dan chat dengan pelapor.

---

## 2. Aktor dan hak akses

| Aksi | Guest | Member | Admin (`is_staff`) |
|---|---|---|---|
| Membuat report | Tidak (diarahkan ke login) | Ya, kecuali listing miliknya sendiri | Ya |
| Melihat daftar report sendiri | Tidak | Ya | Ya |
| Mengubah/menghapus report sendiri | Tidak | Ya, hanya saat status `Open` | Tidak (mengelola lewat moderasi) |
| Membaca semua report | Tidak | Tidak | Ya |
| Mengubah status, menulis catatan moderasi | Tidak | Tidak | Ya |
| Menyembunyikan/memulihkan/menghapus listing dari report | Tidak | Tidak | Ya |

Seller **tidak** dapat melihat report yang menyasar listing miliknya, dan tidak dapat melihat identitas pelapor.

---

## 3. Model `Report`

| Field | Tipe/aturan |
|---|---|
| `reporter` | ForeignKey ke `User`, wajib, `on_delete=CASCADE`, `related_name="reports"` |
| `listing` | ForeignKey ke `Listing`, wajib, `related_name="reports"` |
| `reason` | choices: `Counterfeit`, `Misleading`, `Offensive`, `Prohibited Item`, `Other` |
| `description` | `TextField`, wajib, 10–1000 karakter setelah di-strip |
| `status` | choices: `Open`, `Reviewing`, `Resolved`, `Rejected`; default `Open` |
| `moderator_note` | `TextField`, opsional, **privat** (tidak pernah dirender ke member) |
| `reviewed_by` | **[Usulan]** ForeignKey ke `User`, null, admin terakhir yang mengubah status |
| `created_at`, `updated_at` | timestamp |

**Label tampilan (UI berbahasa Indonesia, nilai tersimpan tetap bahasa Inggris):**

| Nilai | Label |
|---|---|
| `Counterfeit` | Barang palsu / tiruan |
| `Misleading` | Informasi menyesatkan |
| `Offensive` | Konten tidak pantas |
| `Prohibited Item` | Barang terlarang |
| `Other` | Lainnya |
| `Open` | Terbuka |
| `Reviewing` | Sedang ditinjau |
| `Resolved` | Selesai |
| `Rejected` | Ditolak |

### Constraint dan aturan data

1. `description` tidak boleh kosong atau hanya spasi.
2. Reporter tidak boleh melaporkan listing yang `seller`-nya adalah dirinya sendiri (validasi di form **dan** view).
3. **[Usulan]** Satu member hanya boleh punya satu report aktif (`Open`/`Reviewing`) per listing, lewat `UniqueConstraint` bersyarat. Tujuannya mencegah spam. Setelah report `Resolved`/`Rejected`, member boleh melapor lagi bila ada hal baru.
4. `moderator_note` hanya ditulis lewat form admin.
5. **[Usulan]** `listing` memakai `on_delete=CASCADE` sesuai spesifikasi induk (field wajib). Konsekuensinya, jika seller menghapus listing, report terkait ikut hilang dan riwayat moderasinya tidak tersisa. Alternatif: `SET_NULL` plus snapshot judul listing. Keputusan perlu disepakati dengan Anggota 1.

### Alur status

```text
Open ──► Reviewing ──► Resolved
  │          │
  └──────────┴────────► Rejected
```

- Transisi yang diizinkan: `Open → Reviewing`, `Open → Resolved/Rejected`, `Reviewing → Resolved/Rejected`.
- **[Usulan]** Report berstatus `Resolved`/`Rejected` bisa dibuka kembali ke `Reviewing` oleh admin (untuk koreksi salah klik), tetapi tidak kembali ke `Open`.
- Transisi tidak valid ditolak server dengan pesan error umum.

---

## 4. Fitur

### 4.1 Membuat report (Member)

- Titik masuk: tombol **Laporkan listing** di halaman detail listing (hanya tampil untuk member login dan bukan pemilik listing).
- Halaman: `/reports/create/<listing_id>/`.
- Form: pilihan alasan (`reason`) dan penjelasan (`description`). Ringkasan listing (judul, gambar, kota) ditampilkan di atas form sebagai konteks, bukan field yang bisa diubah.
- Listing yang boleh dilaporkan: `Available` dan `Sold`. Listing `Hidden` mengembalikan 404 untuk non-admin.
- Setelah berhasil: redirect ke `/reports/` dengan pesan sukses.
- Jika sudah ada report aktif untuk listing yang sama: tampilkan pesan bahwa laporan sudah diterima dan arahkan ke daftar report, tanpa membuat data baru.

### 4.2 Daftar report saya (Member)

- Halaman: `/reports/`, hanya menampilkan report milik user yang login, terbaru dulu, dengan pagination.
- Tiap baris: judul listing (tautan ke detail bila masih ada dan boleh dilihat), alasan, status (teks + tag), tanggal.
- Aksi **Ubah** dan **Hapus** hanya muncul untuk status `Open`.
- `moderator_note` **tidak ditampilkan**. Untuk status `Resolved`/`Rejected`, tampilkan teks netral, misalnya "Laporan telah ditinjau oleh tim moderasi."
- Empty state yang jelas jika belum ada report.

### 4.3 Mengubah dan menghapus report (Member)

- URL **[Usulan]**: `/reports/<id>/edit/` dan `/reports/<id>/delete/`.
- Hanya pemilik, hanya saat `Open`. Query selalu difilter `reporter=request.user`; bila tidak cocok, kembalikan 404 (bukan 403, agar ID tidak bisa diprobing).
- Jika status sudah berubah saat form dibuka lalu disubmit, aksi ditolak dengan pesan "Laporan sudah diproses dan tidak dapat diubah."
- Hapus memakai halaman konfirmasi (POST), dengan fallback HTML biasa.
- Yang bisa diubah hanya `reason` dan `description`. `listing` dan `reporter` tidak bisa diganti.

### 4.4 Moderasi report (Admin)

**Dasbor `/moderation/`** (bersama dengan Modul 4): ringkasan jumlah report per status dan tautan ke `/moderation/reports/`. Hanya bagian report yang menjadi tanggung jawab modul ini.

**Daftar `/moderation/reports/`:**
- Menampilkan semua report, default urut `Open` lebih dulu lalu terbaru.
- Filter: status, alasan, dan pencarian (judul listing atau username pelapor). Pagination.
- Tiap baris: listing, alasan, pelapor, status, tanggal, tautan ke detail.
- Jumlah report aktif per listing ditampilkan agar listing yang dilaporkan berulang mudah terlihat.

**Detail `/moderation/reports/<id>/` [Usulan]:**
- Menampilkan data lengkap report, pelapor, ringkasan listing (status saat ini, penjual, tautan ke detail), dan daftar report lain pada listing yang sama.
- Form admin: ubah `status` dan isi `moderator_note`.
- Panel **Tindakan pada listing**:
  - **Sembunyikan listing**: set `Listing.status = Hidden`.
  - **Pulihkan listing**: set kembali ke `Available`.
  - **Hapus listing**: dengan konfirmasi, mengikuti aturan Modul 1.
- Tindakan listing bersifat terpisah dari perubahan status report. Admin boleh menyembunyikan listing lalu menandai report `Resolved`, atau menolak report tanpa menyentuh listing.
- **[Usulan]** Tindakan listing dijalankan lewat fungsi/service milik Modul 1 (mis. `set_listing_status(listing, status)`) agar logika status tidak diduplikasi di modul ini.
- Setiap perubahan mengisi `reviewed_by` dan `updated_at`.

---

## 5. URL

| Halaman | URL | Akses |
|---|---|---|
| Daftar report saya | `/reports/` | Member |
| Buat report | `/reports/create/<listing_id>/` | Member |
| Edit report | `/reports/<id>/edit/` | Pemilik, saat `Open` |
| Hapus report | `/reports/<id>/delete/` | Pemilik, saat `Open` |
| Dasbor moderasi | `/moderation/` | Admin |
| Kelola report | `/moderation/reports/` | Admin |
| Detail report (admin) | `/moderation/reports/<id>/` | Admin |
| Ubah status report | `/moderation/reports/<id>/status/` | Admin (POST) |
| Tindakan listing | `/moderation/reports/<id>/listing-action/` | Admin (POST) |

Nama URL memakai namespace `reports` (mis. `reports:my_reports`, `reports:create`, `reports:moderation_list`) supaya `href="#"` di `header.html` dan `footer.html` dapat diganti dengan `{% url %}`.

Jalur `/moderation/...` ditangani oleh app ini untuk bagian report. Prefix bersama dengan Modul 4 (`/moderation/guides/`) perlu dikoordinasikan agar tidak bentrok di `pakelagi/urls.py`.

---

## 6. Interaktivitas HTMX

Syarat minimal modul: satu interaksi sisi klien. Rencana:

1. **Filter daftar moderasi** (utama): form `GET` ke `/moderation/reports/`, `hx-target="#report-results"`, `hx-push-url="true"`. View mengembalikan partial `reports/partials/report_results.html` bila `request.htmx`/header `HX-Request` ada, dan halaman penuh bila tidak.
2. **Ubah status inline** (opsional): dropdown status di baris/detail mengirim `POST`, respons hanya mengganti blok status dan `#report-results` terkait.
3. **Hapus report sendiri**: konfirmasi lalu baris dihapus tanpa reload.

**Aturan:** semua request pengubah data memakai `POST` dengan CSRF (sudah global lewat `hx-headers` di `base.html`). Setiap aksi HTMX punya fallback form HTML biasa yang berfungsi tanpa JavaScript. Empty state tampil saat filter tidak menghasilkan data.

---

## 7. Forms

| Form | Field | Validasi |
|---|---|---|
| `ReportForm` | `reason`, `description` | alasan harus salah satu pilihan; deskripsi 10–1000 karakter, di-strip; menolak laporan atas listing sendiri (diteruskan `listing` dan `user` dari view) |
| `ModerationReportForm` | `status`, `moderator_note` | transisi status valid; `moderator_note` maksimal 1000 karakter; wajib diisi saat memilih `Rejected` **[Usulan]** |
| `ListingActionForm` | `action` (`hide`/`restore`/`delete`) | pilihan terkontrol |

Semua input divalidasi lewat Django Forms. Setiap field punya label dan pesan error (`.field`, `.errorlist`).

---

## 8. Template

```text
templates/reports/
├── my_reports.html                  # daftar report saya
├── report_form.html                 # buat & edit (satu template)
├── report_confirm_delete.html
├── moderation/
│   ├── dashboard.html               # bersama Modul 4, bagian report saja
│   ├── report_list.html             # halaman penuh + form filter
│   └── report_detail.html
└── partials/
    ├── report_results.html          # target HTMX #report-results
    └── report_status.html           # tag status
```

- Semua extend `base.html` dan memakai komponen yang sudah ada: `.container-page`, `.page-section`, `.panel`, `.field`, `.btn-*`, `.tag`, `.flash`, `.empty-state`, `.label-caps`.
- Status memakai **teks + tag**, bukan warna saja: `Open` → `.tag-accent`; `Reviewing` → `.tag`; `Resolved` → `.tag-sustain`; `Rejected` → `.tag-sold`. Tidak perlu CSS baru kecuali benar-benar dibutuhkan.
- Tabel di layar kecil harus bisa di-scroll horizontal atau berubah menjadi kartu bertumpuk (mobile-first).
- Nama listing dan deskripsi report dirender dengan auto-escape Django, tanpa `|safe`.

---

## 9. Keamanan dan privasi

- `@login_required` untuk semua halaman member; `@user_passes_test(lambda u: u.is_staff)` (atau mixin setara) untuk semua halaman `/moderation/`. Guest diarahkan ke login, member non-admin mendapat 403/404 di halaman moderasi.
- **Ownership check pada query**, bukan hanya pada ID URL: `get_object_or_404(Report, pk=pk, reporter=request.user)`.
- `moderator_note`, identitas pelapor, dan keberadaan report **tidak pernah** muncul di halaman penjual, halaman publik, maupun respons HTMX untuk member.
- Semua aksi pengubah memakai `POST` + CSRF. Aksi admin tidak boleh dapat dipicu lewat `GET`.
- Pesan error tidak membocorkan detail internal (mis. tidak menyebut "report ID 12 milik user X").
- **[Usulan]** Batasi laju pembuatan report per member (mis. maksimal 5 report per jam) untuk mencegah spam; cukup dengan pengecekan jumlah `created_at` terbaru di view.
- Aturan privasi lain dari spesifikasi induk tetap berlaku: tidak ada alamat rumah atau kontak pribadi dalam deskripsi. Tambahkan helper text di form: "Jangan menulis nomor telepon atau alamat pribadi."

---

## 10. Dependensi dengan modul lain

| Modul | Kebutuhan |
|---|---|
| Modul 1 (Listings) | Model `Listing` dengan `status` (`Available`/`Sold`/`Hidden`), `seller`, halaman detail dengan tombol laporkan, serta fungsi untuk mengubah/menghapus status listing sebagai admin. **Modul ini tidak bisa diuji penuh sebelum `Listing` ada**; selama menunggu, gunakan model stub di test atau branch bersama. |
| Modul 2 (Profiles) | Tampilan nama pelapor/penjual (`display_name`, fallback `username`). |
| Modul 4 (Guides) | Berbagi prefix `/moderation/` dan dasbor moderasi; header sudah memiliki tautan **Moderasi** untuk `is_staff`. |
| Auth | Halaman login (`LOGIN_URL`) harus tersedia agar redirect guest berjalan. |

Perubahan pada file bersama yang perlu dikoordinasikan: `pakelagi/settings.py` (`INSTALLED_APPS`, `LOGIN_URL`), `pakelagi/urls.py` (include app), `templates/components/header.html` dan `footer.html` (ganti `href="#"`), serta halaman detail listing (tombol laporkan).

---

## 11. Rencana testing

Gunakan Django `TestCase`. Hubungan dengan `Listing` memakai data dummy di `setUp`. Target coverage modul: **≥ 80%**, fokus pada permission dan alur CRUD.

**Model**
- Report valid tersimpan dengan status default `Open`.
- Deskripsi kosong/spasi saja ditolak; alasan di luar choices ditolak.
- Constraint report aktif ganda ditolak (bila usulan diterima).

**Permission**
- Guest dialihkan ke login pada semua URL member dan moderasi.
- Member biasa mendapat 403/404 di `/moderation/...`.
- Member tidak dapat melihat, mengubah, atau menghapus report member lain (404).
- Member tidak dapat melaporkan listing sendiri.
- Member tidak dapat mengubah/menghapus report berstatus selain `Open`.
- Admin dapat membaca semua report dan mengubah status.

**CRUD**
- Create: report tersimpan dengan `reporter` = user login, redirect ke `/reports/`.
- Read: `/reports/` hanya berisi report milik sendiri.
- Update: `reason`/`description` berubah saat `Open`; `listing`/`reporter` tidak bisa dimanipulasi lewat POST.
- Delete: report terhapus lewat POST; GET hanya menampilkan konfirmasi.

**Moderasi**
- Transisi status valid berhasil, tidak valid ditolak.
- `moderator_note` tersimpan dan **tidak muncul** di halaman `/reports/` milik pelapor.
- Tindakan sembunyikan membuat listing `Hidden` dan hilang dari katalog publik.
- Tindakan pulihkan mengembalikan listing ke `Available`.
- Aksi admin lewat `GET` ditolak (405).

**HTMX**
- Request dengan header `HX-Request` mengembalikan partial (tanpa `<html>`), tanpa header mengembalikan halaman penuh.
- Filter status/alasan/pencarian menghasilkan data yang benar, termasuk kombinasi filter.
- Empty state tampil saat tidak ada hasil.

**Keamanan**
- Request POST tanpa CSRF token ditolak.
- Input yang mengandung HTML ter-escape pada output.

---

## 12. Seed data

- Tambahkan fixture `fixtures/seed_reports.json` berisi **8–12 report sample** yang mencakup semua status dan semua alasan, memakai akun sample (bukan data pribadi anggota) dan listing dari seed utama.
- Beri keterangan internal bahwa data adalah sample (mis. prefix `[SAMPLE]` pada `moderator_note`).
- Fixture harus aman dijalankan ulang (pakai `pk` tetap agar tidak menggandakan data).
- Buat setidaknya satu akun admin sample untuk demo moderasi; kredensial **tidak** disimpan di repository.

---

## 13. Kriteria penerimaan

Modul Report dianggap selesai apabila:

- [ ] Member login dapat melaporkan listing orang lain dengan alasan dan penjelasan, dan tidak dapat melaporkan listing sendiri.
- [ ] Member melihat daftar report miliknya saja, dan dapat mengubah atau menghapus report yang masih `Open`.
- [ ] Report berstatus `Reviewing`/`Resolved`/`Rejected` terkunci dari perubahan member.
- [ ] Admin dapat melihat semua report, memfilternya, mengubah status, dan menulis catatan moderasi.
- [ ] Admin dapat menyembunyikan, memulihkan, atau menghapus listing dari halaman report; listing `Hidden` hilang dari katalog publik.
- [ ] `moderator_note` dan identitas pelapor tidak pernah terlihat oleh member lain atau penjual.
- [ ] Tidak ada celah IDOR sederhana: semua akses report difilter berdasarkan kepemilikan atau peran admin.
- [ ] Filter moderasi memakai HTMX dengan partial `#report-results` dan memiliki fallback tanpa JavaScript.
- [ ] Semua template memakai `base.html`, responsif, status berupa teks (bukan warna saja), dan form memiliki label serta pesan error.
- [ ] Test modul lulus dengan coverage ≥ 80%.
- [ ] Fixture sample report tersedia dan tautan di header/footer menuju halaman report/moderasi berfungsi di deployment PWS.

---

## 14. Keputusan terbuka untuk kelompok

| # | Pertanyaan | Usulan |
|---|---|---|
| 1 | Perilaku `on_delete` saat listing dihapus | CASCADE sesuai spesifikasi; pertimbangkan `SET_NULL` + snapshot judul bila riwayat moderasi penting |
| 2 | Batasan satu report aktif per member per listing | Ya, lewat `UniqueConstraint` bersyarat |
| 3 | Apakah `Rejected` mewajibkan catatan moderasi | Ya |
| 4 | Siapa yang memiliki fungsi ubah status listing | Modul 1 menyediakan, Modul 5 memanggil |
| 5 | Pembatasan laju pembuatan report | 5 report per jam per member |