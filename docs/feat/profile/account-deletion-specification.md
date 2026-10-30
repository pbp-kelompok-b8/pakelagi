# Spesifikasi Penghapusan Akun

## 1. Tujuan dan hubungan dengan spesifikasi lain

Dokumen ini menetapkan perilaku produk untuk penghapusan akun Pakelagi. Dokumen ini menetapkan target fitur; **implementasi saat ini baru mencakup akun Django dan profil**, sesuai model yang tersedia. Integrasi Listing/Favorite/Report/Guide belum tersedia dan tidak dinyatakan selesai. Spesifikasi produk utama tetap menjadi sumber kebenaran domain; rincian penghapusan akun ini melengkapi bagian autentikasi, profil, listing, favorite, guide, dan report.

Penghapusan akun berbeda dari penghapusan profil. Penghapusan profil hanya menghapus data profil dan tidak menghapus akun. Fitur ini menghapus akun login Django beserta profil dan data terkait yang ditetapkan di sini.

## 2. Keputusan produk

- Penghapusan hanya tersedia untuk akun yang sedang login dan hanya dapat menghapus akun itu sendiri. Tidak ada kemampuan untuk menghapus akun pengguna lain.
- Akun Django dengan `is_staff=True` atau `is_superuser=True` tidak dapat menggunakan alur penghapusan mandiri. Penonaktifan/penghapusan akun admin harus ditangani melalui prosedur admin terpisah.
- Penghapusan bersifat permanen dan langsung setelah konfirmasi valid, tanpa masa tunggu atau pemulihan.
- Konfirmasi dilakukan pada halaman khusus, bukan melalui aksi GET atau konfirmasi browser sederhana.
- Pengguna wajib memasukkan username akun saat ini dan password saat ini. Tidak diperlukan kata konfirmasi tambahan.
- Jika berhasil, akun, sesi login, profil, serta data terkait yang disebut pada §4 dihapus atau dianonimkan sesuai kebijakan di dokumen ini.
- Username yang dihapus menjadi tersedia kembali. Pendaftaran baru dengan username sama membuat akun baru yang tidak mewarisi data akun lama.

## 3. Alur pengguna

1. Pemilik membuka aksi **Hapus akun** di bagian paling bawah form Edit Profil (`/profile/edit/`), dalam bagian **Zona berbahaya**. Tautan yang sama tersedia di halaman onboarding agar akun tanpa profil lengkap tetap dapat dihapus. Aksi ini harus dibedakan secara visual dan tekstual dari **Hapus profil**.
2. Sistem menolak akses Guest dan mengarahkan mereka ke login. Pengguna login yang belum melengkapi onboarding tetap dapat membuka dan menyelesaikan penghapusan akunnya.
3. Jika akun berstatus staff atau superuser, sistem menolak alur mandiri dan menjelaskan bahwa akun admin harus ditangani melalui prosedur terpisah. Tidak ada data yang berubah.
4. Halaman konfirmasi menjelaskan bahwa penghapusan permanen dan tidak dapat dibatalkan, serta merangkum data yang dihapus/dipertahankan sebagaimana §4. Jelaskan bahwa media eksternal tidak dapat dihapus oleh Pakelagi.
5. Form meminta username saat ini dan password saat ini. Kedua nilai dibandingkan/divalidasi terhadap akun yang sedang login. Username harus cocok dengan username akun tersebut.
6. Pengiriman form menggunakan POST dan CSRF. Request GET hanya menampilkan halaman konfirmasi dan tidak mengubah state.
7. Jika username/password salah, jangan mengubah data atau sesi; tampilkan pesan umum bahwa konfirmasi gagal dan minta pengguna memeriksa kredensial. Pesan tidak boleh mengungkap apakah username cocok atau akun ada. Batasi hingga 5 konfirmasi gagal per akun dalam jendela 15 menit. Percobaan berikutnya ditolak dengan HTTP 429 sampai jendela berakhir; batas disimpan di database sehingga tidak dapat dilewati dengan mengganti sesi.
8. Jika konfirmasi benar, lakukan penghapusan/perubahan data terkait dalam satu transaksi atomik sejauh didukung oleh penyimpanan yang digunakan. Bila ada langkah yang gagal, batalkan perubahan sehingga akun tidak terhapus sebagian dan sesi tetap aktif; tampilkan pesan kegagalan yang aman.
9. Jika seluruh perubahan berhasil, akhiri sesi pengguna dan cabut seluruh sesi yang terkait dengan akun di semua perangkat. Arahkan ke beranda dalam keadaan logout dan tampilkan pesan bahwa akun telah dihapus.

Rute contoh: `GET/POST /accounts/delete/`. Nama/rute dapat disesuaikan selama perilaku dan kontrol akses yang ditetapkan terpenuhi.

## 4. Cakupan data dan dampak

| Data | Perilaku saat penghapusan akun |
|---|---|
| Akun Django `User` | Hapus secara permanen; termasuk username, email akun, password hash, dan atribut akun lainnya. Username dilepas dan dapat digunakan untuk registrasi baru. |
| Profil | Hapus profil terkait akun. Ini dapat terjadi melalui cascade user→profile, tetapi hasilnya harus dipastikan sebagai bagian dari operasi keseluruhan. |
| Listing | Hapus semua listing yang dimiliki akun, tanpa membedakan status Available, Sold, Hidden, atau status moderasi. Hapus juga record media/referensi gambar yang disimpan Pakelagi. |
| File gambar listing eksternal | Tidak dapat dihapus oleh Pakelagi. Menghapus listing hanya menghapus URL/referensinya dari data Pakelagi; file tetap mengikuti kebijakan penyedia eksternal. |
| Favorite akun yang dihapus | Hapus seluruh favorite yang dibuat akun tersebut. |
| Favorite pengguna lain pada listing akun | Hapus favorite yang merujuk listing yang ikut terhapus, agar tidak ada favorite dengan referensi listing yatim. Jangan menghapus favorite pengguna lain pada listing yang tetap ada. |
| Report yang dibuat akun | Pertahankan report untuk kebutuhan moderasi, tetapi hapus relasi ke akun pelapor dan field identitas terstruktur pelapor. Pertahankan relasi listing hanya bila listing tersebut tidak ikut terhapus; untuk listing yang dihapus, putus relasi listing tanpa menghapus report. |
| Isi bebas report | Pertahankan alasan, deskripsi, status, catatan moderasi, dan waktu yang dibutuhkan untuk jejak moderasi. Jangan menyunting teks bebas secara otomatis; informasi pribadi yang ditulis langsung di dalam teks mungkin tetap tersimpan. |
| Guide/konten yang ditulis akun | Hapus seluruh panduan/konten yang dibuat akun tersebut, baik draft maupun terbit. Hapus relasi/atribusi penulis bersama kontennya. |
| Data terkait lain | Sebelum fitur diimplementasikan, inventarisasi seluruh foreign key dan referensi ke user/listing. Tetapkan perilaku eksplisit untuk setiap relasi; jangan menyisakan referensi yatim atau menyalin identitas ke data yang dipertahankan tanpa kebijakan. |

Sebelum implementasi, skema report harus mendukung retensi tanpa identitas pelapor dan tanpa listing melalui relasi opsional, record arsip/anonymisasi, atau pemodelan setara. Pilihan skema adalah detail implementasi, tetapi report yang dipertahankan tidak boleh memiliki foreign key wajib yang menghalangi penghapusan user/listing.

## 5. UI dan pesan

Halaman konfirmasi harus menggunakan kerangka UI bersama dan aksesibel. Konten minimum:

- Judul langsung: **Hapus akun**.
- Peringatan tegas: **Penghapusan ini permanen dan tidak dapat dibatalkan.**
- Ringkasan: akun/profil, listing, favorite, dan guide yang ditulis akun akan dihapus; report moderasi akan tetap disimpan tanpa relasi identitas pelapor dan akan diputus dari listing jika listing dihapus.
- Penjelasan bahwa file gambar yang disimpan pada layanan eksternal tidak ikut terhapus.
- Input username dan password dengan label jelas. Password bertipe password; jangan pernah mengisi ulang password pada respons form.
- Tombol destruktif dengan label eksplisit seperti **Hapus akun secara permanen**, serta aksi batal yang aman.
- Error konfirmasi bersifat umum dan tidak mengungkap detail autentikasi. Feedback sukses diberikan setelah transaksi berhasil dan sesi berakhir.

Jangan menyamarkan aksi ini sebagai penghapusan profil. Jangan menjanjikan pemulihan akun atau konten setelah sukses.

## 6. Keamanan dan privasi

- Wajib login; target penghapusan selalu user dari sesi server, tidak pernah ID user dari input pengguna atau URL.
- Validasi ulang username dan password pada server tepat sebelum penghapusan. Gunakan mekanisme autentikasi/password Django; jangan membandingkan password plaintext atau menyimpannya.
- Jangan log password, token, atau kredensial yang dikirim. Jangan memasukkan kredensial ke query string, analytics, pesan flash, atau error log.
- Operasi perubahan hanya melalui POST ber-CSRF. GET tidak boleh menghapus, menonaktifkan, atau mengubah data.
- Rate-limit kegagalan konfirmasi dan gunakan pesan umum yang sama untuk username/password yang tidak cocok.
- Cegah akses mandiri staff/superuser di server, bukan hanya menyembunyikan tombol UI.
- Lindungi terhadap pengiriman ulang dan request bersamaan: setelah satu penghapusan berhasil, request lain tidak boleh menghapus akun berbeda atau menjalankan operasi sebagian.
- Jangan menyimpan salinan identitas dalam data yang dipertahankan kecuali telah ditetapkan sebagai kebijakan retensi tersendiri.
- Gunakan transaksi database untuk penghapusan relasional. Jika ada efek eksternal yang tidak dapat dimasukkan ke transaksi, rancang urutan/kompensasi agar tidak menghapus akun sebelum data lokal yang wajib dihapus berhasil ditangani. Tidak ada penghapusan file gambar eksternal dalam lingkup ini.

## 7. Kegagalan dan kondisi tepi

- Username tidak sama dengan username akun aktif, password salah, atau input kosong: gagal dengan pesan umum; semua data dan sesi tetap ada.
- User tidak login: arahkan ke login; jangan mengungkap keberadaan akun target.
- Staff/superuser: tolak tanpa perubahan.
- Profil tidak ada/belum lengkap: akun tetap dapat dihapus; proses tidak boleh gagal hanya karena relasi profil opsional tidak tersedia.
- Listing/report/favorite/guide tidak ada: proses tetap berhasil tanpa asumsi bahwa setidaknya ada data terkait.
- Kegagalan saat menganonimkan report atau menghapus relasi lain: seluruh perubahan database dibatalkan dan akun tidak terhapus.
- Username dipakai kembali setelah penghapusan: akun baru memiliki identitas dan data baru; tidak ada pemulihan atau penggabungan dengan akun lama.

## 8. Rute dan akses

| Aksi | Rute contoh | Metode | Akses |
|---|---|---|---|
| Tampilkan konfirmasi | `/accounts/delete/` | GET | Pemilik yang login, bukan staff/superuser |
| Konfirmasi penghapusan | `/accounts/delete/` | POST + CSRF | Pemilik yang login, bukan staff/superuser; wajib username dan password saat ini |
| Batal | Tautan aman ke area profil/akun | GET | Pemilik yang login |
| Sukses | Beranda | Redirect setelah penghapusan berhasil | Guest/logout |

Rute ini merupakan usulan dan dapat berubah. Izin dan semantik metode HTTP wajib dipertahankan.

## 9. Kriteria penerimaan

Checklist ini tetap merupakan target kontrak penuh; bagian yang memerlukan modul yang belum tersedia belum dapat dinyatakan selesai. Implementasi akun/profil diverifikasi melalui `accounts/test_deletion.py`.

- [ ] Halaman konfirmasi hanya dapat dibuka pengguna yang login; tidak ada penghapusan akun lain melalui manipulasi URL/request.
- [ ] Pengguna yang belum melengkapi profil tetap dapat menghapus akunnya sendiri.
- [ ] Staff dan superuser ditolak baik melalui UI maupun request langsung, tanpa perubahan data.
- [ ] Halaman menjelaskan sifat permanen/tidak dapat dibatalkan dan seluruh dampak data, termasuk batas file gambar eksternal serta report yang dipertahankan.
- [ ] Username saat ini dan password saat ini wajib. Username harus cocok dengan akun sesi; password diverifikasi dengan mekanisme Django.
- [ ] Konfirmasi yang salah memberi error umum, tidak membedakan username/password, tidak mengubah data/sesi, dan percobaan dibatasi.
- [ ] GET tidak mengubah state; POST tanpa CSRF ditolak.
- [ ] Konfirmasi benar menghapus akun Django, profil, semua listing, favorite milik akun, favorite pada listing yang dihapus, dan semua guide yang ditulis akun.
- [ ] Report tetap tersedia untuk moderasi; identitas pelapor terstruktur dihapus; listing yang terhapus dilepas; isi bebas dipertahankan sesuai kebijakan retensi.
- [ ] URL gambar eksternal dihapus dari data Pakelagi; sistem tidak mengklaim menghapus file pada layanan eksternal.
- [ ] Kegagalan pada setiap langkah membatalkan semua perubahan relasional dan akun tetap dapat digunakan.
- [ ] Setelah sukses, username tersedia untuk registrasi baru tanpa mewarisi data lama.
- [ ] Semua sesi akun dicabut, sesi saat ini berakhir, dan pengguna diarahkan ke beranda dengan feedback sukses.
- [ ] Kredensial tidak pernah ditampilkan kembali atau ditulis ke log.
- [ ] Profil tidak tersedia atau koleksi data terkait kosong tidak menyebabkan operasi yang gagal secara keliru.

## 10. Bukan lingkup

- Penghapusan mandiri akun staff/superuser; proses admin terpisah.
- Masa tenggang, soft delete, pemulihan akun, atau pemulihan konten.
- Menghapus file gambar dari host eksternal.
- Menghapus laporan moderasi yang dipertahankan sesuai kebijakan di atas.
- Menghapus favorite pengguna lain pada listing yang tidak ikut terhapus.
- Penghapusan profil saja; alurnya tetap ditentukan oleh spesifikasi profil.

## 11. Catatan implementasi dan dependensi

Pada branch yang didokumentasikan oleh catatan integrasi profil, modul listing/favorite masih berupa adapter kosong. Model Report/Guide dan relasi aktual mungkin belum tersedia. Sebelum implementasi fitur ini, lakukan inventarisasi skema nyata dan tambahkan kebijakan penghapusan/anonymisasi untuk setiap relasi; jangan menganggap tabel atau constraint sudah mendukung kontrak ini.

Implementasi awal menggunakan session store database bawaan Django dan mencabut sesi aktif akun dalam transaksi penghapusan. `AccountDeletionAttempt` menyimpan pembatasan percobaan per akun dan ikut dihapus ketika akun dihapus. Jalankan migrasi sebelum menggunakan fitur. Tidak ada model Listing/Favorite/Report/Guide atau mekanisme penghapusan spekulatif yang ditambahkan. Pencabutan sesi membaca semua sesi database yang belum kedaluwarsa; biayanya bertambah seiring jumlah sesi dan perlu pemetaan sesi-ke-user bila skala meningkat. Penguncian baris akun menggunakan `select_for_update`; pengujian kontensi paralel pada PostgreSQL produksi belum dilakukan (SQLite pengembangan tidak menyediakan semantik row lock yang sama).

Penghapusan sesi lintas perangkat harus didukung oleh konfigurasi/session store yang dipakai. Jika sesi Django tidak menyimpan relasi user yang dapat dicabut dengan andal, tambahkan mekanisme pencabutan sesi atau rotasi/revokasi yang setara sebelum menyatakan kriteria tersebut terpenuhi.
