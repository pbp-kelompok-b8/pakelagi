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
- Verifikasi email, verifikasi nomor telepon, OTP, CAPTCHA, serta layanan pengiriman kode verifikasi belum diputuskan dan tidak termasuk MVP.
- Template `auth-verifyphone.html` hanya referensi desain untuk kemungkinan pengembangan mendatang.
- Pengguna baru wajib membuat profil dengan `display_name` sebelum mengakses fitur yang mensyaratkan member. Bio dan field lain tidak diwajibkan untuk menyelesaikan onboarding.
- Profil dan akun adalah konsep berbeda. Menghapus profil tidak menghapus akun. Penghapusan akun beserta listing/data terkait adalah fitur mendatang, bukan MVP.
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
| Kontak publik | Data pada `contact_type` dan `contact_value`; hanya ditampilkan kepada member login sesuai aturan privasi spesifikasi utama. |
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
| `bio` | Opsional; teks singkat. Batas panjang belum ditentukan oleh spesifikasi utama; jangan menganggap angka pada mockup sebagai keputusan domain. |
| `city` | Opsional; kota/area umum saja, bukan alamat rumah. |
| `contact_type` | Opsional; pilihan terkontrol `email`, `instagram`, atau `other` sesuai spesifikasi utama. |
| `contact_value` | Opsional; nilai untuk metode kontak yang dipilih. Bukan field email akun. Tidak boleh memuat alamat rumah. |
| `created_at`, `updated_at` | Timestamp pembuatan dan perubahan profil. |

Avatar URL, foto sampul toko, nomor telepon, status verifikasi, dan atribut toko tambahan pada mockup tidak masuk model/lingkup MVP karena tidak ditetapkan pada spesifikasi utama.

### 4.3 Penghapusan

- Fitur hapus profil tetap bagian dari CRUD profil MVP, meskipun bukan prioritas implementasi tahap pertama.
- Menghapus profil hanya menghapus record profil; akun Django dan listing, favorite, serta report tetap ada.
- Cascade hanya berlaku dari user yang dihapus ke profil terkait. Penghapusan user bukan konsekuensi dari menghapus profil.
- Penghapusan akun yang kelak menghapus listing dan data terkait memerlukan alur dan kebijakan tersendiri; tidak diimplementasikan atau dijanjikan oleh fitur ini.

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

- Member dapat membuka profil sendiri dan memperbarui `display_name`, `bio`, `city`, `contact_type`, `contact_value`, serta email akun opsional.
- Data email akun diedit sebagai atribut Django `User`, bukan disalin ke `Profile` atau otomatis ditampilkan sebagai kontak.
- Member tidak dapat mengubah profil user lain melalui manipulasi URL atau request.
- Tampilan profil publik dan visibilitas listing/contact mengikuti aturan pada spesifikasi utama.
- Penghapusan profil, ketika diimplementasikan, memerlukan konfirmasi dan request POST ber-CSRF; tidak memakai GET. Profil yang dihapus dapat dibuat kembali.

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
- `profile-template/profile-edit.html` — referensi tampilan field inti dan preview. Nomor telepon terverifikasi, avatar, dan cover diabaikan untuk MVP. Email akun harus dibedakan dari kontak publik.
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

- [ ] Guest dapat membuat akun dengan username, password, dan konfirmasi password yang valid.
- [ ] Username duplikat ditolak dengan pesan yang dapat dipahami.
- [ ] Password yang tidak memenuhi validator Django atau konfirmasi yang tidak sama ditolak.
- [ ] Password tersimpan melalui hashing Django; tidak pernah disimpan plaintext.
- [ ] Email akun boleh kosong atau diisi; tidak ada klaim bahwa email telah diverifikasi.
- [ ] Guest dapat login dan member dapat logout.
- [ ] Respons login gagal tidak membedakan username yang tidak ada dari password yang salah.

### Onboarding dan profil

- [ ] Setelah registrasi, user diarahkan ke onboarding profil.
- [ ] `display_name` wajib untuk menyelesaikan onboarding; bio, kota, metode/nilai kontak, dan email akun opsional.
- [ ] User tanpa profil lengkap tidak dapat mengakses aksi member, termasuk jika mencoba URL langsung; setelah lengkap akses diberikan.
- [ ] Halaman publik tetap dapat dibuka dan redirect onboarding tidak menghasilkan loop.
- [ ] User dapat melihat dan mengubah profil sendiri, tetapi tidak dapat mengubah profil user lain.
- [ ] Email akun tersimpan sebagai field Django User, tetap opsional, tidak terverifikasi, dan bukan kontak publik otomatis.
- [ ] Kontak publik tidak terlihat guest dan tidak boleh berisi alamat rumah.
- [ ] Menghapus profil tidak menghapus akun, listing, favorite, atau report; penghapusan profil dapat diikuti pembuatan ulang.
- [ ] Penghapusan akun massal beserta listing tidak tersedia dalam MVP.

### Halaman 404

- [ ] URL yang tidak ditemukan menampilkan halaman 404 Pakelagi.
- [ ] Tersedia navigasi kembali ke beranda/katalog.
- [ ] Halaman tidak membocorkan detail internal dan tidak mensyaratkan rekomendasi listing tersedia.
- [ ] Halaman mengikuti kerangka UI bersama dan berfungsi pada layar kecil.

## 12. Bukan lingkup saat ini

- Verifikasi email atau nomor telepon.
- OTP, CAPTCHA, integrasi Firebase, SMS/email provider, dan pemilihan layanan pengiriman OTP.
- Pemulihan/reset password kecuali bila nanti ditetapkan sebagai bagian terpisah dari autentikasi.
- Foto/avatar, cover toko, upload gambar, atau field tambahan yang hanya terlihat di mockup.
- Penghapusan akun beserta listing dan data terkait.
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
