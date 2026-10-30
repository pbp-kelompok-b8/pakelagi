# Spesifikasi Fitur Akun, Autentikasi, Profil, dan Halaman 404

## 1. Tujuan dan hubungan dengan spesifikasi utama

Dokumen ini merinci pekerjaan untuk area auth dan profile yang menjadi fondasi penggunaan Pakelagi. Spesifikasi produk dan teknis utama di [`../../pakelagi-specification.md`](../../pakelagi-specification.md) tetap menjadi sumber kebenaran untuk domain dan cakupan produk. Bila ada konflik, spesifikasi utama yang berlaku; dokumen ini menjelaskan alur dan kriteria penerimaan fitur ini.

Lingkup terdiri dari:

1. registrasi, login, dan logout menggunakan Django Authentication;
2. onboarding wajib untuk membuat profil setelah registrasi;
3. melihat dan mengubah profil;
4. halaman 404 Not Found bermerek Pakelagi.

Ini adalah dokumen perencanaan, bukan implementasi. Template HTML di direktori `auth-template/`, `profile-template/`, dan `error-template/` merupakan referensi visual; bukan kontrak bahwa semua elemen/fitur yang tergambar harus dibuat.

## 2. Keputusan produk

- Akun MVP menggunakan Django `User` bawaan dan autentikasi username/password.
- Form registrasi meminta username, password, dan konfirmasi password.
- Email akun opsional, belum diverifikasi, dan dapat ditambahkan atau diubah dari area profil/akun. Email akun bukan kontak publik.
- Verifikasi email/nomor telepon, OTP, CAPTCHA, serta layanan pengiriman kode verifikasi tidak termasuk MVP. Nomor telepon opsional boleh disimpan sebagai kontak tanpa klaim verifikasi.
- Avatar dan sampul opsional menggunakan URL HTTPS eksternal, bukan upload file ke Pakelagi. Keputusan URL ini menggantikan rencana upload beserta batas 5 MB/validasi isi file.
- Etalase profil sendiri dan orang lain memakai struktur yang sama; edit dilakukan melalui menu akun menuju `/profile/edit/`.
- Template `auth-verifyphone.html` hanya referensi desain untuk kemungkinan pengembangan mendatang.
- Pengguna baru wajib membuat profil dengan `display_name` sebelum mengakses fitur yang mensyaratkan member. Bio dan field lain tidak diwajibkan untuk menyelesaikan onboarding.
- Profil dan akun adalah konsep berbeda. Menghapus profil tidak menghapus akun. Penghapusan akun bukan MVP; alur dan kebijakan untuk pengembangan mendatang ditetapkan pada [spesifikasi penghapusan akun](account-deletion-specification.md).
- Hanya halaman 404 yang menjadi deliverable error page saat ini.
- Tailwind CSS mengikuti acuan UI pada template project; halaman implementasi menggunakan kerangka bersama Django template.

## 3. Istilah domain

| Istilah | Definisi |
|---|---|
| Guest | Pengunjung yang belum login. |
| User/akun | Identitas Django Authentication yang menyimpan username, password hash, dan email akun opsional. |
| Member | User yang sudah login dan memiliki profil dengan `display_name` terisi. |
| Profil | Data Pakelagi yang terkait one-to-one dengan user; berisi nama tampilan, bio, kota, dan preferensi/nilai kontak. |
| Email akun | Email opsional pada Django `User`; belum diverifikasi dan tidak otomatis terlihat sebagai kontak publik. |
| Kontak penjual (kontak publik terbatas) | Metode utama pada `contact_type`/`contact_value` dan telepon tambahan opsional; hanya terlihat pemilik dan member lengkap, bukan seluruh pengunjung publik. |
| Onboarding profil | Langkah setelah registrasi untuk membuat profil dan mengisi `display_name` sebelum fitur member dibuka. |

## 4. Model data dan aturan field

### 4.1 User Django

- Gunakan model `User` bawaan Django Authentication, tanpa custom user model untuk cakupan ini.
- `username` dan `password` wajib pada registrasi dan autentikasi.
- Password dikonfirmasi saat registrasi dan disimpan menggunakan mekanisme hashing Django, tidak pernah sebagai teks biasa.
- `email` opsional. Pengguna dapat menambah/mengubahnya dari area profil/akun. Pada MVP tidak ada verifikasi email, OTP, atau jaminan bahwa email telah dikonfirmasi.
- Email akun tetap privat dan tidak diperlakukan sebagai `contact_value`.

### 4.2 Profile

Satu user dapat belum memiliki profil selama onboarding, lalu memiliki paling banyak satu profil.

| Field | Aturan |
|---|---|
| `user` | Relasi one-to-one wajib ke Django `User`; keunikan satu profil per user. Penghapusan user menghapus profil terkait melalui cascade. |
| `display_name` | Wajib; satu-satunya field yang harus terisi untuk menyelesaikan onboarding. Ditampilkan sebagai nama member di UI/profil publik. |
| `bio` | Opsional; teks singkat maksimal 500 karakter. |
| `city` | Opsional; kota/area umum saja, bukan alamat rumah. |
| `contact_type` | Opsional; pilihan terkontrol `email`, `instagram`, atau `other` sesuai spesifikasi utama. |
| `contact_value` | Opsional; nilai untuk metode kontak yang dipilih. Bukan field email akun. Tidak boleh memuat alamat rumah. |
| `created_at`, `updated_at` | Timestamp pembuatan dan perubahan profil. |

Avatar, sampul, dan nomor telepon opsional masuk MVP sesuai keputusan produk terbaru. Gambar menggunakan URL eksternal, bukan upload file ke Pakelagi. Status verifikasi nomor telepon tetap di luar MVP; jangan menampilkan badge atau teks “Nomor terverifikasi”.

| Field tambahan | Aturan |
|---|---|
| `avatar_url` | Opsional; URL HTTPS gambar eksternal. Ditampilkan persegi dengan cropping responsif. Kosong atau gagal dimuat memakai placeholder/inisial. |
| `cover_url` | Opsional; URL HTTPS gambar eksternal. Ditampilkan melebar dengan cropping responsif. Kosong atau gagal dimuat memakai latar bawaan. |
| `phone_number` | Opsional; kontak tambahan penjual, terpisah dari `contact_type`/`contact_value`. Disimpan dalam format internasional berawalan `+`, maksimal 15 digit di luar `+`. Hanya pemilik dan member lengkap dapat melihat nilainya. |

#### Validasi field profil

- Trim spasi awal/akhir; `display_name` tidak boleh hanya whitespace, maksimal 150 karakter. Bio maksimal 500 karakter, kota maksimal 100 karakter, dan `contact_value` maksimal 254 karakter.
- `contact_type` dan `contact_value` harus sama-sama kosong atau sama-sama terisi. Keduanya tetap opsional untuk onboarding.
- Instagram menerima handle dengan/tanpa `@` atau URL profil Instagram dan dinormalisasi menjadi handle; tolak URL yang bukan profil Instagram valid.
- Email kontak memakai validator email. `other` merupakan teks biasa yang di-escape, bukan HTML.
- Nomor telepon menerima nomor Indonesia maupun internasional. Awalan lokal `08…` dinormalisasi menjadi `+628…`; format internasional disimpan dengan `+`. Input yang tidak dapat dinormalisasi atau melebihi 15 digit ditolak dengan pesan field yang jelas.
- Validasi nomor hanya memeriksa format, bukan memastikan nomor aktif atau kepemilikan pengguna. Tidak ada OTP, tombol WhatsApp, atau badge verifikasi dalam MVP.

#### Siklus gambar berbasis URL

- Pengguna mengunggah gambar ke layanan eksternal, kemudian menempelkan URL HTTPS pada edit profil. Server Pakelagi hanya memvalidasi URL; tidak mengambil, memproses, atau menyimpan file gambar eksternal.
- Mengganti gambar berarti mengganti URL. Sediakan aksi hapus terpisah untuk avatar dan sampul yang mengosongkan field setelah perubahan berhasil disimpan. Validasi/penyimpanan gagal tidak boleh mengubah URL tersimpan sebelumnya.
- Menghapus profil hanya menghapus referensi URL, bukan file pada layanan eksternal atau gambar listing.
- Batas upload 5 MB dan pemeriksaan isi JPEG/PNG/WebP ditunda sampai upload file menjadi fitur tersendiri; validitas URL tidak membuktikan format, ukuran, atau ketersediaan gambar.
- Browser memuat gambar eksternal; layanan tersebut dapat menerima alamat IP pengunjung. Jelaskan konsekuensi privasi ini pada form edit. Jangan memasukkan kontak privat atau token rahasia ke URL gambar yang tampil publik.

### 4.3 Penghapusan

- Fitur hapus profil tetap bagian dari CRUD profil MVP, meskipun bukan prioritas implementasi tahap pertama.
- Menghapus profil hanya menghapus record profil; akun Django dan listing, favorite, serta report tetap ada.
- Cascade hanya berlaku dari user yang dihapus ke profil terkait. Penghapusan user bukan konsekuensi dari menghapus profil.
- Penghapusan akun adalah aksi terpisah dari penghapusan profil. Implementasi awal mencakup akun Django, profil, pencabutan sesi, dan pembatasan konfirmasi; integrasi modul lain masih tertunda. Alur dan status lengkap mengikuti [spesifikasi penghapusan akun](account-deletion-specification.md).

## 5. Alur pengguna

### 5.1 Registrasi dan onboarding

1. Guest membuka halaman daftar.
2. Guest mengisi username, password, konfirmasi password, dan boleh mengisi email akun opsional.
3. Sistem memvalidasi field, memastikan username unik, dan memvalidasi password menggunakan aturan Django.
4. Jika valid, akun dibuat dengan password hash. Email kosong diperbolehkan; email yang diisi tidak dianggap terverifikasi.
5. Pengguna diautentikasi dan diarahkan ke pembuatan profil.
6. Pengguna mengisi sekurangnya `display_name`. Bio, kota, metode kontak, dan nilai kontak dapat dilewati.
7. Setelah profil berhasil dibuat dengan `display_name`, pengguna dianggap member lengkap dan dapat memakai fitur member.

Jika pengguna meninggalkan onboarding sebelum profil selesai, saat login/permintaan fitur member berikutnya ia tetap diarahkan untuk melengkapi profil. Jangan membuat profil kosong diam-diam yang dianggap lengkap.

### 5.2 Login dan logout

- Guest dapat login menggunakan username dan password.
- Akun tanpa profil lengkap dapat login, tetapi tidak dapat melewati onboarding untuk memakai fitur member.
- Akun dengan profil lengkap dapat kembali ke halaman yang diminta sebelumnya bila aman; bila tidak ada tujuan tersimpan, arahkan ke halaman profil atau beranda sesuai alur navigasi yang disepakati saat implementasi.
- Logout mengakhiri sesi menggunakan alur Django yang aman dan memberi feedback yang sesuai.
- Pesan kesalahan login tidak membocorkan apakah username terdaftar atau tidak.

### 5.3 Melihat dan mengubah profil

- Member dapat membuka etalase profil sendiri dan memperbarui `display_name`, `bio`, `city`, `contact_type`, `contact_value`, `phone_number`, `avatar_url`, `cover_url`, serta email akun opsional melalui `/profile/edit/` dari menu akun di navbar. Etalase bukan form pengelolaan profil/listing.
- Data email akun diedit sebagai atribut Django `User`, bukan disalin ke `Profile` atau otomatis ditampilkan sebagai kontak.
- Member tidak dapat mengubah profil user lain melalui manipulasi URL atau request.
- Tampilan profil publik dan visibilitas listing/contact mengikuti aturan pada spesifikasi utama.
- Penghapusan profil, ketika diimplementasikan, memerlukan konfirmasi dan request POST ber-CSRF; tidak memakai GET. Profil yang dihapus dapat dibuat kembali.

### 5.4 Etalase profil publik dan profil sendiri

`/profile/` dan `/profile/<user_id>/` menggunakan etalase yang sama. Tidak ada daftar Hidden atau form/email akun privat di etalase, termasuk ketika dibuka pemilik. Pengelolaan profil melalui menu akun menuju `/profile/edit/`; pengelolaan seluruh listing sendiri tetap tanggung jawab halaman listing saya.

Urutan konten mengikuti mockup:

1. Header/navbar bersama sesuai status sesi, breadcrumb Beranda / Penjual / nama tampilan.
2. Sampul melebar dan avatar persegi dengan fallback masing-masing.
3. Nama tampilan sebagai judul utama, bio dan kota bila terisi, serta total Dijual dan Terjual.
4. Kartu kontak sesuai akses dan jenis kontak; tidak ada badge verifikasi.
5. Tab Dijual/Terjual dengan hitungan, ringkasan hasil, kontrol urutan, dan grid listing.
6. Tombol pemuatan berikutnya bila masih ada hasil.
7. Cuplikan “Sudah dipakai lagi” hanya pada tab Dijual.
8. Footer bersama, bukan salinan link autentikasi statis dari mockup.

Nama, angka 14/23, merek, harga, kota, serta gambar placeholder pada mockup bukan data tetap. Kota kosong tidak diganti lokasi rekaan. Gambar dekoratif memiliki alt kosong; avatar/gambar barang memiliki teks alternatif yang sesuai. Layout desktop harus menyesuaikan layar kecil tanpa lebar tetap 1440 px atau konten yang terpotong.

### 5.5 Matriks akses etalase

| Konten/aksi | Guest | User login, profil belum lengkap | Member lain | Pemilik dengan profil lengkap |
|---|---|---|---|---|
| Identitas publik, avatar/sampul, kota/bio | Ya | Ya | Ya | Ya |
| Daftar dan hitungan Available/Sold publik | Ya | Ya | Ya | Ya |
| Hidden/hasil moderasi tersembunyi | Tidak | Tidak | Tidak | Tidak di etalase |
| Nilai kontak utama dan telepon | Tidak | Tidak | Ya | Ya |
| Email akun | Tidak | Tidak | Tidak | Hanya di area akun/edit, bukan etalase |
| Tambah favorit Available milik orang lain | Ke login | Ke onboarding | Ya | Bukan untuk listing sendiri |
| Edit profil yang dilihat | Tidak | Tidak | Tidak | Melalui menu akun |

Pemilik yang profilnya belum lengkap membuka `/profile/` diarahkan onboarding. URL publik untuk profil tidak ada atau `display_name` kosong mengembalikan 404 generik, termasuk setelah profil dihapus. Listing yang tetap ada mengikuti kebijakan modul listing; tautan penjual tidak boleh menimbulkan error internal atau membocorkan data profil yang sudah tidak tersedia.

### 5.6 Kartu kontak penjual

- `instagram`: tampilkan handle dengan `@` dan CTA “Hubungi via Instagram” ke URL profil HTTPS yang dibangun dari handle tervalidasi.
- `email`: tampilkan email kontak dan CTA email menggunakan `mailto:`. Jangan mengambil nilai dari email akun secara otomatis.
- `other`: tampilkan teks yang di-escape; buat tautan hanya bila seluruh nilai merupakan URL HTTP/HTTPS valid. Skema berbahaya tidak dijadikan tautan.
- Telepon ditampilkan sebagai teks berlabel “Telepon”, tanpa klaim verifikasi atau tombol WhatsApp.
- Tanpa kontak utama, hilangkan CTA yang tidak tersedia; telepon tetap tampil jika ada. Bila seluruh kontak kosong, tampilkan “Penjual belum menambahkan kontak.”
- Guest mendapat ajakan masuk; user login tanpa profil lengkap mendapat ajakan melengkapi profil, dengan tujuan kembali yang aman. Nilai kontak tidak dikirim ke kedua kelompok ini, bukan sekadar disembunyikan lewat CSS.
- Sertakan penjelasan bahwa kontak hanya terlihat oleh member yang sudah masuk dan transaksi berlangsung di luar Pakelagi. Untuk tautan eksternal tab baru, gunakan perlindungan `noopener noreferrer`.

### 5.7 Tab, hitungan, pengurutan, dan pemuatan

- Tab default **Dijual** memuat hanya `Available`; **Terjual** hanya `Sold`. Keduanya milik pemilik profil yang dilihat. `Hidden` dan listing yang disembunyikan moderator dikecualikan dari daftar, cuplikan, dan hitungan, termasuk untuk pemilik pada etalase.
- Hitungan header/tab adalah total hasil publik per status, bukan jumlah kartu yang sudah dimuat. Ringkasan Dijual dapat memakai “N pakaian menunggu dipakai lagi”; Terjual memakai teks sesuai statusnya.
- Kedua tab memuat **8 barang per pemuatan**, termasuk pemuatan berikutnya. Tombol “Muat N lainnya” memakai N = minimum 8 dan jumlah sisa; tombol tidak ditampilkan bila tidak ada sisa.
- Pilihan urutan: **Terbaru**, **Harga terendah**, **Harga tertinggi**. Default Terbaru berdasarkan waktu publikasi listing menurun, lalu ID menurun. Harga diurutkan sesuai pilihan, dengan ID sebagai pembeda deterministik bila harga sama.
- Simpan tab dan urutan di URL GET; contoh `?tab=dijual&sort=terbaru`, `?tab=terjual&sort=harga_terendah`. Penamaan parameter dapat disesuaikan tanpa mengubah makna. Pergantian tab/urutan memulai daftar dari pemuatan pertama.
- Posisi pagination/pemuatan juga harus dapat dipulihkan lewat URL/riwayat saat kembali dari detail listing; pemuatan parsial tidak boleh menggandakan kartu yang sudah tampil. URL dapat dibagikan dan dibuka langsung tanpa bergantung pada state JavaScript sebelumnya.
- Gunakan HTMX/respons parsial dengan navigasi halaman HTML biasa sebagai fallback tanpa JavaScript. Setiap permintaan menghitung ulang akses/status pada server; tidak menjanjikan snapshot tetap ketika data berubah bersamaan.
- Cuplikan **“Sudah dipakai lagi”** pada tab Dijual berisi maksimal empat listing publik yang paling baru ditandai Sold, dengan ID sebagai pembeda. Tombol **“Lihat N terjual”** membuka tab Terjual, bukan halaman pengelolaan. Pada tab Terjual, jangan ulangi cuplikan tersebut.
- Cuplikan membutuhkan waktu perubahan menjadi Sold dari modul listing, bukan `updated_at` umum yang bisa berubah saat judul diedit. Kontrak integrasi: catat waktu transisi ke Sold; transisi Sold berikutnya menjadi acuan terbaru jika barang sempat kembali Available.

### 5.8 Kartu listing dan favorit

- Gunakan partial kartu bersama: gambar/fallback, brand bila ada, judul, harga Rupiah, ukuran, kondisi, dan kota listing. Klik kartu menuju detail listing; tombol favorit merupakan kontrol terpisah, bukan aksi yang ikut memicu navigasi kartu.
- Sold memiliki badge teks “Terjual” dan pembeda visual yang tetap terbaca; tidak cukup hanya opacity atau warna. Halaman detail Sold mengikuti kebijakan modul listing dan tidak boleh memperlakukannya sebagai barang tersedia.
- Tambah favorit hanya untuk Available milik orang lain. Guest diarahkan login; user login tanpa profil lengkap diarahkan onboarding. Listing sendiri tidak memiliki aksi tambah favorit.
- Perubahan Available menjadi Sold tidak menghapus favorite yang sudah ada. Pada Sold, hanya tampilkan aksi hapus jika member tersebut sudah memfavoritkannya; jangan tampilkan aksi tambah. Favorite tetap privat dan unik per user/listing.
- Setiap aksi memakai POST + CSRF dan memeriksa ulang member, kepemilikan favorite, serta status/visibilitas listing pada server. Bila listing sudah Sold/Hidden saat request tambah diproses, tolak penambahan dan beri feedback; penghapusan favorite milik sendiri tetap diperbolehkan.

### 5.9 Kondisi kosong, loading, dan kegagalan

- Profil valid tanpa barang tetap 200 dengan hitungan nol, bukan 404. Tampilkan pesan khusus tab: “Belum ada barang dijual” atau “Belum ada barang terjual”. Sembunyikan cuplikan dan tautan lihat semua jika tidak ada Sold.
- Saat pemuatan berikutnya berlangsung, beri indikator proses dan cegah pengiriman berulang dari kontrol yang sama. Jika gagal, pertahankan kartu yang sudah tampil dan sediakan coba lagi tanpa menggandakan hasil.
- Gagal memuat avatar/sampul/gambar barang menampilkan fallback, bukan merusak halaman. Fallback tidak memicu loop pemuatan ulang.
- Tampilkan pesan validasi dekat field, pertahankan input yang aman saat form gagal, dan feedback sukses setelah simpan/hapus. Jangan menampilkan detail internal.
- Tab, urutan, pemuatan, dan favorit dapat digunakan dengan keyboard; status aktif dan hasil perubahan dinyatakan secara aksesibel. Gunakan link/button/form semantik, bukan `<div>` interaktif dari mockup.

## 6. Akses dan redirect onboarding

- Halaman publik (misalnya beranda, katalog publik, detail listing yang tersedia, dan halaman 404) tetap dapat dibuka guest maupun member.
- Fitur yang memerlukan member harus mensyaratkan sesi login.
- Jika user belum login, arahkan ke login dengan tujuan kembali yang aman.
- Jika user login tetapi belum memiliki profil atau `display_name` kosong, arahkan ke onboarding profil.
- Pengecualian dari redirect onboarding: halaman publik, halaman login/registrasi yang relevan, onboarding itu sendiri, logout, dan halaman admin yang menggunakan mekanisme akses admin tersendiri.
- Redirect harus mencegah loop, mempertahankan tujuan awal yang aman, dan tidak menerima URL eksternal sembarang sebagai tujuan kembali.
- Keberadaan profil tidak memberikan hak admin; hak admin tetap ditentukan oleh Django permissions/staff status.

## 7. Halaman dan rute yang direncanakan

Rute dapat disesuaikan implementasinya selama perilaku dan batas akses dipenuhi.

| Halaman | Rute contoh | Akses |
|---|---|---|
| Registrasi | `/accounts/register/` | Guest |
| Login | `/accounts/login/` | Guest |
| Logout | `/accounts/logout/` | Member |
| Buat/lengkapi profil | `/profile/create/` | User login tanpa profil lengkap |
| Profil saya | `/profile/` | Member |
| Edit profil | `/profile/edit/` | Pemilik/member |
| Hapus profil | `/profile/delete/` | Pemilik; prioritas lanjutan dalam lingkup MVP |
| Konfirmasi hapus akun | `/accounts/delete/` | Pemilik akun non-staff/non-superuser, termasuk profil belum lengkap |
| Profil publik | `/profile/<user_id>/` | Semua; mengikuti privasi dan aturan listing utama |
| Halaman tidak ditemukan | handler 404 | Semua |

## 8. Halaman 404

- Tampilkan halaman branded Pakelagi ketika route/resource tidak ditemukan.
- Jelaskan secara generik bahwa halaman tidak ditemukan; jangan mengasumsikan semua 404 berasal dari listing yang terjual.
- Sediakan aksi kembali ke beranda dan/atau katalog.
- Rekomendasi listing pada mockup bersifat opsional dan hanya ditampilkan jika data tersedia serta dapat dimuat dengan aman.
- Halaman harus memakai struktur template bersama dan tidak menampilkan traceback, path file, query, atau detail internal.
- 403 dan 500 custom tidak termasuk deliverable saat ini; tetap gunakan penanganan aman bawaan framework pada production.

## 9. UI dan referensi template

Template yang menjadi bahan visual:

- `auth-template/auth-login.html` — referensi tampilan login username/password.
- `auth-template/auth-register.html` — saat ini hanya panel manfaat, belum menunjukkan form; field registrasi ditetapkan oleh dokumen ini.
- `auth-template/auth-verifyphone.html` — mockup masa depan saja, bukan alur MVP.
- `profile-template/profile-edit.html` — referensi field dan preview. Avatar/cover diisi melalui URL HTTPS, nomor telepon tanpa verifikasi; email akun dibedakan dari kontak penjual.
- `profile-template/profile-public(member).html` — referensi etalase untuk member: sampul, avatar, identitas, hitungan, kartu kontak, tab, kartu barang, dan cuplikan Sold. Berlaku juga untuk profil sendiri; variasi akses dijelaskan pada §5.4–5.8. Badge verifikasi dihilangkan, delapan barang per pemuatan menggantikan contoh “Muat 6 lainnya”, dan hati pada Sold hanya tersedia untuk menghapus favorit lama.
- `error-template/error-404.html` — referensi tampilan 404; sesuaikan pesannya agar generik, bukan khusus listing.

Template implementasi mengikuti `base.html`, komponen header/footer, token dan font project, serta Tailwind CSS sesuai spesifikasi utama. Mockup adalah fragmen visual statis; kelas utility yang belum terkonfigurasi, ukuran fixed desktop, placeholder, dan contoh data bukan persyaratan perilaku. UI final tetap harus responsive dan accessible.

## 10. Keamanan, privasi, dan validasi

- Gunakan form dan validator Django; jangan menyimpan password sendiri atau dalam teks biasa.
- Lindungi semua perubahan state dengan CSRF; logout dan operasi hapus tidak boleh menggunakan GET.
- Pastikan kepemilikan profil diverifikasi di server, bukan hanya berdasarkan ID dari URL.
- Gunakan escaping bawaan template untuk bio/nama; jangan menandai input pengguna sebagai HTML aman tanpa sanitasi yang tepat.
- Jangan menampilkan email akun atau `contact_value` kepada guest. Kontak publik mengikuti aturan akses di spesifikasi utama.
- Tolak atau beri peringatan atas input lokasi yang menyerupai alamat rumah; hanya kota/area umum yang diperbolehkan.
- Jangan log password, token, atau nilai sensitif. Pesan autentikasi tidak boleh mengungkap keberadaan akun.
- Terapkan pengaturan production aman: `DEBUG` nonaktif dan secret dari environment, sesuai spesifikasi utama.

## 11. Kriteria penerimaan

### Registrasi dan autentikasi

- [X] Guest dapat membuat akun dengan username, password, dan konfirmasi password yang valid.
- [X] Username duplikat ditolak dengan pesan yang dapat dipahami.
- [X] Password yang tidak memenuhi validator Django atau konfirmasi yang tidak sama ditolak.
- [X] Password tersimpan melalui hashing Django; tidak pernah disimpan plaintext.
- [X] Email akun boleh kosong atau diisi; tidak ada klaim bahwa email telah diverifikasi.
- [X] Guest dapat login dan member dapat logout.
- [X] Respons login gagal tidak membedakan username yang tidak ada dari password yang salah.

### Onboarding dan profil

- [X] Setelah registrasi, user diarahkan ke onboarding profil.
- [X] `display_name` wajib untuk menyelesaikan onboarding; bio, kota, metode/nilai kontak, dan email akun opsional.
- [ ] User tanpa profil lengkap tidak dapat mengakses semua aksi member, termasuk jika mencoba URL langsung; setelah lengkap akses diberikan. Pemeriksaan saat ini diterapkan pada route profil yang ada, belum diverifikasi untuk semua fitur member.
- [X] Halaman publik tetap dapat dibuka dan redirect onboarding tidak menghasilkan loop.
- [X] User dapat melihat dan mengubah profil sendiri, tetapi tidak dapat mengubah profil user lain.
- [X] Email akun tersimpan sebagai field Django User, tetap opsional, tidak terverifikasi, dan bukan kontak publik otomatis.
- [ ] Kontak publik tidak terlihat guest dan tidak boleh berisi alamat rumah. Pembatasan visibilitas sudah diterapkan; validasi alamat hanya berbasis pola dan belum mencakup semua kemungkinan alamat.
- [ ] Menghapus profil tidak menghapus akun, listing, favorite, atau report; penghapusan profil dapat diikuti pembuatan ulang. Fitur hapus profil belum tersedia.
- [ ] Kontrak penuh penghapusan akun mengikuti [spesifikasi penghapusan akun](account-deletion-specification.md); akun/profil telah diimplementasikan, tetapi integrasi modul data terkait belum tersedia.

### Halaman 404

- [X] URL yang tidak ditemukan menampilkan halaman 404 Pakelagi saat `DEBUG=False`; sudah diuji untuk URL dan resource profil yang tidak ditemukan.
- [X] Tersedia navigasi kembali ke beranda, dan test memastikan tautan beranda berfungsi.
- [X] Halaman tidak membocorkan detail internal dan tidak mensyaratkan rekomendasi listing tersedia. Template generik tidak menampilkan rekomendasi; test memeriksa kebocoran detail dengan `DEBUG=False`. Catatan: konfigurasi default masih menetapkan `DEBUG=True` dan `SECRET_KEY` hard-coded, sehingga pengaturan production di `pakelagi/settings.py` tetap harus diperbaiki sebelum deploy.
- [X] Halaman memakai kerangka UI bersama (`base.html`, header, dan footer) serta kelas responsif untuk layar kecil.

### Etalase, gambar, kontak, dan integrasi listing

Checklist ini adalah target pengujian, bukan klaim bahwa implementasi sudah selesai.

Catatan tahap implementasi etalase: modul listing/favorite belum tersedia pada branch ini. Sesuai keputusan cakupan, integrasi sementara menggunakan adapter kosong; kontrak dan pekerjaan lanjutan dicatat pada [`listing-integration.md`](listing-integration.md). Daftar nyata, pagination data, cuplikan Sold, dan favorit belum diimplementasikan dan checklist terkait tetap belum selesai.

- [X] Profil sendiri dan publik memakai etalase sama; menu akun mengarah ke edit milik sendiri dan tidak mengekspos email akun di etalase.
- [X] Profil tidak ada/belum lengkap menghasilkan 404 generik di URL publik; `/profile/` pemilik tanpa profil lengkap menuju onboarding.
- [X] URL avatar/sampul hanya menerima HTTPS; kosong/gagal dimuat memakai fallback. Hapus/ganti URL tidak menghapus file eksternal atau gambar listing.
- [X] Server tidak mengambil gambar eksternal; UI edit menjelaskan risiko privasi alamat IP pada layanan gambar eksternal.
- [X] Field dan batas panjang, pasangan kontak, normalisasi Instagram serta nomor lokal/internasional tervalidasi di server.
- [X] Nomor tampil sebagai “Telepon” tanpa badge verifikasi atau WhatsApp; email kontak tidak diambil otomatis dari email akun.
- [X] Guest dan user belum onboarding tidak menerima kontak/telepon di HTML, atribut, partial HTMX, atau respons data. Ajakan login/onboarding mempertahankan tujuan aman.
- [X] Instagram/email/other menghasilkan CTA yang sesuai; kontak kosong dan nomor-saja memiliki fallback yang benar.
- [ ] Semua permukaan etalase mengecualikan Hidden/moderasi, termasuk hitungan dan cuplikan serta ketika pemilik membukanya.
- [ ] Dijual default, Terjual terpisah; hitungan total sesuai status, bukan jumlah kartu termuat.
- [ ] Kedua tab memuat 8 barang, label sisa tepat, serta tombol hilang pada akhir daftar; uji 0, 1, 8, 9, dan lebih dari 16 hasil.
- [ ] Urutan terbaru/harga deterministik; tab, urutan, dan posisi pemuatan dapat dipulihkan lewat URL/riwayat dan bekerja tanpa JavaScript.
- [ ] Cuplikan maksimal empat Sold berdasarkan waktu transisi Sold, hanya pada tab Dijual; tautan menuju tab Terjual.
- [ ] Favorit hanya dapat ditambahkan untuk Available milik orang lain; request langsung tetap diperiksa dan favorite tidak duplikat.
- [ ] Favorite lama pada Sold tetap ada dan dapat dihapus pemilik; tidak ada aksi tambah pada Sold/listing sendiri.
- [ ] Perubahan status bersamaan diperiksa ulang pada daftar dan aksi; kegagalan pemuatan mempertahankan kartu dan dapat dicoba ulang.
- [ ] Layout kecil, keyboard, alt text, status tab, loading, empty state, dan feedback memenuhi aksesibilitas dasar.

## 12. Bukan lingkup saat ini

- Verifikasi email atau nomor telepon.
- OTP, CAPTCHA, integrasi Firebase, SMS/email provider, dan pemilihan layanan pengiriman OTP.
- Pemulihan/reset password kecuali bila nanti ditetapkan sebagai bagian terpisah dari autentikasi.
- Upload file gambar ke Pakelagi, penyimpanan/pemrosesan gambar di server, serta jaminan ukuran/format file eksternal. Avatar dan cover berbasis URL HTTPS termasuk MVP.
- Verifikasi kepemilikan nomor telepon, badge “Nomor terverifikasi”, dan integrasi WhatsApp.
- Implementasi penghapusan akun; rancangan perilakunya dicatat pada [spesifikasi penghapusan akun](account-deletion-specification.md).
- Halaman custom 403/500.
- Implementasi front-end terpisah dengan React; aplikasi tetap menggunakan Django Templates.

## 13. Urutan implementasi yang disarankan

1. Sepakati dan implementasikan form registrasi/login/logout memakai Django auth.
2. Implementasikan model/form pembuatan profil sesuai field utama.
3. Implementasikan redirect onboarding dan pembatasan fitur member di server.
4. Implementasikan tampilan profil/edit dan pengelolaan email akun opsional dengan privasi yang tepat.
5. Implementasikan 404 branded dan fallback yang aman.
6. Tambahkan test autentikasi, izin, validasi, onboarding, privasi, dan 404.
7. Integrasikan alur ini dengan listing, favorite, report, dan modul member lainnya.
