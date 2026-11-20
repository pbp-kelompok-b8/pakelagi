# AI Disclosure — Fitur Akun dan Profil Pakelagi

## 1. Pernyataan penggunaan AI

AI digunakan sebagai alat bantu dalam perencanaan, dokumentasi, implementasi, pengujian, review, dan refactoring fitur akun serta profil Pakelagi. Bantuan ini mencakup pembuatan dan perubahan kode, bukan hanya perbaikan bahasa atau pemberian saran.

Dokumen ini disusun berdasarkan enam transkrip percakapan pada direktori [`AI-Disclosure-Chat/`](AI-Disclosure-Chat/), yang mencatat sesi pada 17–18 dan 30 Oktober 2026. Nama model dan penyedia AI tidak tercantum dalam transkrip tersebut, sehingga dokumen ini tidak mengatribusikan pekerjaan kepada model atau penyedia tertentu.

## 2. Cakupan kontribusi AI

| Area | Bantuan AI yang tercatat |
|---|---|
| Analisis kebutuhan | Mengajukan pertanyaan untuk memperjelas batas MVP, hubungan akun dan profil, onboarding, privasi kontak, etalase, gambar, dan integrasi listing. |
| Dokumentasi | Membantu menyusun serta memperbarui spesifikasi profil, spesifikasi utama, istilah domain, kontrak integrasi listing, dan checklist refactoring. |
| Akun dan onboarding | Membantu implementasi alur registrasi menuju onboarding, penanganan profil belum lengkap, tujuan kembali `next` yang aman, dan pembatasan fitur member. |
| Penghapusan akun | Membantu menyusun spesifikasi dan mengimplementasikan penghapusan akun Django beserta profil secara permanen, termasuk halaman konfirmasi username/password, penghapusan atomik, pencabutan sesi, pembatasan percobaan, serta tautan dari edit profil dan onboarding. |
| Profil | Membantu pembuatan dan pengubahan profil, validasi field, pemisahan email akun dari kontak penjual, dan pembatasan akses berdasarkan kepemilikan serta kelengkapan profil. |
| Halaman 404 | Membantu membuat halaman 404 bermerek Pakelagi dengan template bersama, pesan generik, dan navigasi kembali ke beranda. |
| Etalase dan UI | Membantu tampilan profil sendiri/publik, avatar serta sampul berbasis URL HTTPS, fallback gambar, kartu kontak, tab etalase, dan perapian halaman edit berdasarkan mockup. |
| Integrasi listing | Membantu menyiapkan adapter kosong dan kontrak integrasi untuk modul listing/favorite mendatang; bukan menyelesaikan integrasi data listing nyata. |
| Pengujian | Membantu menulis dan memisahkan tes registrasi, autentikasi, profil, validasi, 404, etalase, URL, migrasi, penyimpanan atomik profil/email, serta penghapusan akun dan sesi. |
| Review dan perbaikan | Membantu mengidentifikasi dan menangani risiko seperti URL kontak berkredensial serta collision content type saat migrasi kepemilikan model. |
| Refactoring | Membantu memisahkan tanggung jawab `accounts`, `profiles`, dan `main`, memperbarui namespace URL, serta merancang migrasi non-destruktif model `Profile`. |

## 3. Peran dan keputusan pengguna

Pengguna memberikan kebutuhan, spesifikasi, referensi mockup, batas perubahan, persetujuan, dan koreksi selama proses. Keputusan pengguna yang terlihat dalam percakapan antara lain:

- Membatasi pekerjaan pada bagian fitur yang diminta dan meminimalkan perubahan di luar lingkup.
- Meminta pemisahan tes berdasarkan domain registrasi, autentikasi, dan profil.
- Memasukkan avatar serta sampul opsional ke MVP dan menggunakan URL gambar eksternal HTTPS sebagai keputusan final, bukan upload file ke server Pakelagi.
- Memilih etalase yang sama untuk profil sendiri dan profil orang lain, dengan edit melalui halaman terpisah.
- Menentukan tab Dijual/Terjual, delapan barang per pemuatan sebagai target integrasi, serta kebijakan favorit berdasarkan status listing dan kepemilikan.
- Menyetujui bahwa nilai kontak tidak dikirim kepada guest atau pengguna yang belum menyelesaikan onboarding.
- Mengoreksi tampilan edit profil yang belum sesuai mockup dan meminta perapian lebih lanjut.
- Meminta dokumen refactoring terlebih dahulu, kemudian secara terpisah memberi izin implementasi.
- Mengoreksi rencana pemindahan template: template tetap berada di `templates/accounts/` dan `templates/profiles/`, bukan dipindahkan ke dalam direktori app.
- Menyetujui batas pengujian refactoring pada HTTP/resolusi URL, migrasi database, dan atomisitas penyimpanan profil serta email akun.
- Menetapkan bahwa penghapusan akun harus menghapus akun Django dan profil secara permanen, berbeda dari penghapusan profil, dengan konfirmasi username/password dan tanpa masa pemulihan.
- Menyetujui kebijakan untuk data terkait akun, termasuk penolakan penghapusan mandiri staff/superuser, pencabutan sesi, batas percobaan konfirmasi, serta pembatalan seluruh perubahan jika penghapusan gagal.
- Menyetujui cakupan implementasi minimal pada model yang tersedia; integrasi Listing/Favorite/Report/Guide tidak diklaim selesai karena modelnya belum tersedia.
- Menyetujui tombol **Hapus akun** di bagian bawah halaman Edit Profil dan onboarding, dengan alur menuju halaman konfirmasi, bukan menghapus langsung.

Persetujuan pengguna dalam percakapan menunjukkan pengarahan dan pengambilan keputusan, tetapi tidak dengan sendirinya membuktikan bahwa setiap perubahan kode telah diperiksa secara manual atau diuji secara independen oleh manusia.

## 4. Ringkasan sumber percakapan

| Sumber | Pekerjaan yang dibahas |
|---|---|
| [Implementasi onboarding dan profil](AI-Disclosure-Chat/session-a5cee861-da7a-4a67-8cf7-bebd22fce6ba.md) | Implementasi onboarding/profil, validasi dan privasi, penghubungan navigasi, serta pemisahan tes berdasarkan domain. |
| [Perincian spesifikasi berdasarkan template](AI-Disclosure-Chat/session-545da8c6-bca1-46d8-b29e-5353db073c9b.md) | Klarifikasi kebutuhan dan pembaruan dokumen, termasuk keputusan final penggunaan URL gambar eksternal, akses kontak, etalase, dan kontrak listing/favorite. |
| [Implementasi halaman 404](AI-Disclosure-Chat/session-d53b9232-2a5d-4c4e-b895-643e94d4ce14.md) | Template 404 bersama, pesan generik, navigasi pemulihan, dan tes integrasi dengan `DEBUG=False`. |
| [Etalase, gambar, kontak, dan edit profil](AI-Disclosure-Chat/session-b66a36d1-c69a-4c2e-8311-a365f3e079df.md) | Etalase dan kontak, URL gambar, adapter listing kosong, perbaikan validasi, serta perapian UI edit profil. |
| [Refactoring app accounts dan profiles](AI-Disclosure-Chat/session-6299d2f1-14bd-4692-aa32-b0535333f519.md) | Penyusunan rencana, koreksi lokasi template, pemisahan app, migrasi model dan content type, tes regresi, review, serta laporan commit. |
| [Spesifikasi dan implementasi penghapusan akun](AI-Disclosure-Chat/session-37391f76-e2ab-4a05-8d1d-8cbe430b26c2.md) | Klarifikasi spesifikasi penghapusan permanen, keputusan dampak terhadap data terkait, implementasi akun/profil dan sesi, pembatasan percobaan, UI konfirmasi, tes, review, dan laporan commit. |

## 5. Pengujian dan batas bukti

Percakapan menyebut penggunaan alur `@grill-with-docs`, `@tdd`, dan `@implement`. Untuk pengujian, asisten melaporkan pemakaian tes Django, system checks, pemeriksaan konsistensi migrasi, kompilasi Python pada pekerjaan awal, serta pemeriksaan diff Git.

Hasil yang **dilaporkan asisten dalam transkrip** meliputi:

- 34 tes lulus setelah implementasi awal onboarding/profil dan pemisahan tes.
- 38 tes lulus setelah pekerjaan halaman 404.
- 58 tes lulus setelah pekerjaan etalase dan validasi, kemudian 60 tes setelah perapian edit profil.
- 64 tes lulus pada akhir refactoring, termasuk pengujian URL, upgrade/rollback migrasi, permission, dan rollback penyimpanan profil/email.
- Commit refactoring `02dfec5` dengan pesan `refactor: split accounts and profiles into Django apps` serta working tree bersih pada akhir sesi tersebut.
- 12 tes fitur penghapusan akun lulus; suite lengkap versi akhir dilaporkan lulus 78 tes. Pemeriksaan Django, konsistensi migrasi, dan review akhir juga dilaporkan selesai.
- Commit penghapusan akun `97bd7a4` dengan pesan `feat(accounts): add confirmed permanent account deletion`.

**Batas bukti:** keenam berkas sumber berisi pesan pengguna dan asisten, tanpa rekaman pemanggilan tool, keluaran terminal lengkap, diff kode, atau laporan reviewer mentah. Angka tes, hasil pemeriksaan, dan commit di atas merupakan laporan yang tercatat dalam percakapan, bukan hasil audit independen oleh dokumen ini. Dokumen ini juga tidak menjalankan ulang tes atau memverifikasi kondisi deployment.

Review yang disebut sebagai review standar dan spesifikasi tidak boleh ditafsirkan sebagai bukti review manusia atau sertifikasi keamanan. Tidak ada typechecker terkonfigurasi yang dilaporkan pada pekerjaan awal; pemeriksaan Django dan kompilasi Python bukan pengganti pemeriksaan tipe statis penuh.

## 6. Keterbatasan dan pekerjaan yang belum selesai

Berdasarkan kondisi yang dinyatakan pada akhir sesi terkait:

- Integrasi listing/favorite nyata masih ditunda. Adapter kosong, hitungan nol, dan empty state tidak berarti kartu listing, pagination data, cuplikan Sold, atau aksi favorit sudah tersedia.
- Penghapusan akun Django beserta profil sudah dilaporkan diimplementasikan dan di-commit; ini berbeda dari aksi penghapusan profil saja. Implementasi yang dicatat mencakup akun, profil, dan sesi, bukan integrasi data dari modul lain yang belum tersedia.
- Gambar profil memakai referensi URL HTTPS eksternal. Server tidak mengambil, memproses, atau menyimpan file gambar; validasi ukuran 5 MB dan isi file gambar bukan kemampuan yang dijanjikan oleh pendekatan ini.
- Pemeriksaan visual langsung lintas browser dan kemiripan mockup belum dilaporkan selesai pada sesi perapian UI.
- Penghapusan akun memerlukan migrasi database sebelum digunakan. Pengujian konkurensi pada PostgreSQL produksi belum dilakukan.
- Konfigurasi proyek pada akhir sesi penghapusan masih memakai `DEBUG=True`; transkrip menyatakan production harus menggunakan `DEBUG=False` agar redaksi exception sensitif berfungsi dengan benar. Perubahan konfigurasi global tersebut tidak termasuk implementasi.
- Hasil tes otomatis tidak membuktikan bebas bug, aman untuk seluruh skenario, atau siap deployment tanpa pemeriksaan lanjutan.

Catatan ini menjelaskan batas pekerjaan pada transkrip, bukan klaim bahwa status proyek tidak mungkin berubah setelah sesi tersebut.

## 7. Tanggung jawab penggunaan hasil AI

Hasil AI perlu diperlakukan sebagai kontribusi yang tetap memerlukan pemeriksaan oleh pengembang. Tim pengembang tetap bertanggung jawab atas pemahaman kode, kesesuaian spesifikasi, keamanan dan privasi, pengujian ulang, peninjauan migrasi, serta keputusan deployment.

Disclosure ini mengungkap cakupan bantuan AI dan batas bukti yang tersedia. Dokumen ini tidak menyatakan bahwa seluruh kode ditulis tanpa bantuan manusia, seluruh fitur produk telah selesai, atau seluruh hasil AI telah diverifikasi secara independen.
