# Product Requirements Document (PRD) & Spesifikasi Teknis
## Modul: Sustainable Guides (`sustainableguides`)

| Informasi Dokumen | Detail |
| :--- | :--- |
| **Nama Modul** | `sustainableguides` (Jurnal & Panduan Perawatan Pakaian) |
| **Peran Pengguna** | Pengunjung Publik ( Guest ), Member Terdaftar ( Author ) |
| **Stack Teknologi** | Django 5.2, HTMX, Tailwind CSS, Python Markdown, Vanilla CSS/JS |
| **Status Implementasi** | Selesai (Dilengkapi Mitigasi XSS & Unit Testing) |

---

## 1. Ringkasan Eksekutif & Tujuan Produk

### 1.1 Latar Belakang Masalah
Platform *preloved fashion* Pakelagi membutuhkan sarana edukasi bagi pengguna untuk memperpanjang usia pakai pakaian melalui perawatan, perbaikan, dan pola konsumsi yang sadar (*conscious shopping*)[cite: 4]. Tanpa wadah berbagi pengetahuan yang terkurasi, kualitas pakaian yang beredar di ekosistem dapat menurun dan mengurangi nilai keberlanjutan (*sustainability*). Di sisi lain, membuka fitur penulisan artikel secara bebas kepada pengguna berisiko menurunkan kualitas konten dan membuka celah keamanan siber seperti *Stored Cross-Site Scripting* (XSS)[cite: 3, 4].

### 1.2 Tujuan Produk (Product Goals)
1. **Edukasi Publik:** Menyediakan katalog artikel panduan (*Jurnal*) yang terstruktur, memiliki estimasi waktu baca, daftar isi (*Table of Contents*) otomatis, dan filter kategori yang responsif tanpa memuat ulang seluruh halaman (*full page reload*)[cite: 4].
2. **Kontribusi Komunitas Terkurasi:** Memungkinkan member terdaftar untuk menulis draf panduan menggunakan format *Markdown*, mengelola draf yang masih berstatus menunggu tinjauan (`PENDING`), dan memantau status kurasi serta catatan umpan balik dari moderator[cite: 4].
3. **Keamanan Berlapis:** Menjamin seluruh input pengguna dan hasil render *Markdown* bebas dari injeksi skrip berbahaya (XSS) serta membatasi hak akses modifikasi data secara ketat berdasarkan kepemilikan akun dan siklus hidup status draf[cite: 3, 4].

---

## 2. Peran Pengguna & User Stories

| Aktor | User Story | Kriteria Penerimaan (Acceptance Criteria) |
| :--- | :--- | :--- |
| **Pengunjung Publik** | Sebagai pengunjung, saya ingin membaca panduan yang telah terbit dan memfilternya berdasarkan kategori agar saya menemukan tips perawatan pakaian yang relevan[cite: 4]. | 1. Hanya panduan berstatus `DISETUJUI` dan `is_published=True` yang muncul di katalog publik.<br>2. Filter kategori berjalan secara asinkron menggunakan HTMX (`hx-get` & `hx-push-url`)[cite: 4].<br>3. Menampilkan 1 artikel *Featured* secara acak pada tampilan kategori `SEMUA`[cite: 4]. |
| **Pengunjung Publik** | Sebagai pembaca, saya ingin melihat daftar isi artikel dan rekomendasi panduan lain saat membaca detail artikel[cite: 4]. | 1. Konten Markdown dirender menjadi HTML dengan *styling* tipografi editorial dan *sidebar Table of Contents* (TOC) yang bersifat *sticky* di layar desktop[cite: 4].<br>2. Bagian bawah artikel menampilkan maksimal 3 panduan terbit lainnya secara acak[cite: 4]. |
| **Member Terdaftar** | Sebagai member, saya ingin mengirim draf panduan baru dari halaman dasbor akun saya tanpa harus berpindah halaman[cite: 4]. | 1. Form pengiriman menggunakan HTMX (`hx-post`) yang memperbarui area `#drafts-content-area` secara langsung[cite: 4].<br>2. Tombol kirim menampilkan indikator visual `Mengirim...` dan mengunci interaksi klik ganda selama proses *request* berlangsung[cite: 4].<br>3. Jika validasi gagal, pesan *error* per kolom ditampilkan kembali pada form[cite: 4]. |
| **Member Terdaftar** | Sebagai penulis draf, saya ingin mengubah atau membatalkan draf yang sudah saya kirim selama belum dikurasi oleh admin[cite: 4]. | 1. Draf berstatus `PENDING` menampilkan tautan **Ubah draf** dan tombol **Hapus** (dengan dialog konfirmasi HTMX `hx-confirm`)[cite: 4].<br>2. Draf berstatus `DISETUJUI` atau `DITOLAK` terkunci secara sistem di *frontend* maupun *backend* (tidak dapat diubah atau dihapus oleh member)[cite: 4].<br>3. Draf berstatus `DITOLAK` menampilkan kutipan catatan evaluasi (`rejected_notes`) dari moderator[cite: 4]. |

---

## 3. Siklus Hidup Draf (State Machine)

Setiap entitas `Guide` yang dibuat oleh member melewati siklus status berikut dari sudut pandang penulis:

1. **`PENDING` (Menunggu Tinjauan):**
   * Status awal otomatis saat member mengirim form lewat `submit_draft`.
   * Draf hanya terlihat oleh penulisnya sendiri di halaman **Draf panduan** dan oleh admin di dasbor moderasi[cite: 4].
   * Penulis masih memiliki hak penuh untuk melakukan *Update* (`edit_draft`) dan *Delete* (`delete_draft`)[cite: 4].
2. **`DISETUJUI` + `is_published = False` (Menunggu Jadwal Terbit):**
   * Draf telah lolos kurasi substansi oleh admin, namun belum ditayangkan ke publik[cite: 4].
   * Hak *edit* dan *delete* milik penulis dicabut. Status di tabel riwayat menampilkan informasi *"Disetujui — menunggu jadwal terbit dari admin"*[cite: 4].
3. **`DISETUJUI` + `is_published = True` (Telah Terbit):**
   * Panduan resmi tayang di katalog Jurnal publik dan dapat diakses melalui halaman detail[cite: 4].
   * Tabel riwayat draf penulis menampilkan tautan langsung **Lihat Panduan** menuju halaman artikel publik[cite: 4].
4. **`DITOLAK` (Ditolak Moderator):**
   * Draf tidak lolos kurasi. Hak *edit* dan *delete* terkunci, dan penulis dapat membaca alasan penolakan pada kolom *Catatan & tindakan*[cite: 4].

---

## 4. Spesifikasi Teknis & Arsitektur

### 4.1 Daftar Endpoint & Routing (`sustainableguides`)

| Fungsi View | Nama Route (`app_name:name`) | Metode HTTP | Proteksi Akses | Deskripsi Fungsional |
| :--- | :--- | :--- | :--- | :--- |
| `guide_list` | `sustainableguides:list` | `GET` | Publik | Merender halaman katalog jurnal, menangani query parameter `?category=`, dan memilih 1 *featured guide* acak[cite: 4]. |
| `guide_detail` | `sustainableguides:detail` | `GET` | Publik | Merender artikel terbit (`id`), mengekstrak TOC & HTML dari Markdown secara aman, serta memuat 3 rekomendasi artikel lain[cite: 4]. |
| `user_drafts` | `sustainableguides:my_submissions` | `GET` | `@login_required` | Menampilkan tabel riwayat draf milik pengguna yang sedang login, penghitung draf *pending*, dan form pengiriman draf baru[cite: 4]. |
| `submit_draft` | `sustainableguides:submit_draft` | `POST` | `@login_required` | Memvalidasi input `GuideForm`, menetapkan `author=request.user` dan `status='PENDING'`, lalu merender ulang `user_drafts` via HTMX[cite: 4]. |
| `edit_draft` | `sustainableguides:edit_draft` | `GET`, `POST` | `@login_required` + Kepemilikan | Menampilkan dan memproses form pembaruan draf (`instance=guide`). Menolak akses jika pengguna bukan pemilik atau status bukan `PENDING`[cite: 4]. |
| `delete_draft` | `sustainableguides:delete_draft` | `POST` | `@login_required` + Kepemilikan | Menghapus draf milik pengguna jika statusnya masih `PENDING`, lalu memperbarui daftar draf via HTMX[cite: 4]. |

### 4.2 Struktur Template & Komponen Modular
* **`templates/sustainableguides/guide_list.html`:** Memuat *Hero Section* (`"Merawat, bukan mengganti."`), barisan tombol filter kategori berbasis HTMX yang menargetkan `#jurnal-container`, blok *Featured Article*, *Grid* artikel terbaru, dan *Banner CTA* pengiriman draf[cite: 4].
* **`templates/sustainableguides/guide_detail.html`:** Memuat navigasi *Breadcrumbs*, *Header* artikel (dilengkapi logika kondisional tautan profil publik penulis jika penulis bukan *superuser*), gambar sampul lebar penuh, tata letak 2 kolom (Sidebar TOC & `.markdown-body`), serta *Grid* rekomendasi panduan lainnya[cite: 4].
* **`templates/sustainableguides/user_drafts.html`:** Menggunakan tata letak 2 kolom dengan *Sidebar* navigasi akun di sebelah kiri dan area dinamis `#drafts-content-area` di sebelah kanan yang merangkum notifikasi pesan Django, tabel riwayat draf responsif, serta form pembuatan draf baru[cite: 4].
* **`templates/sustainableguides/edit_draft.html`:** Halaman khusus penyempurnaan draf dengan navigasi *breadcrumbs* kembali ke `sustainableguides:my_submissions` dan indikator status draf saat ini[cite: 4].
* **`templates/sustainableguides/components/guide_card.html`:** Komponen kartu artikel *reusable* yang menampilkan gambar sampul (dengan *fallback placeholder* dan efek *hover scale*), label kategori, judul, ringkasan `line-clamp-2`, nama penulis, estimasi waktu baca (`reading_time`), dan tanggal terbit[cite: 4].
* **`templates/sustainableguides/components/status_badge.html`:** Komponen lencana status modular yang menyesuaikan warna dan ikon untuk status `PENDING`, `DISETUJUI`, dan `DITOLAK`[cite: 4].

---

## 5. Spesifikasi Keamanan & Mitigasi XSS

Mengacu pada standar keamanan aplikasi web (Tutorial 05 PBP), modul ini menerapkan pertahanan berlapis (*Defense in Depth*) terhadap serangan *Cross-Site Scripting* (XSS) dan manipulasi otorisasi[cite: 3]:

1. **Sanitasi Input Sisi Server (`GuideForm` di `forms.py`):**
   * Mengimplementasikan metode pembersihan otomatis `clean_title()`, `clean_ringkasan()`, dan `clean_konten()` menggunakan fungsi `strip_tags()` bawaan Django untuk melucuti seluruh tag HTML berbahaya sejak data dikirimkan[cite: 3].
   * Jika hasil pembersihan menyisakan string kosong (misalnya penyerang memasukkan *payload* murni berisi tag `<img src="x" onerror="alert('XSS!')">` atau `<script></script>`), form secara otomatis melempar `ValidationError` dan menolak penyimpanan ke database[cite: 3].
   * Metode `clean_image_url()` memvalidasi skema tautan secara ketat dan menolak skema berbahaya seperti `javascript:alert(1)` maupun protokol tidak terenkripsi (`http://`), dengan mewajibkan awalan `https://`[cite: 3, 4].
2. **Sanitasi Output & Render Markdown (`views.py`):**
   * Karena template `guide_detail.html` menggunakan filter `|safe` untuk merender HTML hasil konversi Markdown (`{{ content_html|safe }}` dan `{{ table_of_contents|safe }}`)[cite: 4], teks mentah dari database terlebih dahulu dibungkus dengan fungsi `escape(guide.konten)` sebelum diproses oleh `md.convert()`. Langkah ini memastikan apabila terdapat data lama di database yang mengandung tag `<script>`, karakter `<` dan `>` tetap diubah menjadi entitas aman (`&lt;` dan `&gt;`)[cite: 3].
   * Hasil konversi HTML juga disaring menggunakan `.replace('href="javascript:', 'href="#blocked-javascript:')` untuk mencegah eksekusi XSS melalui sintaks tautan Markdown `[Teks](javascript:...)`[cite: 3].
3. **Kontrol Akses & Isolasi Kepemilikan Data:**
   * Query pengambilan objek pada `edit_draft` dan `delete_draft` menggunakan `get_object_or_404(Guide, id=id, author=request.user)` sehingga pengguna lain yang mencoba menembak URL secara paksa akan langsung mendapatkan respons `404 Not Found`.
   * Pengecekan kondisi `if guide.status != 'PENDING'` diterapkan langsung di level *view* untuk mencegah modifikasi draf yang sudah disetujui atau ditolak melalui *request* POST langsung.

---

## 6. Spesifikasi Pengujian (Unit Testing)

Pengujian otomatis diimplementasikan di dalam `sustainableguides/tests.py` yang terbagi ke dalam 3 kelas pengujian utama:
1. **`GuideFormAndSecurityTests`:** Menguji validasi data form normal, pembuktian bahwa `strip_tags` berhasil membersihkan tag `<script>` dan `<iframe>`, penolakan terhadap *payload* khusus tag HTML (`<img onerror=...>`), serta penolakan skema URL `javascript:` dan `http://`[cite: 3].
2. **`GuidePublicViewsTests`:** Menguji visibilitas katalog publik (memastikan draf `PENDING` dan draf `DISETUJUI` yang belum terbit tidak bocor ke publik), pengujian filter kategori, pengujian akses halaman detail (hanya mengembalikan 200 OK jika `is_published=True`, selain itu 404), dan pengujian ketahanan halaman detail terhadap *Stored XSS* pada konten Markdown[cite: 3, 4].
3. **`GuideMemberCRUDAndAuthTests`:** Menguji pengalihan (*redirect* 302) bagi pengunjung anonim, isolasi daftar draf antar-pengguna, pembuatan draf baru, pembaruan draf saat `PENDING`, pemblokiran aksi *edit/delete* oleh pengguna bukan pemilik (404), serta penguncian aksi *edit/delete* ketika status draf sudah berubah menjadi `DISETUJUI`.

---

## 7. AI & Development Disclosure

* **Kolaborasi & Bantuan AI:** Perancangan struktur logika *backend* Django, pola integrasi atribut HTMX, strategi mitigasi keamanan XSS (sanitasi form dan *escaping* Markdown), serta kerangka skenario *unit testing* pada modul ini dikembangkan dengan bantuan asisten AI (Google Gemini).
* **Tautan Transkrip Diskusi AI:** [https://share.gemini.google/fQB7cWM7PlAe](https://share.gemini.google/fQB7cWM7PlAe)
* **Implementasi, Pengetikan Ulang, & Penyesuaian Manual:**
  Sebagian kode tidak sekadar disalin tempel (*copy-paste*), melainkan diketik ulang, diintegrasikan, dan disesuaikan secara manual terhadap arsitektur proyek **Pakelagi**, meliputi:
  1. Penyusunan struktur *layout* dan *styling* Tailwind CSS pada `guide_list.html`, `guide_detail.html`, `user_drafts.html`, dan `edit_draft.html` beserta aturan CSS kustom untuk `.markdown-body` dan `.toc-wrapper` agar selaras dengan sistem desain tipografi (`Cormorant Garamond` & `Jost`)[cite: 4].
  2. Ekstraksi elemen antarmuka yang berulang menjadi komponen parsial (`guide_card.html` dan `status_badge.html`) menggunakan tag `{% include %}`[cite: 4].
  3. Pelacakan dan perbaikan *bug* `NoReverseMatch` secara mandiri pada *breadcrumbs* dan tombol batal di `edit_draft.html` untuk menyelaraskan nama rute URL (`sustainableguides:my_submissions`)[cite: 4].
  4. Penyesuaian alur pengembalian objek `form` yang gagal divalidasi pada fungsi `submit_draft` menuju `user_drafts` agar pesan *error* dari `ValidationError` dapat dirender oleh HTMX di antarmuka pengguna.