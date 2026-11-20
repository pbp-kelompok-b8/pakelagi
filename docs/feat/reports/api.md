# API laporan

Semua endpoint memerlukan sesi Django dan profil lengkap (nama tampilan tidak kosong), termasuk untuk superuser. Akses tanpa sesi atau profil lengkap mengembalikan `403`. Untuk request yang mengubah data, kirim cookie sesi, cookie `csrftoken`, dan header `X-CSRFToken` sesuai [alur login sesi](../favorites/api.md#login-dari-klien-mobile). Kirim body JSON dengan `Content-Type: application/json`.

| Metode dan path | Input dan akses | Respons sukses |
| --- | --- | --- |
| `GET /api/v1/reports/` | Daftar laporan milik sendiri. Superuser dapat melihat semua laporan dan memakai `?reporter=<id>` (ID pengguna berupa bilangan bulat positif); parameter ini diabaikan untuk pengguna lain. | `200`, array laporan |
| `POST /api/v1/reports/` | `{"listing": 42, "reason": "Misleading", "description": "Foto tidak sesuai dengan barang."}`. Listing harus berstatus `Available` atau `Sold` dan bukan milik pelapor. Server menetapkan pelapor dari sesi dan status `open`. | `201`, laporan baru |
| `GET /api/v1/reports/<id>/` | Laporan milik sendiri, atau laporan apa pun bagi superuser. | `200`, detail laporan |
| `PUT /api/v1/reports/<id>/` | `reason` dan `description` wajib. Hanya pemilik laporan berstatus `open`. | `200`, detail terbaru |
| `PATCH /api/v1/reports/<id>/` | Kirim `reason` dan/atau `description`. Hanya pemilik laporan berstatus `open`. | `200`, detail terbaru |
| `DELETE /api/v1/reports/<id>/` | Hanya pemilik laporan berstatus `open` yang belum memiliki catatan moderasi. | `204`, tanpa isi |

`<id>` adalah UUID laporan, bukan ID listing. Respons memuat `id`, `reporter`, `listing`, `listing_title`, `reason`, `description`, `status`, `created_at`, dan `updated_at`. `listing_title` menyimpan judul saat laporan dibuat; `listing` menjadi `null` bila listing dihapus. Perubahan judul, penyembunyian, atau penghapusan listing tidak menghalangi penyuntingan laporan yang masih `open`.

- `reason`: `Counterfeit`, `Misleading`, `Offensive`, `Prohibited Item`, atau `Other`. `description`: 10–1.000 karakter setelah spasi di awal dan akhir dibuang.
- `400` untuk input tidak valid (termasuk field di luar yang diizinkan), listing milik sendiri, `reporter` filter yang tidak valid bagi superuser, atau laporan kedua untuk kombinasi pelapor dan listing yang masih punya laporan `open`/`reviewing`. Setelah `resolved`/`rejected`, pelapor boleh membuat laporan baru.
- `404` untuk laporan yang tidak dapat diakses atau tidak ada, serta listing tujuan yang `Hidden` atau tidak ada. `403` untuk perubahan pada laporan yang tidak lagi `open` atau penghapusan laporan yang memiliki catatan moderasi.
- `is_staff` saja tidak memberi hak baca lintas pengguna. Hak tambahan superuser hanya untuk baca; aturan tulis tetap berlaku. Perubahan status, catatan internal, dan tindakan pada listing tetap di antarmuka web `/moderation/reports/`. API tidak mengirim isi catatan moderator, termasuk untuk superuser.
