# Memperbarui spesifikasi profile member berdasarkan template HTML

**Session ID:** ses_eb72cc19fffe3Q7HwUJv3AxY4A
**Created:** 10/17/2026, 2:46:06 PM
**Updated:** 10/17/2026, 4:21:05 PM

---

## User

@grill-with-docs Ada file template @docs/feat/profile/profile-template/profile-public(member).html yang menampilkan bagaimana user bisa melihat profilenya dan oranglain juga bisa melihatnya sebagai member. Update dokumentasi dan spesifikasi yang sudah ada pada @docs/feat/profile/profile-specification.md agar lebih detail dan menyeluruh. 

---

## Assistant

Saya sudah memeriksa template, spesifikasi utama, dan implementasi profil saat ini. Sebelum memperbarui dokumen, ada beberapa keputusan produk yang perlu dipastikan agar **detail mockup tidak otomatis dianggap sebagai kewajiban MVP**.

Aturan yang sudah jelas dan tidak perlu diputuskan ulang:
- Profil publik dapat dibuka guest; kontak hanya untuk **member yang sudah menyelesaikan onboarding**.
- Profil publik menampilkan listing **Available/Dijual dan Sold/Terjual**, bukan Hidden.
- Email akun tetap privat dan berbeda dari kontak penjual.
- Angka, nama, dan produk dalam template adalah contoh data.

Berikut putaran pertama keputusan yang akan menentukan rincian spesifikasi.

❓ **Q1 — Batas cakupan mockup:** Template memiliki avatar, foto sampul, dan label “Nomor terverifikasi”, sedangkan dokumen saat ini secara eksplisit mengecualikan ketiganya dari MVP. Apakah batas ini tetap dipertahankan, atau Anda ingin memperluas cakupan produk?

➡️ **Rekomendasi:** Pertahankan batas MVP. Adaptasi struktur profil, kontak, dan daftar barang dari template; gunakan tampilan tanpa avatar/cover dan jangan tampilkan klaim verifikasi. Jika ingin memasukkan avatar/cover, kita perlu membahas perubahan model dan spesifikasi utama juga.

---

❓ **Q2 — Profil sendiri versus profil orang lain:** Saat member membuka profilnya sendiri, apakah halaman ini menjadi **etalase publik dengan tambahan aksi pemilik**, atau sekaligus halaman pengelolaan listing yang juga menampilkan Hidden?

Contoh: Nina memiliki 14 barang Dijual, 23 Terjual, dan 2 Hidden. Apakah profilnya sendiri tetap memperlihatkan hanya 14 dan 23, dengan pengelolaan 2 Hidden dilakukan di halaman lain?

➡️ **Rekomendasi:** Gunakan etalase yang sama untuk diri sendiri dan pengunjung lain, dengan tambahan tombol **Edit profil** dan akses ke **Kelola listing** bagi pemilik. Hidden tidak muncul pada etalase maupun hitungan publik. Form/email akun privat tetap berada di area edit, bukan di etalase.

---

❓ **Q3 — Hubungan tab dan bagian “Sudah dipakai lagi”:** Mockup menampilkan tab Dijual/Terjual sekaligus cuplikan Terjual di bawah daftar Dijual. Apakah kedua mekanisme ini ingin dipertahankan?

➡️ **Rekomendasi:** Pertahankan keduanya dengan aturan:
- Tab **Dijual** aktif secara default, menampilkan daftar Available.
- Di bawahnya terdapat cuplikan maksimal empat listing Sold.
- Tombol **Lihat N terjual** membuka tab Terjual.
- Tab **Terjual** menampilkan daftar Sold lengkap yang dipaginasi, tanpa mengulang cuplikan tersebut.

---

❓ **Q4 — Tombol favorit:** Apakah ikon hati pada kartu barang menjadi fungsi wajib di profil publik? Jika ya, apakah pengunjung boleh memfavoritkan barang Sold dan barang miliknya sendiri?

Ini belum diputuskan oleh spesifikasi utama; ikon hati pada barang Sold di mockup belum cukup menjadi aturan produk.

➡️ **Rekomendasi:** Wajibkan favorit untuk listing **Available milik orang lain**. Guest diarahkan login dan user yang belum lengkap diarahkan onboarding. Jangan sediakan aksi tambah favorit pada Sold atau listing sendiri. Favorit yang sudah ada ketika barang berubah menjadi Sold tidak dihapus otomatis; pengguna tetap dapat menghapus favorit tersebut.

---

❓ **Q5 — Cakupan penyuntingan dokumen:** Permintaan Anda menunjuk `docs/feat/profile/profile-specification.md`. Apakah perubahan cukup di file itu, atau boleh menyelaraskan `docs/pakelagi-specification.md` jika keputusan baru menambahkan aturan lintas fitur?

➡️ **Rekomendasi:** Utamakan file spesifikasi profil. Ubah spesifikasi utama **hanya jika diperlukan untuk mencegah konflik**, terutama jika cakupan avatar/cover atau kebijakan favorit diperluas.

---

Silakan jawab **Q1–Q5**; boleh singkat seperti “semua sesuai rekomendasi, kecuali …”. Setelah itu saya akan mendalami aturan yang bergantung pada jawaban tersebut—termasuk pemuatan daftar, kontak, dan kondisi kosong/error—sebelum meminta konfirmasi akhir dan menyunting dokumen.

---

## User

1. Update batas MVP, bisa diberikan ya harus menyesuaikan dengan mock up yang sudah ada. Untuk nomor telepon hanya ditaruh saja tanpa adanya verifikasi, fitur verifikasinya nanti akan diimplementasikan.
2. Gunakan etalase yang sama untuk diri sendiri dan pengunjung lain, untuk bagian edit nanti akan dihubungkan dengan profile/edit yang ada navbar account untuk mengeditnya.
3.Pertahankan keduanya dengan aturan:
Tab Dijual aktif secara default, menampilkan daftar Available.
Di bawahnya terdapat cuplikan maksimal empat listing Sold.
Tombol Lihat N terjual membuka tab Terjual.
Tab Terjual menampilkan daftar Sold lengkap yang dipaginasi, tanpa mengulang cuplikan tersebut. 
4.Wajibkan favorit untuk listing Available milik orang lain. Guest diarahkan login dan user yang belum lengkap diarahkan onboarding. Jangan sediakan aksi tambah favorit pada Sold atau listing sendiri. Favorit yang sudah ada ketika barang berubah menjadi Sold tidak dihapus otomatis; pengguna tetap dapat menghapus favorit tersebut. 
5.Utamakan file spesifikasi profil. Ubah spesifikasi utama hanya jika diperlukan untuk mencegah konflik, terutama jika cakupan avatar/cover atau kebijakan favorit diperluas. 

---

## Assistant

Baik. Keputusan berikut sudah disepakati:

- **Avatar dan foto sampul masuk MVP**, mengikuti arah visual mockup.
- **Nomor telepon masuk MVP tanpa verifikasi**. Label “Nomor terverifikasi” tidak boleh ditampilkan; verifikasi merupakan pengembangan berikutnya.
- Profil sendiri dan profil orang lain menggunakan **etalase yang sama**. Pengeditan melalui menu akun di navbar menuju `/profile/edit/`, bukan form di etalase.
- Tab Dijual/Terjual dan cuplikan maksimal empat barang Sold mengikuti aturan yang Anda setujui.
- Favorit hanya dapat ditambahkan pada Available milik orang lain; favorit lama pada Sold tetap dapat dihapus.
- Penyuntingan berfokus pada spesifikasi profil, dengan penyesuaian spesifikasi utama seperlunya.

Ada beberapa keputusan turunan agar dokumentasinya benar-benar bisa dijadikan acuan implementasi.

---

❓ **Q6 — Sumber avatar dan sampul:** Apakah pengguna mengunggah gambar dari perangkat, atau mengisi URL gambar? Apakah gambar wajib untuk menyelesaikan onboarding?

➡️ **Rekomendasi:** Gunakan **upload gambar opsional** melalui edit profil; onboarding tetap hanya mewajibkan `display_name`. Avatar kosong menggunakan placeholder/inisial, sampul kosong menggunakan latar bawaan. Batasi setiap file maksimal **5 MB**, format JPEG/PNG/WebP, validasi isi gambar di server, dan tolak SVG. Avatar ditampilkan persegi dan sampul melebar dengan cropping responsif; angka dimensi pada mockup bukan ukuran upload wajib.

---

❓ **Q7 — Privasi dan fungsi nomor telepon:** Nomor telepon ini dimaksudkan sebagai informasi privat pemilik akun, atau kontak tambahan penjual yang dapat dilihat member lain? Apakah perlu tombol WhatsApp?

Ini perlu dibedakan dari `contact_type`, yang saat ini hanya mengenal email, Instagram, dan other.

➡️ **Rekomendasi:** Tambahkan `phone_number` opsional sebagai **kontak tambahan penjual**, terpisah dari metode kontak utama. Hanya pemilik dan member lengkap yang dapat melihatnya; guest tidak menerima nilainya. Tampilkan sebagai teks **“Telepon”**, tanpa badge verifikasi dan tanpa tombol WhatsApp pada MVP. Nomor tidak wajib dan tidak mengubah syarat onboarding.

---

❓ **Q8 — Jumlah barang dan pengurutan:** Mockup menampilkan delapan barang awal lalu “Muat 6 lainnya”. Apakah pola ini ingin dijadikan aturan, dan apakah “Urutkan: Terbaru” merupakan kontrol yang benar-benar bisa diubah?

➡️ **Rekomendasi:** Gunakan **8 barang per pemuatan**, termasuk pemuatan berikutnya, untuk kedua tab. Tombol berbunyi **“Muat N lainnya”**, dengan N maksimal delapan sesuai sisa data. Sediakan pilihan **Terbaru, Harga terendah, Harga tertinggi**; default Terbaru berdasarkan waktu publikasi listing, dengan urutan ID sebagai pembeda jika sama. Cuplikan Sold menampilkan empat barang yang paling baru ditandai terjual. Tab dan pengurutan tersimpan pada URL agar dapat dibagikan dan dipulihkan saat kembali dari detail barang.

---

❓ **Q9 — Perilaku kartu kontak:** Bagaimana kartu Instagram pada mockup diadaptasi ketika penjual memilih email, other, atau belum mengisi kontak?

➡️ **Rekomendasi:**
- **Instagram:** tampilkan handle dan tautan HTTPS ke profil Instagram.
- **Email kontak:** tampilkan alamat kontak dan tombol `mailto:`.
- **Other:** tampilkan teks kontak; hanya jadikan tautan jika berupa URL HTTP/HTTPS yang valid.
- **Tanpa kontak utama:** sembunyikan CTA yang tidak tersedia; jika ada nomor telepon, nomor tetap ditampilkan.
- **Tanpa semua kontak:** tampilkan “Penjual belum menambahkan kontak.”
- **Guest:** tampilkan ajakan login tanpa mengirim nilai kontak melalui HTML, atribut, atau respons data.
- **User login belum onboarding:** tampilkan ajakan melengkapi profil.
- Tetap tampilkan keterangan bahwa transaksi berlangsung di luar Pakelagi.

---

❓ **Q10 — Profil yang tidak tersedia:** Jika akun belum menyelesaikan onboarding atau pemilik sudah menghapus profil, apakah URL profil publik menampilkan halaman kosong, atau 404? Listing akun tersebut bisa saja masih ada karena hapus profil tidak menghapus listing.

➡️ **Rekomendasi:** URL profil publik mengembalikan **404 generik** untuk profil yang tidak ada atau belum lengkap. Listing tetap mengikuti kebijakan visibilitas modul listing; tautan profil penjual tidak boleh menyebabkan error internal. Pemilik yang membuka `/profile/` diarahkan membuat/melengkapi profil kembali. Profil yang valid tetapi belum mempunyai barang tetap tampil, dengan hitungan nol dan pesan kosong per tab.

---

Silakan jawab **Q6–Q10**. Jika mengikuti rekomendasi, cukup sebutkan demikian; khusus nomor telepon, mohon pastikan apakah memang boleh dilihat member lain karena itu merupakan keputusan privasi.

---

## User

6. Gunakan upload gambar opsional melalui edit profil; onboarding tetap hanya mewajibkan display_name. Avatar kosong menggunakan placeholder/inisial, sampul kosong menggunakan latar bawaan. Batasi setiap file maksimal 5 MB, format JPEG/PNG/WebP, validasi isi gambar di server, dan tolak SVG. Avatar ditampilkan persegi dan sampul melebar dengan cropping responsif; angka dimensi pada mockup bukan ukuran upload wajib. 
7. Tambahkan phone_number opsional sebagai kontak tambahan penjual, terpisah dari metode kontak utama. Hanya pemilik dan member lengkap yang dapat melihatnya; guest tidak menerima nilainya. Tampilkan sebagai teks “Telepon”, tanpa badge verifikasi dan tanpa tombol WhatsApp pada MVP. Nomor tidak wajib dan tidak mengubah syarat onboarding. 
8. Gunakan 8 barang per pemuatan, termasuk pemuatan berikutnya, untuk kedua tab. Tombol berbunyi “Muat N lainnya”, dengan N maksimal delapan sesuai sisa data. Sediakan pilihan Terbaru, Harga terendah, Harga tertinggi; default Terbaru berdasarkan waktu publikasi listing, dengan urutan ID sebagai pembeda jika sama. Cuplikan Sold menampilkan empat barang yang paling baru ditandai terjual. Tab dan pengurutan tersimpan pada URL agar dapat dibagikan dan dipulihkan saat kembali dari detail barang. 
9. Instagram: tampilkan handle dan tautan HTTPS ke profil Instagram.
Email kontak: tampilkan alamat kontak dan tombol mailto:.
Other: tampilkan teks kontak; hanya jadikan tautan jika berupa URL HTTP/HTTPS yang valid.
Tanpa kontak utama: sembunyikan CTA yang tidak tersedia; jika ada nomor telepon, nomor tetap ditampilkan.
Tanpa semua kontak: tampilkan “Penjual belum menambahkan kontak.”
Guest: tampilkan ajakan login tanpa mengirim nilai kontak melalui HTML, atribut, atau respons data.
User login belum onboarding: tampilkan ajakan melengkapi profil.
Tetap tampilkan keterangan bahwa transaksi berlangsung di luar Pakelagi. 
10. URL profil publik mengembalikan 404 generik untuk profil yang tidak ada atau belum lengkap. Listing tetap mengikuti kebijakan visibilitas modul listing; tautan profil penjual tidak boleh menyebabkan error internal. Pemilik yang membuka /profile/ diarahkan membuat/melengkapi profil kembali. Profil yang valid tetapi belum mempunyai barang tetap tampil, dengan hitungan nol dan pesan kosong per tab. 

---

## Assistant

Q6–Q10 sudah jelas dan saya catat sebagai keputusan spesifikasi. Ada tiga aturan turunan terakhir yang perlu dikunci sebelum penyuntingan.

---

❓ **Q11 — Mengganti dan menghapus gambar:** Apakah pemilik dapat menghapus avatar/sampul tanpa menggantinya? Bagaimana nasib file lama setelah gambar diganti atau profil dihapus?

➡️ **Rekomendasi:** Sediakan aksi hapus terpisah untuk avatar dan sampul pada edit profil. Setelah dihapus, gunakan fallback bawaan. File lama dibersihkan setelah perubahan berhasil disimpan, selama tidak digunakan lagi; kegagalan validasi atau penyimpanan tidak boleh menghilangkan gambar sebelumnya. Penghapusan profil juga membersihkan gambar profil, tetapi tidak menghapus gambar listing.

---

❓ **Q12 — Validasi nomor dan pasangan kontak:** Apakah nomor telepon dibatasi ke Indonesia? Bagaimana jika pengguna memilih Instagram tetapi tidak mengisi handle, atau mengisi kontak tanpa memilih jenisnya?

➡️ **Rekomendasi:**
- Terima nomor Indonesia maupun internasional; normalisasi ke format internasional berawalan `+`. Awalan lokal `08…` dianggap nomor Indonesia dan dinormalisasi menjadi `+628…`.
- Validasi hanya memeriksa format, **bukan membuktikan nomor aktif atau dimiliki pengguna**.
- `contact_type` dan `contact_value` harus sama-sama kosong atau sama-sama terisi.
- Instagram menerima handle dengan/tanpa `@` atau URL profil Instagram, lalu dinormalisasi menjadi handle.
- Email kontak divalidasi sebagai email; `other` berupa teks biasa dengan escaping, bukan HTML.
- Batas field: `display_name` 150 karakter, `bio` 500, `city` 100, dan `contact_value` 254. Nomor tersimpan maksimal 15 digit di luar tanda `+`.

---

❓ **Q13 — Konsistensi daftar saat status berubah:** Misalnya sebuah barang menjadi Hidden setelah halaman pertama dimuat, atau berubah menjadi Sold sebelum tombol favorit ditekan. Apakah daftar/hitungan boleh tetap mengandalkan data lama di browser?

➡️ **Rekomendasi:** Setiap permintaan daftar dan aksi favorit memeriksa ulang status serta izin di server. Hitungan merupakan total listing publik per status, bukan jumlah kartu yang sudah dimuat; Hidden dan listing yang disembunyikan moderator selalu dikecualikan. Barang yang sudah tidak memenuhi syarat tidak boleh ditambahkan ke favorit. Jika pemuatan berikutnya gagal, kartu yang sudah tampil tetap ada dan pengguna dapat mencoba lagi. Sediakan navigasi halaman biasa sebagai fallback ketika JavaScript tidak tersedia.

---

Jika **Q11–Q13 sesuai rekomendasi**, mohon sekaligus konfirmasikan bahwa keseluruhan keputusan Q1–Q13 sudah menjadi pemahaman bersama dan saya boleh mulai menyunting dokumentasi.

Hasil penyuntingan akan mencakup:
- spesifikasi profil yang lebih menyeluruh: model, matriks akses, etalase, upload, kontak, tab/pemuatan, kondisi kosong/error, keamanan, dan kriteria penerimaan;
- penyesuaian minimum pada spesifikasi utama untuk field baru dan aturan favorit;
- glosarium domain di `CONTEXT.md` sesuai alur skill yang Anda minta.

**Tidak ada perubahan kode implementasi atau template HTML dalam pekerjaan ini.**

---

## User

1. Sediakan aksi hapus terpisah untuk avatar dan sampul pada edit profil. Setelah dihapus, gunakan fallback bawaan. File lama dibersihkan setelah perubahan berhasil disimpan, selama tidak digunakan lagi; kegagalan validasi atau penyimpanan tidak boleh menghilangkan gambar sebelumnya. Penghapusan profil juga membersihkan gambar profil, tetapi tidak menghapus gambar listing. atau sementara buat dia itu dalam link aja sehingga dia itu bsa mudah untuk di upload dan di apus.
2. Terima nomor Indonesia maupun internasional; normalisasi ke format internasional berawalan +. Awalan lokal 08… dianggap nomor Indonesia dan dinormalisasi menjadi +628….
Validasi hanya memeriksa format, bukan membuktikan nomor aktif atau dimiliki pengguna.
contact_type dan contact_value harus sama-sama kosong atau sama-sama terisi.
Instagram menerima handle dengan/tanpa @ atau URL profil Instagram, lalu dinormalisasi menjadi handle.
Email kontak divalidasi sebagai email; other berupa teks biasa dengan escaping, bukan HTML.
Batas field: display_name 150 karakter, bio 500, city 100, dan contact_value 254. Nomor tersimpan maksimal 15 digit di luar tanda +. 
3. Setiap permintaan daftar dan aksi favorit memeriksa ulang status serta izin di server. Hitungan merupakan total listing publik per status, bukan jumlah kartu yang sudah dimuat; Hidden dan listing yang disembunyikan moderator selalu dikecualikan. Barang yang sudah tidak memenuhi syarat tidak boleh ditambahkan ke favorit. Jika pemuatan berikutnya gagal, kartu yang sudah tampil tetap ada dan pengguna dapat mencoba lagi. Sediakan navigasi halaman biasa sebagai fallback ketika JavaScript tidak tersedia. 

---

## Assistant

Aturan validasi kontak/nomor telepon dan konsistensi daftar sudah disepakati. Namun, tambahan **“sementara buat dalam link saja”** mengubah keputusan upload gambar sebelumnya, jadi perlu dipastikan satu hal terakhir.

❓ **Q14 — Gambar melalui URL atau upload file:** Apakah untuk MVP avatar dan sampul cukup menggunakan **URL gambar yang diisi pada edit profil**, sehingga Pakelagi tidak menerima atau menyimpan file upload?

➡️ **Rekomendasi: Ya, gunakan URL gambar untuk MVP**, dengan aturan:
- Field opsional `avatar_url` dan `cover_url`, hanya menerima URL HTTPS.
- Pengguna mengunggah gambar ke layanan eksternal, lalu menempelkan tautannya di edit profil.
- Mengganti gambar cukup mengganti URL; menghapus gambar cukup mengosongkan field melalui aksi hapus masing-masing.
- Menghapus profil hanya menghapus referensi URL, **bukan file pada layanan eksternal**.
- URL kosong atau gambar gagal dimuat menggunakan placeholder/inisial untuk avatar dan latar bawaan untuk sampul.
- Server Pakelagi tidak mengambil atau memproses gambar dari URL tersebut. Karena itu, batas **5 MB dan validasi isi JPEG/PNG/WebP tidak dijanjikan pada MVP berbasis URL**; aturan tersebut ditunda sampai upload file diimplementasikan.
- Dokumentasi mencatat bahwa layanan gambar eksternal dapat menerima alamat IP pengunjung ketika gambar dimuat.

**Apakah pendekatan URL ini yang Anda maksud?** Jika ya, sekaligus konfirmasikan saya boleh mulai menyunting spesifikasi profil, menyelaraskan spesifikasi utama seperlunya, dan menambahkan glosarium `CONTEXT.md`—tanpa mengubah kode atau template HTML.

---

## User

14. Ya, gunakan URL gambar untuk MVP, dengan aturan:
Field opsional avatar_url dan cover_url, hanya menerima URL HTTPS.
Pengguna mengunggah gambar ke layanan eksternal, lalu menempelkan tautannya di edit profil.
Mengganti gambar cukup mengganti URL; menghapus gambar cukup mengosongkan field melalui aksi hapus masing-masing.
Menghapus profil hanya menghapus referensi URL, bukan file pada layanan eksternal.
URL kosong atau gambar gagal dimuat menggunakan placeholder/inisial untuk avatar dan latar bawaan untuk sampul.
Server Pakelagi tidak mengambil atau memproses gambar dari URL tersebut. Karena itu, batas 5 MB dan validasi isi JPEG/PNG/WebP tidak dijanjikan pada MVP berbasis URL; aturan tersebut ditunda sampai upload file diimplementasikan.
Dokumentasi mencatat bahwa layanan gambar eksternal dapat menerima alamat IP pengunjung ketika gambar dimuat. 

---

## Assistant

Saya akan menerapkan keputusan final berbasis URL gambar, memperinci perilaku etalase dan kriteria penerimaannya, serta menyelaraskan aturan lintas modul di spesifikasi utama. Template HTML yang ada tidak akan diubah.

---

## Assistant

Dokumentasi sudah diperbarui sesuai keputusan diskusi, termasuk keputusan akhir **gambar berbasis URL, bukan upload file**.

### File yang diperbarui
- **`docs/feat/profile/profile-specification.md`**
  - Field avatar, sampul, telepon, batas panjang, dan validasi kontak.
  - Struktur etalase yang sama untuk profil sendiri dan orang lain.
  - Matriks akses guest, user belum onboarding, member, dan pemilik.
  - Kartu kontak, tab Dijual/Terjual, delapan barang per pemuatan, pengurutan, serta cuplikan Sold.
  - Aturan favorit, kondisi kosong/error, fallback gambar, aksesibilitas, dan checklist penerimaan.

- **`docs/pakelagi-specification.md`**
  - Penyelarasan field profil, privasi kontak, dan kebijakan favorit.
  - Kebutuhan waktu transisi `sold_at` untuk mengurutkan cuplikan barang terjual.

- **`CONTEXT.md`**
  - Glosarium akun, member, profil, etalase, kontak penjual, status listing, dan favorite.

**Kode implementasi dan template HTML tidak diubah.** Checklist baru merupakan target pengujian, bukan klaim implementasi selesai.

Validasi `git diff --check` lolos tanpa kesalahan whitespace; hanya ada peringatan normalisasi line ending LF/CRLF.
