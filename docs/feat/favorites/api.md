# API favorit (mobile)

Semua endpoint memerlukan sesi Django dan akun dengan profil lengkap. Favorit dan catatan bersifat privat.

| Metode dan path | Input | Respons sukses |
| --- | --- | --- |
| `GET /api/v1/favorites/` | Opsional: `category` (mis. `Modest Wear`), `page` | `200` dengan `count`, `next`, `previous`, `results` (20 per halaman). |
| `POST /api/v1/favorites/` | `{"listing_id": 42}` | `201` untuk favorit baru, `200` jika sudah ada. POST kedua tidak menimpa catatan. Hanya listing `Available` milik orang lain yang bisa ditambahkan. |
| `GET /api/v1/favorites/<id>/` | — | `200` dengan detail favorit sendiri. |
| `PATCH /api/v1/favorites/<id>/` | `{"note": "Catatan saya"}` | `200` dengan detail terbaru. Maksimal 1.000 karakter; kirim `""` untuk mengosongkan. |
| `DELETE /api/v1/favorites/<id>/` | — | `204` tanpa isi. Pemilik juga bisa menghapus favorit lama saat listing disembunyikan. |

`<id>` adalah ID **favorit**, bukan ID listing. Setiap favorit memuat `id`, `note`, `created_at`, `updated_at`, dan `listing` dengan `id`, `title`, `price` (rupiah), `category`, `image_url`, dan `status`. Favorit dengan listing `Sold` tetap bisa dibaca dan diedit catatannya; listing `Hidden` tidak muncul di daftar maupun detail. Data yang tidak bisa diakses mengembalikan `404`; input tidak valid `400`; akses tanpa sesi atau profil lengkap `403`.

## Login dari klien mobile

1. `GET /accounts/login/` untuk memperoleh cookie `csrftoken`.
2. `POST /accounts/login/` sebagai form URL-encoded dengan `username`, `password`, dan `csrfmiddlewaretoken`. Simpan cookie `sessionid` dan **`csrftoken` yang baru** dari respons login. Jika server meminta pelengkapan profil, selesaikan onboarding sebelum mengakses favorit.
3. Kirim cookie sesi pada request favorit. Untuk `POST`, `PATCH`, dan `DELETE`, kirim juga cookie `csrftoken` dan header `X-CSRFToken` dengan nilai token terbaru. Di HTTPS, sertakan `Referer` dari origin yang sama bila klien tidak mengirim header `Origin`. Gunakan `Content-Type: application/json` ketika mengirim JSON.

Endpoint login JSON dan autentikasi token/JWT tidak termasuk perubahan ini.
