# API Panduan

Gunakan `Accept: application/json` dan sertakan garis miring di akhir URL.

| Request | Akses dan respons |
| --- | --- |
| `GET /api/v1/guides/` | Publik. `200` dengan array panduan terbit, terbaru lebih dulu. Filter opsional `?category=REUSE`. |
| `POST /api/v1/guides/` | Profil lengkap. `201` dengan panduan baru berstatus `PENDING`, belum terbit. |
| `GET /api/v1/guides/my-submissions/` | Profil lengkap. `200` dengan `{ "count": …, "pending_count": …, "results": […] }` untuk kiriman milik akun sesi, terbaru lebih dulu. |
| `GET /api/v1/guides/<id>/` | `200` untuk panduan terbit. Panduan lain hanya bisa dibaca pemilik berprofil lengkap atau superuser; selain itu `404`, sama seperti ID yang tidak ditemukan. |
| `PUT` / `PATCH /api/v1/guides/<id>/` | Hanya pemilik berprofil lengkap dan status `PENDING`. `200` dengan data terbaru. `PUT` wajib menyertakan `title`, `ringkasan`, dan `konten`; `PATCH` hanya menyertakan field yang diubah. |
| `DELETE /api/v1/guides/<id>/` | Hanya pemilik berprofil lengkap dan status `PENDING`. `204` tanpa isi. |

Panduan terbit harus berstatus `DISETUJUI`, ditandai terbit, dan sudah mencapai waktu `date_published`. Status pending/ditolak dan jadwal mendatang tidak terlihat oleh publik. `is_staff` saja tidak memberi akses khusus; superuser tidak mendapat hak untuk mengubah draf orang lain.

`rejected_notes` hanya ditampilkan untuk kiriman berstatus `DITOLAK` yang boleh dibaca oleh akun sesi; nilainya `null` untuk status lain.

Untuk menulis, kirim JSON dengan `title`, `ringkasan`, `konten` (Markdown), serta `category` dan `image_url` (HTTPS) bila diperlukan. Nilai `category`: `PERAWATAN` (default), `PERBAIKAN`, `REUSE`, `SLOW_FASHION`, `CONSCIOUS_SHOPPING`. ID, penulis, status, dan field moderasi/publikasi hanya-baca. Respons juga memuat `content_html` dan `table_of_contents` (keduanya HTML hasil render). `400` berarti input tidak valid atau panduan bukan lagi `PENDING`; `403` berarti sesi/profil belum memenuhi syarat, CSRF gagal, atau akun mencoba mengubah draf orang lain.

## Sesi dan CSRF

1. Ambil cookie `csrftoken` dari `GET /accounts/login/`, lalu login dengan JSON `{"username": "…", "password": "…"}` ke `POST /api/v1/accounts/login/`, beserta cookie dan header `X-CSRFToken`. Jika `profile_complete` bernilai `false`, lengkapi profil melalui `/api/v1/profiles/` dengan `display_name` yang tidak kosong.
2. Simpan `sessionid` dan `csrftoken` terbaru dari login. Kirim cookie sesi untuk request privat. Untuk `POST`, `PUT`, `PATCH`, dan `DELETE`, kirim juga cookie CSRF dan header `X-CSRFToken`. Di HTTPS, kirim `Origin` yang sama dengan server atau `Referer` dari origin yang sama. Gunakan `Content-Type: application/json` untuk body JSON.

Halaman HTML tetap di `/guides/`. Moderasi dan publikasi tidak tersedia melalui API ini.
