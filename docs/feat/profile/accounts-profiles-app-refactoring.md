# Rencana Refactoring Django App `accounts` dan `profiles`

## Status dokumen

Dokumen ini adalah spesifikasi dan checklist perencanaan refactor. **Dokumen ini tidak mengimplementasikan perubahan kode.** Semua item checklist berstatus belum dikerjakan; centang hanya setelah perubahan benar-benar dilakukan dan diverifikasi.

## Tujuan

Memisahkan fitur akun/autentikasi dan profil dari app `main` menjadi app Django `accounts` dan `profiles`. Pemisahan kepemilikan file bertujuan mengurangi konflik kerja paralel, memperjelas tanggung jawab kode, dan membuat pengembangan lebih mudah dinavigasi.

Refactor ini bersifat struktural. Perilaku fitur, akses, tampilan, dan URL publik yang sudah ada harus tetap sama. Perubahan perilaku di luar tujuan pemisahan harus menjadi pekerjaan terpisah.

## Sumber acuan dan batasan

- Spesifikasi produk utama: [`../../pakelagi-specification.md`](../../pakelagi-specification.md).
- Spesifikasi fitur akun/profil: [`profile-specification.md`](profile-specification.md).
- Kontrak integrasi etalase-listing: [`listing-integration.md`](listing-integration.md).
- Istilah domain: [`../../../CONTEXT.md`](../../../CONTEXT.md).
- Istilah **akun** berarti identitas untuk login, sedangkan **profil** adalah identitas tampilan. Keduanya bukan sinonim.
- Django `User` bawaan tetap digunakan. Refactor ini tidak memperkenalkan custom user model.
- Tidak termasuk dalam refactor: implementasi penghapusan profil, model/rute listing atau favorite, dan pengembangan ulang tampilan atau alur produk.

## Keputusan yang disepakati

1. Pertahankan perilaku aplikasi dan path URL publik yang sudah ada.
2. Pertahankan template di direktori template project yang sudah teratur berdasarkan nama app: `templates/accounts/` dan `templates/profiles/`. Template tidak perlu dipindahkan ke dalam direktori app.
3. App `profiles` menjadi pemilik model `Profile`; app `accounts` memiliki alur akun dan autentikasi.
4. Pertahankan tabel database yang sudah ada, `main_profile`, dan data profil. Perpindahan kepemilikan model harus menggunakan strategi migrasi non-destruktif yang menangani state Django serta database.
5. Jangan menghapus atau membuat ulang histori migrasi sebagai jalan pintas. Verifikasi upgrade database yang sudah berisi data dan instalasi baru dari nol.
6. Pertahankan path URL eksternal, tetapi gunakan namespace `accounts:` dan `profiles:` secara konsisten di seluruh referensi internal. Jangan membuat alias namespace `main:` lama kecuali kemudian terbukti dibutuhkan konsumen yang kompatibel.
7. Pindahkan tes mengikuti kepemilikan domain dan pertahankan cakupan integrasi lintas app.
8. `accounts` memiliki data akun, termasuk email akun. `profiles` memiliki data profil. Form edit profil boleh tetap menjadi satu alur bagi pengguna, tetapi penyimpanan lintas app harus eksplisit dan tetap atomik.
9. `main` tetap ada untuk beranda dan integrasi/komponen yang benar-benar bersama; app ini bukan lagi pemilik fitur autentikasi atau profil.
10. Aturan kelengkapan profil dan akses member menjadi API bersama di `profiles.access`.

## Pemetaan kepemilikan yang dituju

| Tanggung jawab/file saat ini | Kepemilikan tujuan | Catatan |
|---|---|---|
| `main/models.py` — model `Profile` | `profiles/models.py` | Pertahankan relasi `user.profile`, tabel `main_profile`, field, batasan, dan perilaku saat ini. |
| Form `RegistrationForm` dan `LoginForm` dari `main/forms.py` | `accounts/forms.py` | Tetap gunakan autentikasi Django dan `User` bawaan. |
| Form `ProfileForm` dari `main/forms.py` | `profiles/forms.py` | Profil tetap milik `profiles`; pembaruan `User.email` dikoordinasikan dengan pemilik data akun `accounts` dalam transaksi atomik. |
| View `register`, `AccountLoginView`, `AccountLogoutView` dari `main/views.py` | `accounts/views.py` | Pertahankan redirect, validasi, keamanan, dan feedback. |
| View `profile_create`, `profile_form`, `profile_detail`, `profile_public`, `profile_edit`, `render_storefront` dari `main/views.py` | `profiles/views.py` | Pertahankan aturan akses, URL, dan perilaku etalase. |
| `main/access.py` | `profiles/access.py` | Pindahkan aturan kelengkapan profil, onboarding URL, safe `next`, dan akses member; hindari siklus import. |
| Validator profil dari `main/validators.py` | `profiles/validators.py` | Sediakan jalur re-export kompatibilitas `main.validators.validate_external_https_url` karena migrasi historis mengimpornya. |
| `main/profile_contacts.py` | `profiles/profile_contacts.py` | Tetap jangan mengirim kontak penjual kepada guest atau user yang belum onboarding. |
| `main/storefront.py` | `profiles/storefront.py` | Pertahankan adapter kosong dan kontrak listing yang didokumentasikan; jangan menambahkan fitur listing/favorite pada refactor ini. |
| `main/urls.py` | URLconf masing-masing app | `main` tetap menyediakan route beranda. Path publik akun dan profil tetap sama. |
| Template `templates/accounts/*` | Tetap di `templates/accounts/*` | Lokasi sudah teratur berdasarkan nama app; tidak perlu dipindahkan. Pertahankan nama template dan referensinya. |
| Template `templates/profiles/*` | Tetap di `templates/profiles/*` | Lokasi sudah teratur berdasarkan nama app; tidak perlu dipindahkan. Pertahankan nama template dan referensinya. |
| Tes autentikasi dan registrasi di `main/test_authentication.py`, `main/test_registration.py` | Tes app `accounts` | Tes `main/test_authentication.py` saat ini juga mengimpor helper registrasi; rapikan helper bersama tanpa menghilangkan cakupan integrasi. |
| Tes profil dan etalase di `main/test_profiles.py`, `main/test_profile_fields.py`, `main/test_profile_edit.py`, `main/test_storefront.py` | Tes app `profiles` | Tetap uji URL, izin, privasi, validasi, HTMX, cache, dan empty adapter. |
| Tes 404 di `main/test_not_found.py` | `main` | 404 adalah perilaku lintas aplikasi dan tetap menjadi tanggung jawab project/main. |
| `main/show_main` dan halaman beranda | `main` | Tidak dipindahkan. |
| Komponen global header/footer, base/shared shell, dan 404 | Project/shared UI | Tetap shared, namun semua reverse URL akun/profil harus menggunakan namespace baru. |
| `main/admin.py` | Sesuai kebutuhan app | Saat ini `Profile` tidak terdaftar di admin; jangan menganggap ada konfigurasi yang harus dipindahkan. |

### URL dan nama route

Path berikut adalah kontrak eksternal dan harus dipertahankan:

| Fungsi | Path yang dipertahankan | Namespace tujuan |
|---|---|---|
| Registrasi | `/accounts/register/` | `accounts:register` |
| Login | `/accounts/login/` | `accounts:login` |
| Logout | `/accounts/logout/` | `accounts:logout` |
| Buat/lengkapi profil | `/profile/create/` | `profiles:profile_create` |
| Etalase profil sendiri | `/profile/` | `profiles:profile` |
| Edit profil | `/profile/edit/` | `profiles:profile_edit` |
| Etalase profil publik | `/profile/<user_id>/` | `profiles:profile_public` |
| Beranda | `/` | Nama route tetap dimiliki `main` |

ID pada URL profil publik adalah primary key `User`, bukan primary key model `Profile`. Ubah seluruh reverse URL internal secara serentak, termasuk settings, view, template shared, dan tes. Pertahankan alur `next` yang aman dan jangan menerima redirect ke host eksternal sembarang.

## Rencana pelaksanaan dan checklist

### Fase 0 — Baseline dan pengamanan kontrak

- [ ] Catat hasil test suite sebelum perubahan untuk dipakai sebagai baseline.
- [ ] Catat nama route, path, dan hasil redirect yang sudah ada, termasuk redirect registrasi ke onboarding.
- [ ] Catat state migrasi saat ini (`main` 0001–0004), nama tabel `main_profile`, content type, dan jumlah/data contoh Profile pada database pengujian yang dapat dipulihkan.
- [ ] Pastikan tersedia salinan database atau fixture terkontrol untuk menguji upgrade dengan data yang sudah ada; jangan memakai data produksi untuk eksperimen.
- [ ] Identifikasi semua reverse URL `main:` dan import `main.*` yang terkait akun/profil sebelum dipindahkan.
- [ ] Sepakati urutan deployment/migrasi untuk lingkungan yang menyimpan database persisten.

### Fase 1 — Buat batas app dan konfigurasi URL

- [ ] Buat app Django `accounts` dengan app config yang eksplisit.
- [ ] Buat app Django `profiles` dengan app config yang eksplisit.
- [ ] Daftarkan kedua app pada `INSTALLED_APPS` tanpa mengubah konfigurasi lain yang tidak terkait.
- [ ] Pisahkan URLconf untuk `accounts` dan `profiles`, lalu sertakan keduanya dari konfigurasi URL project.
- [ ] Pertahankan seluruh path publik yang tercantum pada tabel URL.
- [ ] Pertahankan route beranda di `main` dan tentukan pola include agar route root tidak mengambil alih path app lain.
- [ ] Ubah konfigurasi login/redirect serta seluruh reverse URL internal ke namespace pemilik baru.
- [ ] Tambahkan tes resolusi URL untuk semua path dan nama route yang dipertahankan.

### Fase 2 — Pindahkan autentikasi ke `accounts`

- [ ] Pindahkan form registrasi dan login ke `accounts/forms.py`.
- [ ] Pindahkan view registrasi, login, dan logout ke `accounts/views.py`.
- [ ] Pertahankan penggunaan Django `User` bawaan; jangan menambah custom user model.
- [ ] Pertahankan hashing password Django, validasi password, penanganan user nonaktif, pesan login generik, CSRF, dan logout POST-only.
- [ ] Pertahankan redirect registrasi ke onboarding dan perilaku `next` yang aman untuk login.
- [ ] Pertahankan template `layout.html`, `login.html`, dan `register.html` di `templates/accounts/`; jangan memindahkannya ke dalam app.
- [ ] Pastikan referensi template akun tetap valid tanpa mengubah nama template yang dipanggil oleh view.
- [ ] Pindahkan tes registrasi dan autentikasi ke area tes `accounts` atau struktur yang konsisten dengan repo.
- [ ] Pertahankan tes integrasi yang menguji batas registrasi/login menuju onboarding profil.
- [ ] Pastikan helper tes yang digunakan bersama tidak menimbulkan import silang antar modul tes yang rapuh.

### Fase 3 — Pindahkan profil dan integrasi etalase

- [ ] Pindahkan model `Profile` menjadi model yang dimiliki app `profiles`.
- [ ] Pertahankan semua field, validasi, relasi one-to-one ke `settings.AUTH_USER_MODEL`, cascade user-ke-profil, dan reverse relation `user.profile`.
- [ ] Pertahankan tabel `main_profile`; jangan membuat tabel baru atau kehilangan/menduplikasi record saat upgrade.
- [ ] Rancang migrasi yang mentransfer kepemilikan migration state model secara eksplisit dan aman. Tinjau perubahan app label, tabel, content type, permission, dan urutan dependency sebelum menerapkannya.
- [ ] Jangan sekadar memindahkan/menghapus file migrasi historis atau menghasilkan operasi delete/create yang dapat menghapus data.
- [ ] Pertahankan jalur import `main.validators.validate_external_https_url` agar migrasi lama tetap dapat dimuat; implementasi validator boleh dimiliki `profiles`.
- [ ] Pindahkan `ProfileForm`, view profil, kontak, storefront, dan aturan akses ke modul `profiles` sesuai tabel kepemilikan.
- [ ] Pertahankan penyimpanan profil dan email akun yang atomik, serta jangan menjadikan email akun sebagai kontak penjual otomatis.
- [ ] Pertahankan `detail.html`, `field.html`, `form.html`, dan `listings.html` di `templates/profiles/`; jangan memindahkannya ke dalam app.
- [ ] Pastikan referensi template profil tetap valid.
- [ ] Pertahankan struktur etalase, akses kontak, status empty adapter, dukungan HTMX/history, dan header cache sesuai perilaku saat ini.
- [ ] Pindahkan tes profil, field, edit, dan storefront mengikuti app `profiles`; pertahankan uji integrasi accounts/profiles.

### Fase 4 — Rapikan integrasi `main` dan shared UI

- [ ] Pastikan `main` hanya mempertahankan beranda serta tanggung jawab bersama yang memang lintas domain.
- [ ] Hapus implementasi akun/profil dari `main` hanya setelah seluruh pemanggil dan tes berpindah; jangan meninggalkan duplikasi aktif.
- [ ] Pertahankan handler/halaman 404 dan tesnya di area shared/main.
- [ ] Perbarui namespace pada header, footer, base/shared templates, halaman 404, dan setiap komponen yang menautkan akun/profil.
- [ ] Periksa tidak ada template yang masih menggunakan reverse route `main:login`, `main:register`, `main:logout`, atau route profil lama.
- [ ] Periksa tidak ada import runtime yang masih mengandalkan modul akun/profil lama, selain shim kompatibilitas migrasi yang disengaja.
- [ ] Pastikan `profiles.access` menjadi API aturan kelengkapan/member tanpa siklus import dengan `accounts`.

### Fase 5 — Verifikasi migrasi, regresi, dan penerimaan

- [ ] Jalankan pemeriksaan migrasi Django dan pastikan tidak ada perubahan model yang belum tercakup.
- [ ] Uji upgrade dari database lama yang memiliki record profil; pastikan record, field, relasi User, dan akses ke `user.profile` tetap benar.
- [ ] Uji migrasi instalasi baru dari database kosong hingga semua migrasi selesai.
- [ ] Pastikan tidak ada kehilangan tabel, profil duplikat, perubahan ID, atau perpindahan tabel tak disengaja.
- [ ] Pastikan content type dan permission `Profile` tidak menjadi duplikat/kehilangan keterkaitan tanpa rencana yang ditinjau.
- [ ] Jalankan seluruh tes project, termasuk autentikasi, profil, validasi, 404, dan tes integrasi lintas app.
- [ ] Verifikasi path URL dan redirect tetap sama; nama route internal baru berfungsi pada seluruh template, view, dan settings.
- [ ] Verifikasi akses guest, user login yang belum onboarding, member, dan pemilik tetap sama.
- [ ] Verifikasi email akun dan kontak penjual tidak bocor pada halaman/response yang tidak berhak melihatnya.
- [ ] Verifikasi logout tetap POST + CSRF, operasi tulis tetap terlindungi CSRF, dan form invalid mempertahankan input yang aman.
- [ ] Verifikasi adapter listing tetap kosong dan tidak ada model, route, kartu, atau aksi favorite baru yang masuk tanpa spesifikasi terpisah.
- [ ] Tinjau diff untuk memastikan perubahan hanya mencakup refactor yang disepakati dan dokumen ini.

## Kriteria selesai

Refactor dapat dianggap selesai hanya jika seluruh kondisi berikut terpenuhi:

- [ ] Kepemilikan file dan tes mengikuti batas `accounts`, `profiles`, dan `main` yang disepakati.
- [ ] Path dan perilaku eksternal tidak berubah; namespace internal sudah konsisten dengan app pemilik.
- [ ] Template akun/profil tetap berada di `templates/accounts/` dan `templates/profiles/`, serta berhasil dirender dengan konfigurasi template project.
- [ ] Data dan histori database aman pada skenario upgrade maupun instalasi baru; tabel `main_profile` dan relasi yang disepakati tetap terjaga.
- [ ] Semua tes yang relevan lulus dan cakupan keamanan/privasi sebelumnya tetap ada.
- [ ] Tidak ada implementasi ganda yang aktif atau import silang yang menciptakan siklus.
- [ ] `main` tetap menjalankan beranda dan integrasi bersama tanpa menjadi pemilik fitur akun/profil.
- [ ] Tidak ada perubahan produk di luar refactor yang disepakati.

## Risiko dan perhatian khusus

- **Identitas model/migrasi:** model saat ini terdaftar sebagai `main.Profile`, menggunakan tabel default `main_profile`, dan memiliki migrasi `main` 0001–0004. Pemindahan model bukan sekadar memindahkan file Python. Strategi migrasi harus ditinjau sebelum implementasi, termasuk efek app label pada content type dan permission.
- **Import dari migrasi historis:** `main` migration 0003 menyerialisasi `main.validators.validate_external_https_url`. Fungsi pada path itu harus tetap dapat diimpor selama migrasi historis masih digunakan.
- **Email akun dan profil:** form profil saat ini juga memperbarui `User.email`. Pemisahan domain jangan sampai menimbulkan update parsial apabila salah satu penyimpanan gagal.
- **Batas akses:** aturan member bergantung pada profil lengkap dan digunakan di beberapa alur. Harus ada satu sumber kebenaran yang tidak membuat siklus import.
- **URL dan komponen global:** header/footer dan template bersama merujuk route akun/profil; memindahkan URLconf tanpa pembaruan menyeluruh dapat menyebabkan `NoReverseMatch`.
- **Cakupan fitur:** profile deletion belum tersedia dan integrasi listing/favorite masih berupa adapter kosong. Refactor tidak boleh menandai atau mengimplementasikan kemampuan tersebut secara tidak sengaja.
