# API listing (mobile)

Semua balasan berupa JSON. Aturannya sama dengan halaman web `/listings/`: katalog hanya berisi listing `Available`, listing `Hidden` hanya terlihat oleh penjual dan admin, dan penjual selalu diambil dari akun yang login.

| Metode dan path | Akses | Input | Respons sukses |
| --- | --- | --- | --- |
| `GET /api/v1/listings/` | Semua | Opsional, sama dengan katalog web: `q`, `category`, `size` (boleh berulang), `condition` (boleh berulang), `price_min`, `price_max`, `city`, `tag` (boleh berulang: `repairable`, `upcycled`, `local`, `extends`), `sort` (`terbaru`, `harga_terendah`, `harga_tertinggi`), `page` | `200` dengan `count`, `next`, `previous`, `results` (12 per halaman) |
| `POST /api/v1/listings/` | Member | Field listing (lihat di bawah) | `201` dengan detail listing baru |
| `GET /api/v1/listings/<id>/` | Semua | — | `200` dengan detail listing |
| `PATCH /api/v1/listings/<id>/` | Pemilik atau admin | Field yang ingin diubah saja | `200` dengan detail terbaru |
| `DELETE /api/v1/listings/<id>/` | Pemilik atau admin | — | `204` tanpa isi |
| `POST /api/v1/listings/<id>/status/` | Pemilik | `{"status": "Sold"}` atau `{"status": "Available"}` | `200` dengan detail terbaru |
| `GET /api/v1/listings/mine/` | Member | Opsional: `status` (`tersedia`, `terjual`, `disembunyikan`), `page` | `200` dengan `count`, `next`, `previous`, `results`, `status`, dan `counts` (`all`, `tersedia`, `terjual`, `disembunyikan`) |
| `GET /api/v1/listings/locations/?city=Depok` | Member | `city` | `200` dengan `query`, `status` (`ok`, `short`, `throttled`, `unavailable`), `results` (`title`, `subtitle`, `city`, `lat`, `lon`), dan `attribution` |

"Member" berarti sudah login dan profilnya lengkap.

## Field listing

`POST` dan `PATCH` divalidasi oleh `ListingForm` yang sama dengan form web.

| Field | Keterangan |
| --- | --- |
| `title` | Wajib, 5 sampai 120 karakter |
| `description` | Wajib |
| `category` | Wajib: `Top`, `Bottom`, `Dress`, `Outerwear`, `Modest Wear` |
| `size` | Wajib: `XS`, `S`, `M`, `L`, `XL`, `XXL`, `Free Size` |
| `condition` | Wajib: `Like New`, `Good`, `Fair`, `Needs Repair` |
| `price` | Wajib, rupiah, 0 sampai 100.000.000 |
| `image_url` | Wajib, URL `http` atau `https` |
| `city` | Wajib, kota atau area umum (bukan alamat rumah) |
| `brand` | Opsional |
| `latitude`, `longitude` | Opsional, dari `locations`. Koordinat di luar Indonesia dibuang |
| `is_repairable`, `is_upcycled`, `is_locally_available`, `extends_clothing_life` | Opsional, boolean. Pada `POST`, field yang tidak dikirim bernilai `false` |

`status` dan `seller` tidak bisa diubah lewat `POST` atau `PATCH`, dan akan diabaikan kalau dikirim. Gunakan endpoint `status` untuk menandai terjual.

## Isi respons

Setiap item katalog memuat `id`, `title`, `brand`, `category`, `size`, `condition`, `price`, `image_url`, `city`, `status`, `sustainability_tags`, `is_favorited`, dan `created_at`. Item di `mine` menambahkan `updated_at` dan `sold_at`.

Detail menambahkan `description`, empat field boolean keberlanjutan, `sold_at`, `updated_at`, `is_owner`, `latitude`, `longitude`, dan `seller` (`id`, `display_name`, `active_listings`). Koordinat hanya diisi untuk pemilik, selain itu `null`. Kontak penjual tidak ada di sini; ambil lewat API profil dengan `seller.id`.

## Error

| Status | Arti |
| --- | --- |
| `400` | Input tidak valid. Isinya `{"nama_field": ["pesan"]}`, error umum ada di `non_field_errors` |
| `403` | Belum login, profil belum lengkap, atau token CSRF tidak ada |
| `404` | Listing tidak ada, `Hidden`, bukan milikmu, atau `page` di luar jangkauan |
| `405` | Metode tidak didukung |
| `409` | Status listing yang disembunyikan moderator tidak bisa diubah |

## Login dari klien mobile

API ini memakai sesi Django, sama dengan API favorit. Login dulu, lalu kirim cookie `sessionid` di setiap request. Untuk `POST`, `PATCH`, dan `DELETE`, kirim juga cookie `csrftoken` dan header `X-CSRFToken` dengan nilai token terbaru. Body boleh JSON (`Content-Type: application/json`) atau form-encoded.
