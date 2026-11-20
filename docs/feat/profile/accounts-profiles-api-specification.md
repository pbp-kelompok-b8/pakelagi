# Spesifikasi API Akun dan Profil (DRF)

## 1. Tujuan dan status

Dokumen ini mendefinisikan **kontrak API JSON yang diusulkan** untuk perilaku akun dan profil yang saat ini sudah diimplementasikan di aplikasi Django. Dokumen ini menjadi acuan spesifikasi, bukan pernyataan bahwa API DRF sudah tersedia.

Saat dokumen dibuat, `accounts/` dan `profiles/` masih memakai Django views, forms, session authentication, dan template HTML. Django REST Framework belum terpasang/terdaftar di konfigurasi proyek dan belum ada serializer maupun endpoint JSON untuk modul-modul ini. Rute API di bawah adalah kontrak baru yang perlu diimplementasikan terpisah.

Spesifikasi ini dibatasi pada fungsi yang ada di `accounts/` dan `profiles/`: registrasi, login/logout, penghapusan akun, onboarding profil, pengelolaan profil sendiri, dan data profil publik. Perilaku HTML yang ada tetap dipertahankan.

### Sumber perilaku

- `accounts/urls.py`, `accounts/views.py`, `accounts/forms.py`, `accounts/services.py`
- `profiles/urls.py`, `profiles/views.py`, `profiles/forms.py`, `profiles/models.py`, `profiles/access.py`, `profiles/profile_contacts.py`, `profiles/storefront.py`, `profiles/validators.py`
- Tes di `accounts/test_*.py` dan `profiles/test_*.py`
- Glosarium domain di [`../../../CONTEXT.md`](../../../CONTEXT.md)

Bila spesifikasi API ini menyebut **kontrak API**, artinya keputusan JSON yang diusulkan di sini. Bila menyebut **perilaku sekarang**, artinya perilaku yang telah diperiksa pada implementasi HTML dan tes saat ini.

## 2. Batas cakupan dan terminologi

- **Akun** adalah identitas Django User untuk login; **Profil** adalah identitas tampilan yang terkait one-to-one dengan akun.
- **Guest** belum login.
- **Member** adalah user yang sudah login dan memiliki profil dengan `display_name` terisi setelah di-trim. Login saja tidak otomatis menjadikan user Member.
- **Email akun** adalah email privat, opsional, dan belum diverifikasi. Email akun berbeda dari metode kontak `contact_type=email`.
- **Kontak penjual** (`contact_type`, `contact_value`, dan `phone_number`) hanya diberikan kepada pemilik profil atau Member lain yang login dan profilnya lengkap.

API ini tidak menggantikan atau mengubah rute HTML yang ada. API tidak mendefinisikan endpoint listing, upload gambar, penghapusan profil, perubahan password, reset password, verifikasi email/telepon, atau autentikasi token.

## 3. Konvensi umum API

### Base path dan format

- Prefix: `/api/v1/`.
- Request dan response menggunakan JSON (`Content-Type: application/json`).
- Tanggal/waktu response menggunakan ISO 8601 dengan zona waktu, dalam UTC.
- ID user pada profil publik adalah primary key Django User, sama seperti parameter `user_id` rute publik HTML sekarang.
- Request ke method yang tidak didukung mengembalikan `405 Method Not Allowed`.

### Autentikasi dan CSRF

- Gunakan session cookie Django; endpoint API tidak menerima bearer token.
- Semua operasi yang mengubah state, termasuk registrasi, login, logout, pembuatan/edit profil, dan penghapusan akun, wajib dilindungi CSRF. Klien browser mengirim cookie sesi dan token CSRF dengan cara yang didukung aplikasi.
- DRF harus dikonfigurasi agar respons API untuk request tanpa autentikasi berupa JSON, bukan redirect ke halaman login. Kontrak status untuk autentikasi yang diwajibkan adalah `401`.
- Penegakan CSRF untuk login anonim perlu dipastikan secara eksplisit pada implementasi API. Jangan mengasumsikan `SessionAuthentication` saja otomatis memeriksa CSRF pada request login yang belum terautentikasi.
- CSRF tidak valid/missing: `403` dengan format error JSON umum.

### Bentuk error

Semua error API menggunakan bentuk konsisten berikut:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Periksa kembali data yang dikirim.",
    "fields": {
      "display_name": ["Field ini wajib diisi."]
    }
  }
}
```

`fields` hanya disertakan jika ada error per-field. Pesan kredensial login dan konfirmasi penghapusan tidak boleh membedakan apakah username tidak ditemukan, password salah, atau akun tidak aktif. Respons tidak boleh memuat password, password hash, token autentikasi, atau detail database.

Status error utama:

| Status | Makna |
|---|---|
| `400` | JSON/input tidak valid atau validasi field gagal. |
| `401` | Login gagal dengan pesan generik, atau endpoint yang memerlukan login diakses tanpa sesi. |
| `403` | Sesi tidak berhak melakukan aksi, akun staff/superuser mencoba hapus mandiri, atau CSRF gagal. |
| `404` | Profil publik tidak ada atau belum memiliki nama tampilan. |
| `405` | HTTP method tidak didukung. |
| `409` | Operasi pembuatan profil dikirim ketika profil sudah lengkap. |
| `429` | Batas konfirmasi penghapusan akun tercapai. |
| `500` | Kegagalan server/database yang tidak dapat dipulihkan; respons tidak membocorkan detail internal. |

Perbedaan dari HTML saat ini: sejumlah validasi form HTML dirender ulang dengan status `200`, dan kegagalan `DatabaseError` saat hapus akun juga dirender dengan `200`. API menggunakan status JSON di atas; kontrak status API ini belum diterapkan.

## 4. Endpoint

### 4.1 Registrasi akun

`POST /api/v1/accounts/register/`

Akses: Guest. Request yang valid membuat akun Django User, memulai session login, dan menandai akun belum lengkap profilnya.

Request:

```json
{
  "username": "nina.arum",
  "email": "nina@example.com",
  "password": "contoh-password-kuat",
  "password_confirmation": "contoh-password-kuat"
}
```

- `username`: wajib, unik, maksimal 150 karakter, mengikuti validasi username Django.
- `email`: opsional; bila tidak diberikan dianggap string kosong. Bila diberikan harus merupakan email valid. Email tidak diverifikasi dan bukan kontak publik.
- `password` dan `password_confirmation`: wajib dan harus cocok. Password melewati password validators Django yang aktif di settings: similarity terhadap atribut user, panjang minimum, kata sandi umum, dan kata sandi numerik.
- Password hanya disimpan menggunakan hash Django; jangan mengembalikannya.
- User baru tidak diberi hak staff atau superuser.
- Registrasi valid langsung membuat sesi login sebagaimana implementasi sekarang.
- Registrasi oleh user yang sudah login ditolak dengan `403` (`already_authenticated`); tidak membuat akun lain.

Response berhasil: `201 Created`.

```json
{
  "account": {
    "id": 42,
    "username": "nina.arum",
    "email": "nina@example.com"
  },
  "profile_complete": false,
  "next": "/api/v1/profiles/"
}
```

`400` untuk field invalid, termasuk username duplikat, password tidak cocok, atau password gagal divalidasi. Kesalahan username duplikat ditampilkan sebagai error field `username` tanpa membocorkan data akun yang sudah ada.

### 4.2 Login

`POST /api/v1/accounts/login/`

Akses: Guest. Mengautentikasi dengan username/password dan membuat session login Django. Akun nonaktif atau kredensial salah menghasilkan pesan yang sama.

Request:

```json
{
  "username": "nina.arum",
  "password": "contoh-password-kuat"
}
```

Response berhasil: `200 OK`.

```json
{
  "account": {
    "id": 42,
    "username": "nina.arum",
    "email": "nina@example.com"
  },
  "profile_complete": false,
  "next": "/api/v1/profiles/"
}
```

Untuk Member lengkap, `profile_complete` bernilai `true` dan `next` bernilai `"/api/v1/profiles/me/"`. Untuk akun yang sudah login dan mengirim endpoint login lagi, API mengembalikan data sesi/akun saat ini (`200`) tanpa mencoba mengganti sesi.

Kredensial salah atau akun nonaktif: `401`.

```json
{
  "error": {
    "code": "invalid_credentials",
    "message": "Username atau kata sandi salah."
  }
}
```

Jangan menerima atau memproses redirect `next` URL dari klien API. API mengembalikan action lokal berdasarkan kelengkapan profil, bukan URL eksternal.

### 4.3 Logout

`POST /api/v1/accounts/logout/`

Akses: sesi login atau Guest. Logout mengakhiri sesi Django yang sedang digunakan. Seperti logout sekarang, request Guest juga sukses. Endpoint tidak menghapus akun atau sesi perangkat lain.

Response: `204 No Content`, tanpa body.

### 4.4 Onboarding / pembuatan profil

`POST /api/v1/profiles/`

Akses: sesi login. Endpoint membuat profil yang belum ada atau melengkapi profil yang ada tetapi belum lengkap. Profil dianggap lengkap hanya jika `display_name` tidak kosong setelah whitespace awal/akhir di-trim. Jika profil sudah lengkap, response `409` (`profile_already_complete`); edit profil lengkap menggunakan `PATCH /api/v1/profiles/me/`.

Request contoh:

```json
{
  "display_name": "Nina Arum",
  "bio": "Mencari rumah baru untuk pakaian preloved.",
  "city": "Depok",
  "avatar_url": "https://images.example.com/nina.jpg",
  "cover_url": "https://images.example.com/cover.jpg",
  "phone_number": "081234567890",
  "contact_type": "instagram",
  "contact_value": "@Nina.Arum",
  "email": "nina@example.com"
}
```

Request onboarding adalah pengiriman penuh seperti form onboarding: `display_name` wajib; field opsional yang tidak dikirim dianggap kosong. `email` opsional dan bila tidak disertakan dianggap kosong pada pengiriman onboarding penuh. Penyimpanan profil dan perubahan email akun harus atomik, seperti `ProfileForm.save()` saat ini.

Response:

- `201 Created` jika record profil baru dibuat.
- `200 OK` jika record profil belum lengkap sebelumnya lalu berhasil dilengkapi.
- Bentuk response sukses sama seperti `GET /api/v1/profiles/me/`.
- `400` bila validasi gagal; tidak boleh terjadi perubahan parsial pada profil atau email akun.
- `401` tanpa sesi login.
- `409` bila profil sudah lengkap.

### 4.5 Baca dan edit profil sendiri

`GET /api/v1/profiles/me/` — akses: Member lengkap; mengembalikan profil pemilik dan email akun privat.

`PATCH /api/v1/profiles/me/` — akses: Member lengkap; mengedit profil milik sesi saat ini saja. Tidak menerima user ID untuk memilih target.

User login dengan profil belum lengkap diarahkan secara konseptual ke onboarding API; untuk API, responsnya `403` (`profile_incomplete`) dengan `next: "/api/v1/profiles/"` dan tidak ada redirect HTML.

Contoh response `GET` dan `PATCH` berhasil (`200 OK`):

```json
{
  "profile": {
    "user_id": 42,
    "display_name": "Nina Arum",
    "bio": "Mencari rumah baru untuk pakaian preloved.",
    "city": "Depok",
    "avatar_url": "https://images.example.com/nina.jpg",
    "cover_url": "https://images.example.com/cover.jpg",
    "phone_number": "+6281234567890",
    "contact_type": "instagram",
    "contact_value": "nina.arum",
    "created_at": "2026-11-18T10:15:00Z",
    "updated_at": "2026-11-18T10:20:00Z"
  },
  "account": {
    "username": "nina.arum",
    "email": "nina@example.com"
  }
}
```

`PATCH` bersifat parsial:

- Field yang tidak dikirim tidak berubah.
- String kosong pada field opsional mengosongkan field itu.
- `email` pada PATCH opsional; bila tidak dikirim tidak berubah, bila dikirim string kosong mengosongkan email akun.
- Email akun dan perubahan profil disimpan atomik.
- `remove_avatar: true` mengosongkan `avatar_url`; `remove_cover: true` mengosongkan `cover_url`. Aksi remove menang atas nilai URL yang dikirim bersamaan. Aksi penghapusan gambar independen dan hanya tersimpan jika seluruh PATCH valid.
- `remove_avatar` dan `remove_cover` adalah flag aksi PATCH, bukan field yang disimpan di model atau dikembalikan pada response.
- `user_id`, `username`, timestamp, atau ID user target tidak dapat diubah melalui PATCH.

`401` tanpa autentikasi; `403` jika profil belum lengkap; `400` jika validasi field gagal. Nilai field yang tidak dikirim tidak direset saat error atau saat PATCH parsial lainnya.

### 4.6 Baca profil publik

`GET /api/v1/profiles/{user_id}/`

Akses: Guest atau user login. Endpoint mengembalikan identitas profil publik untuk profil dengan `display_name` terisi. Profil yang tidak ada atau nama tampilannya kosong mengembalikan `404` yang sama.

Contoh response untuk Guest atau user login yang belum menjadi Member:

```json
{
  "profile": {
    "user_id": 42,
    "display_name": "Nina Arum",
    "bio": "Mencari rumah baru untuk pakaian preloved.",
    "city": "Depok",
    "avatar_url": "https://images.example.com/nina.jpg",
    "cover_url": "https://images.example.com/cover.jpg"
  },
  "contact": null
}
```

Contoh `contact` bagi pemilik atau Member lengkap:

```json
{
  "profile": {
    "user_id": 42,
    "display_name": "Nina Arum",
    "bio": "Mencari rumah baru untuk pakaian preloved.",
    "city": "Depok",
    "avatar_url": "https://images.example.com/nina.jpg",
    "cover_url": "https://images.example.com/cover.jpg"
  },
  "contact": {
    "type": "instagram",
    "value": "nina.arum",
    "url": "https://www.instagram.com/nina.arum/",
    "phone_number": "+6281234567890"
  }
}
```

- Nilai kontak dan nomor telepon tidak dikirim kepada Guest atau user login yang profilnya belum lengkap; response menggunakan `"contact": null`, bukan mengirim nilainya lalu menyembunyikannya di UI.
- Email akun tidak pernah ada di response profil publik, termasuk saat pemilik sendiri membaca URL publik.
- Untuk audiens berhak, `contact` bernilai `null` bila metode kontak utama dan nomor telepon sama-sama kosong. Jika hanya telepon yang ada, `type`, `value`, dan `url` bernilai `null` sementara `phone_number` terisi.
- `value` adalah nilai kontak tervalidasi/ternormalisasi yang disimpan (misalnya handle Instagram tanpa `@`); tautan aman hanya diberikan bila tersedia. Email kontak dapat diberi URL `mailto:`. Kontak `other` hanya mendapat URL jika nilainya URL HTTP/HTTPS valid tanpa kredensial; teks biasa tetap berupa teks.
- Respons harus memakai `Cache-Control: private, no-store` karena isinya bergantung pada cookie/identitas viewer, mengikuti kebijakan storefront saat ini.

Tidak ada kemampuan edit profil orang lain, walaupun caller mengubah `user_id` pada URL; URL publik bersifat read-only.

## 5. Field dan validasi profil

Field profil yang dapat ditulis dan batas yang diterapkan implementasi sekarang:

| Field | Aturan saat ini |
|---|---|
| `display_name` | Wajib untuk pembuatan/pelengkapan profil; maksimal 150 karakter; whitespace awal/akhir di-trim; nilai whitespace saja tidak menyelesaikan onboarding. |
| `bio` | Opsional; maksimal 500 karakter. |
| `city` | Opsional; maksimal 100 karakter; validator menolak pola kata/nomor yang menyerupai alamat rumah. Ini pemeriksaan pola, bukan jaminan bahwa setiap alamat rumah dapat dikenali. |
| `avatar_url`, `cover_url` | Opsional; maksimal 2048 karakter; hanya HTTPS eksternal valid, tanpa kredensial URL. Host localhost/internal dan alamat IP non-global ditolak. Server hanya memvalidasi URL dan tidak mengambil file. |
| `phone_number` | Opsional; maksimal 16 karakter tersimpan; awalan lokal `08…` dinormalisasi menjadi `+62…`; format hasil harus `+` diikuti 2–15 digit dengan digit pertama bukan nol. Tidak memverifikasi kepemilikan/keaktifan nomor. |
| `contact_type` | Opsional; hanya `email`, `instagram`, atau `other`. |
| `contact_value` | Opsional; maksimal 254 karakter; harus kosong/terisi bersama `contact_type`. Validator juga menolak pola alamat rumah. |
| `email` (request akun) | Opsional dan privat; email akun Django, bukan bagian model Profile dan bukan kontak publik. Tidak diverifikasi. |

Validasi kontak:

- `instagram`: menerima handle valid dengan/ tanpa `@` atau URL profil Instagram di `instagram.com`/`www.instagram.com`; tidak menerima URL post, path lain, query/fragment, kredensial, atau handle invalid. Nilai dinormalisasi menjadi lowercase handle.
- `email`: `contact_value` harus email valid. Ini tetap berbeda dari email akun.
- `other`: teks biasa diperbolehkan. Jika nilai berupa URL, hanya skema HTTP/HTTPS; URL dengan kredensial ditolak. Skema seperti `javascript:`, `data:`, dan `vbscript:` ditolak.
- Nomor `08…` diubah menjadi `+62…`; nomor internasional yang valid disimpan dalam bentuk `+…`.

Validasi pembuatan akun menggunakan `UserCreationForm` Django saat ini. API harus menerapkan validasi ekuivalen dari username/password Django, termasuk keunikan username, konfirmasi password, dan seluruh password validators yang aktif. Pesan error API boleh berupa format JSON terstruktur, tetapi aturan validasi tidak boleh lebih longgar.

## 6. Penghapusan akun

`POST /api/v1/accounts/delete/`

Akses: user login mana pun yang bukan staff/superuser; profil lengkap tidak disyaratkan. Tidak ada `GET` destruktif dan target selalu akun dari sesi saat ini, bukan ID dari body atau URL.

Request:

```json
{
  "username": "nina.arum",
  "password": "kata-sandi-saat-ini"
}
```

Perilaku yang harus dipertahankan dari `delete_confirmed_account()`:

1. Memeriksa ulang username dan password akun yang login.
2. Username salah, password salah, atau field kosong/malformed dihitung sebagai kegagalan dengan pesan generik yang sama; tidak membocorkan faktor mana yang salah.
3. Lima kegagalan dicatat per akun di database. Request berikutnya ditolak `429` sampai jendela 15 menit sejak awal periode berakhir; percobaan tidak bisa dilewati dengan mengganti sesi/perangkat. Request yang membuka kembali setelah jendela berakhir memulai hitungan baru.
4. Keberhasilan menghapus secara permanen akun Django dan profil terkait (cascade), mencabut sesi database aktif milik akun di semua perangkat, dan mengakhiri sesi peminta.
5. User staff atau superuser tidak dapat menghapus akun mandiri: `403`, tanpa perubahan.
6. Penghapusan menggunakan transaksi. Jika operasi database gagal, perubahan dibatalkan, akun dan sesi tetap ada, dan error aman dikembalikan.

Response:

- Berhasil: `204 No Content` tanpa body.
- Tidak login: `401`.
- Staff/superuser: `403` (`self_deletion_forbidden`).
- Konfirmasi invalid: `400` dengan error generik `confirmation_failed`.
- Percobaan terkunci: `429` (`confirmation_throttled`); boleh menyertakan `Retry-After` detik yang tersisa, tanpa membuka informasi kredensial.
- Kegagalan database: `500` dengan pesan aman, tanpa detail internal.

Cakupan yang benar-benar dilakukan implementasi saat ini adalah akun Django, profil, dan sesi aktif terkait. Jangan menyatakan API ini menghapus listing, favorite, report, guide, ataupun file gambar di penyedia eksternal; integrasi tersebut tidak dilakukan oleh implementasi `accounts/` dan tercatat belum termasuk di [spesifikasi penghapusan akun](account-deletion-specification.md).

## 7. Storefront profil: perilaku HTML yang sudah ada, bukan kontrak JSON

API profil publik di §4.6 **tidak** menambahkan array listing atau mendefinisikan schema kartu listing. Storefront yang sudah ada tetap merupakan halaman HTML/HTMX pada route `/profile/` dan `/profile/<user_id>/`; bagian ini dicantumkan sebagai konteks perilaku yang telah terimplementasi, bukan endpoint API DRF.

Perilaku halaman HTML saat ini:

- Query `tab`: `dijual` atau `terjual`, default `dijual`; nilai tidak valid kembali ke default.
- Query `sort`: `terbaru`, `harga_terendah`, atau `harga_tertinggi`, default `terbaru`; nilai tidak valid kembali ke default.
- Query `page`: bilangan positif, default 1; nilai invalid/kurang dari 1 menjadi 1 dan batas maksimal yang diproses adalah 500.
- Daftar hanya memuat status listing Available/Sold; Hidden dan hasil moderasi yang disembunyikan tidak masuk daftar, hitungan, atau cuplikan, termasuk ketika dibuka pemilik.
- Hitungan Available/Sold adalah total publik, terpisah dari jumlah kartu yang dimuat. Pemuatan 8 item per halaman bersifat kumulatif: `page=3` memuat hingga 24 item awal.
- Pengurutan terbaru memakai `created_at` menurun lalu ID menurun; harga naik/turun memakai ID sebagai pemecah seri deterministik.
- Tab Dijual menampilkan cuplikan hingga 4 item Sold terbaru menurut `sold_at` lalu ID; tab Terjual tidak mengulang cuplikan.
- HTML storefront menggunakan `private, no-store` dan memvariasikan respons berdasarkan header HX dan Cookie.

Detail query/filter tersebut tidak menjadi jaminan response JSON ataupun endpoint listing di bawah `/api/v1/`.

## 8. Pemetaan ke route HTML yang ada

| API baru yang dispesifikasikan | Route HTML sekarang | Catatan |
|---|---|---|
| `POST /api/v1/accounts/register/` | `GET/POST /accounts/register/` | HTML membuat sesi dan redirect ke onboarding. |
| `POST /api/v1/accounts/login/` | `GET/POST /accounts/login/` | HTML merender form dan redirect berdasarkan keamanan `next`/kelengkapan profil. |
| `POST /api/v1/accounts/logout/` | `POST /accounts/logout/` | HTML logout session dan redirect; Guest juga dapat POST. |
| `POST /api/v1/accounts/delete/` | `GET/POST /accounts/delete/` | GET HTML hanya konfirmasi; POST HTML menghapus. API hanya menyediakan POST. |
| `POST /api/v1/profiles/` | `GET/POST /profile/create/` | HTML membuat/melengkapi profil dan redirect. |
| `GET /api/v1/profiles/me/` | `GET /profile/` | HTML storefront pemilik mensyaratkan Member lengkap. |
| `PATCH /api/v1/profiles/me/` | `GET/POST /profile/edit/` | HTML mengubah profil sendiri dan email akun dalam satu transaksi. |
| `GET /api/v1/profiles/{user_id}/` | `GET /profile/<user_id>/` | HTML publik 404 bila profil tidak ada/nama tampilan kosong. |

API dan halaman HTML hidup berdampingan; menambah API tidak mengubah URL HTML atau semantiknya.

## 9. Di luar cakupan / belum diimplementasikan

- DRF dependency, konfigurasi, serializer, views, routes, OpenAPI, dan tes kontrak API.
- Endpoint `DELETE /profiles/me/` atau penghapusan profil. Tidak ada route penghapusan profil pada modul saat ini meskipun konsep penghapusan profil disebut dokumen produk.
- Endpoint listing/storefront JSON; field kartu listing, filter API, pagination response API, dan endpoint listing.
- Token/JWT, OAuth, verifikasi email/telepon, OTP, CAPTCHA, registrasi social, perubahan/reset password.
- Penghapusan atau modifikasi listing/favorite/report/guide sebagai efek penghapusan akun.
- Upload atau penghapusan file gambar eksternal.
- Perilaku CORS dan klien non-browser. Implementasi harus ditetapkan sesuai kebutuhan sebelum API diakses lintas origin.

## 10. Checklist penerimaan per modul

Checklist berikut adalah kriteria penerimaan untuk implementasi API yang direncanakan. Kotak yang belum dicentang bukan penanda status implementasi saat ini; endpoint DRF belum tersedia.

### 10.1 Modul Accounts

- [ ] `POST /api/v1/accounts/register/` hanya menerima Guest; memvalidasi username unik, email opsional, konfirmasi password, dan seluruh password validator Django.
- [ ] Registrasi berhasil membuat akun dengan password ter-hash, memulai session login, menetapkan status profil belum lengkap, dan tidak memberikan hak staff/superuser.
- [ ] Respons registrasi tidak memuat password atau password hash; error username duplikat dan validasi lain dikembalikan dalam format JSON.
- [ ] `POST /api/v1/accounts/login/` membuat session Django untuk kredensial valid dan mengembalikan status kelengkapan profil serta tujuan API lokal yang sesuai.
- [ ] Login gagal dan akun nonaktif menghasilkan status/pesan generik yang sama; respons tidak mengungkap apakah username terdaftar.
- [ ] `POST /api/v1/accounts/logout/` mengakhiri sesi saat ini, berhasil pula untuk Guest, dan tidak menghapus akun atau sesi perangkat lain.
- [ ] `POST /api/v1/accounts/delete/` hanya menghapus akun dari sesi aktif setelah konfirmasi username dan password saat ini valid; tidak menerima ID target dari klien.
- [ ] Akun staff/superuser ditolak dari penghapusan mandiri; akun yang belum menyelesaikan profil tetap dapat menghapus akunnya sendiri.
- [ ] Lima konfirmasi gagal per akun dalam jendela 15 menit menyebabkan `429`; penghitung berlaku lintas sesi dan percobaan malformed/kosong juga dihitung.
- [ ] Penghapusan sukses menghapus akun dan profil terkait serta mencabut sesi aktif akun di semua perangkat; kegagalan database membatalkan operasi secara atomik.
- [ ] Penghapusan tidak mengklaim menghapus listing, favorite, report, guide, atau file gambar eksternal.

### 10.2 Modul Profiles

- [ ] `POST /api/v1/profiles/` hanya dapat digunakan oleh user login untuk membuat profil atau melengkapi profil yang belum lengkap; `display_name` nonblank diperlukan agar user menjadi Member.
- [ ] Pembuatan profil oleh akun yang profilnya sudah lengkap ditolak dengan `409`; pengeditan profil lengkap dilakukan melalui endpoint `PATCH /api/v1/profiles/me/`.
- [ ] Onboarding menerapkan batas field dan validasi yang didokumentasikan; kegagalan validasi tidak meninggalkan perubahan parsial pada profil atau email akun.
- [ ] `GET /api/v1/profiles/me/` dan `PATCH /api/v1/profiles/me/` hanya mengakses profil user dari sesi aktif; akun tanpa profil lengkap menerima respons API `profile_incomplete`, bukan redirect HTML.
- [ ] PATCH bersifat parsial: field yang tidak dikirim tetap, nilai kosong mengosongkan field opsional, dan `remove_avatar`/`remove_cover` menghapus gambar secara independen.
- [ ] Perubahan email akun melalui onboarding/edit profil tersimpan atomik bersama perubahan profil; email akun hanya dikembalikan pada endpoint profil sendiri, tidak pada profil publik.
- [ ] Profil publik mengembalikan `404` generik bila profil tidak ada atau `display_name` kosong dan tidak menyediakan operasi edit profil pengguna lain.
- [ ] Guest dan user login dengan profil belum lengkap menerima `contact: null`; hanya pemilik atau Member lengkap yang dapat menerima kontak penjual dan nomor telepon.
- [ ] Normalisasi Instagram dan nomor telepon, validasi email kontak, pasangan `contact_type`/`contact_value`, penolakan pola alamat, serta validasi URL gambar/kontak mengikuti aturan yang didokumentasikan.
- [ ] Respons profil publik memakai `Cache-Control: private, no-store` dan tidak pernah memuat email akun.
- [ ] Tidak ada klaim bahwa modul Profiles menyediakan endpoint JSON listing/storefront atau penghapusan profil; perilaku storefront yang disebut dalam dokumen tetap konteks HTML/HTMX.

### 10.3 Kriteria lintas modul

- [ ] API memakai prefix `/api/v1/`, request/response JSON, dan tidak mengubah route atau perilaku HTML yang ada.
- [ ] Operasi perubahan state, termasuk login anonim dan registrasi, dilindungi CSRF; kegagalan autentikasi tidak diarahkan ke halaman HTML.
- [ ] Error memakai bentuk JSON konsisten dan tidak membocorkan password, password hash, token, atau detail internal.
- [ ] Method yang tidak didukung mengembalikan `405`; status sukses/gagal mengikuti kontrak pada spesifikasi endpoint.
- [ ] Dokumentasi dan implementasi membedakan endpoint API yang direncanakan dari fitur yang belum tersedia, termasuk DRF, OpenAPI, listing JSON, dan penghapusan profil.
