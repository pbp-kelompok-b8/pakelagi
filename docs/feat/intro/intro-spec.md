# Spesifikasi Intro Pembuka Pakelagi

## Status

Spesifikasi fitur. Belum diimplementasikan.

## Tujuan

Menampilkan intro visual singkat saat pengguna pertama kali membuka situs dalam satu sesi tab, sebelum menampilkan halaman yang diminta. Intro memperkenalkan suasana Pakelagi melalui delapan frame foto editorial, indikator progres, dan layar logo penutup.

## Cakupan

Dokumen ini menetapkan perilaku dan aset intro. Mockup acuan berada di `docs/feat/intro/Intro-template/` dan gambar yang akan digunakan sudah tersedia di `static/intro/`.

Implementasi harus memakai gambar lokal tersebut. Jangan mengambil foto listing secara dinamis.

## Istilah

- **Sesi tab**: masa penggunaan tab browser yang sama, dicatat menggunakan `sessionStorage` dengan key `pakelagi_intro`.
- **Frame foto**: satu komposisi visual yang menampilkan foto belakang dan foto depan secara bersamaan.
- **Halaman tujuan**: URL yang diminta pengguna sebelum intro dimulai.

## Perilaku pengguna

1. Pada pembukaan pertama situs dalam satu sesi tab, tampilkan intro sebelum halaman tujuan.
2. Tampilkan delapan frame foto secara berurutan, masing-masing selama 180 ms. Setiap frame merupakan potong langsung (hard cut), tanpa transisi antarframe. Durasi urutan foto adalah 1.44 detik (sekitar 1.5 detik).
3. Setelah frame foto kedelapan, tampilkan layar logo terracotta selama 600 ms.
4. Larutkan layar logo ke halaman tujuan selama 600 ms. Keseluruhan intro berlangsung sekitar 2.64 detik tanpa interaksi pengguna.
5. Tandai intro sebagai sudah ditampilkan pada sesi tab tersebut. Navigasi selanjutnya pada tab yang sama langsung menampilkan halaman tujuan tanpa intro. Tab baru memiliki sesi sendiri.
6. Pertahankan halaman tujuan awal. Contohnya, bila pengguna pertama kali membuka URL halaman produk, intro berakhir ke halaman produk itu, bukan mengalihkan pengguna ke Beranda.
7. Lewati intro segera jika pengguna melakukan salah satu tindakan ini:
   - klik atau tap di area intro;
   - melakukan scroll;
   - menekan `Escape`;
   - mengaktifkan kontrol **Lewati intro**.
8. Sediakan kontrol **Lewati intro** yang terlihat, dapat difokuskan, dan dapat dioperasikan dengan keyboard.
9. Bila `prefers-reduced-motion: reduce` aktif, jangan tampilkan animasi intro; langsung tampilkan halaman tujuan dan catat intro sebagai sudah ditangani untuk sesi tersebut.
10. Bila aset foto gagal dimuat atau `sessionStorage` tidak tersedia/gagal diakses, jangan mengunci atau menunda konten. Lewati intro dan tampilkan halaman tujuan. Kegagalan penyimpanan tidak boleh menyebabkan halaman gagal dimuat.

## Urutan frame dan progres

Angka progres mengikuti mockup. Setiap nilai ditampilkan dalam format bertanda kurung siku, misalnya `[ 08 ]`. Garis progres di tepi bawah mengikuti nilai persentase tersebut; pada frame terakhir mencapai 100%.

| Frame | Progres | Aset foto belakang | Aset foto depan |
|---|---:|---|---|
| 01 | 08 | `static/intro/Intro — 01/Photo — back.png` | `static/intro/Intro — 01/Photo — front.png` |
| 02 | 21 | `static/intro/Intro — 02/Photo — back.jpeg` | `static/intro/Intro — 02/Photo — front.png` |
| 03 | 34 | `static/intro/Intro — 03/Photo — back.png` | `static/intro/Intro — 03/Photo — front.png` |
| 04 | 47 | `static/intro/Intro — 04/Photo — back.png` | `static/intro/Intro — 04/Photo — front.png` |
| 05 | 63 | `static/intro/Intro — 05/Photo — back.png` | `static/intro/Intro — 05/Photo — front.png` |
| 06 | 78 | `static/intro/Intro — 06/Photo — back.png` | `static/intro/Intro — 06/Photo — front.png` |
| 07 | 91 | `static/intro/Intro — 07/Photo — back.png` | `static/intro/Intro — 07/Photo — front.png` |
| 08 | 100 | `static/intro/Intro — 08/Photo — back.png` | `static/intro/Intro — 08/Photo — front.png` |

Semua enam belas foto harus dimuat dan siap ditampilkan sebelum urutan frame dimulai. Gunakan aset lokal, bukan URL placeholder dari mockup. Jika satu atau lebih foto gagal dimuat, lewati seluruh intro.

## Arahan visual

- Gunakan mockup `intro-01.html` sampai `intro-08.html` sebagai acuan komposisi: bidang latar terang, wordmark Pakelagi di kiri atas, progres di kanan atas, sepasang foto bertumpuk di tengah, dan garis progres tipis di tepi bawah.
- Gunakan `intro-end.html` sebagai acuan susunan layar logo penutup.
- Jika warna mockup berbeda dari deskripsi fitur, gunakan **terracotta** untuk indikator progres dan layar penutup. Warna amber pada mockup bukan acuan warna untuk elemen tersebut.
- Pertahankan rasio gambar dan komposisi foto; gunakan pemotongan gambar yang sesuai agar tidak meregangkan aset.
- Tampilan harus menyesuaikan ukuran viewport, tidak menyebabkan scroll horizontal, dan menempatkan kontrol lewati pada area yang mudah ditemukan.

## Aksesibilitas

- Kontrol **Lewati intro** dapat diakses melalui urutan fokus keyboard dan memiliki label yang jelas.
- Hormati preferensi `prefers-reduced-motion`; intro tidak ditampilkan ketika preferensi tersebut aktif.
- Penghitung progres dan garis progres harus menyampaikan progres yang sama. Implementasi perlu menyediakan semantik progres yang dapat dipahami teknologi bantu tanpa menyebabkan pembacaan berulang yang mengganggu pada setiap pergantian cepat.
- Hindari menjebak fokus di intro. Setelah intro dilewati atau selesai, fokus dan interaksi harus tersedia pada halaman tujuan.

## Kriteria penerimaan

- [ ] Pembukaan pertama dalam satu sesi tab menampilkan delapan pasangan foto lokal sesuai urutan tabel.
- [ ] Tiap frame foto tampil 180 ms, berpindah dengan hard cut, dan memperlihatkan nilai progres yang cocok dengan tabel.
- [ ] Semua aset dimuat sebelum frame pertama dimulai; kegagalan pemuatan aset melewati intro.
- [ ] Garis progres terracotta berada di tepi bawah dan mencapai lebar penuh pada progres 100.
- [ ] Frame penutup menampilkan logo pada layar terracotta selama 600 ms, lalu dissolve 600 ms ke halaman tujuan awal.
- [ ] Intro tampil sekali per sesi tab; navigasi berikutnya pada tab yang sama tidak mengulang intro.
- [ ] Klik/tap, scroll, `Escape`, dan kontrol keyboard-accessible **Lewati intro** masing-masing dapat melewati intro dan menampilkan halaman tujuan.
- [ ] Dengan reduced motion, intro dilewati tanpa animasi dan halaman tujuan tetap dapat digunakan.
- [ ] Bila `sessionStorage` tidak tersedia, aplikasi tetap membuka halaman tujuan tanpa error atau terhalang intro.
- [ ] Layout berfungsi pada viewport sempit maupun lebar tanpa scroll horizontal, dan kontrol lewati tetap dapat ditemukan.

## Di luar cakupan

- Mengubah atau mengganti sembilan mockup HTML.
- Menambah, mengubah, atau mengoptimalkan foto di `static/intro/`.
- Mengambil gambar listing terbaru atau membangun pemilihan foto dinamis.
- Mengubah perilaku autentikasi maupun onboarding profil member.
