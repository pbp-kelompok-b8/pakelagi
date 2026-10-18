# Status integrasi etalase dengan listing

## Keputusan cakupan

Pada branch implementasi ini belum ada modul Listing/Favorite. Sesuai keputusan pengguna, implementasi profil **hanya menyiapkan adapter kosong**, bukan membuat model/route listing atau favorite baru. Spesifikasi utama tetap berlaku; dokumen ini mencatat bagian yang belum tersambung, bukan mengganti kriteria penerimaan.

## Seam yang tersedia

`profiles/storefront.py` menyediakan `listing_context(seller_id, viewer, query)` (argumen keyword-only). View profil sendiri dan publik memanggil interface yang sama. `StorefrontSelection` menormalisasi GET `tab=dijual|terjual`, `sort=terbaru|harga_terendah|harga_tertinggi`, dan `page` positif. Pilihan tidak valid kembali ke default. Pergantian tab/urutan menghilangkan posisi pemuatan sebelumnya.

`EmptyListingAdapter.for_profile(seller_id, viewer, selection)` mengembalikan `available_count`, `sold_count`, `listings`, dan `sold_preview`. Saat ini jumlah selalu nol dan koleksi kosong secara eksplisit. Tidak ada data contoh atau query ke model yang belum ada. `templates/profiles/listings.html` hanya merender keadaan kosong: **mengganti adapter saja belum cukup untuk menampilkan kartu**.

## Kontrak adapter listing mendatang

Saat modul listing tersedia, ganti adapter kosong dan tambahkan partial kartu bersama beserta tes integrasi melalui GET etalase/HTMX yang sudah disepakati:

- Filter seller ke User, bukan Profile; hanya Available/Sold publik, kecualikan Hidden dan hasil moderasi pada daftar, total, dan cuplikan, termasuk untuk pemilik.
- Hitung total masing-masing status secara terpisah. Dijual default; delapan barang per pemuatan. `page=N` harus bisa dibuka langsung dan memulihkan seluruh kartu yang sudah dimuat tanpa state JS; mengganti hasil kumulatif secara atomik menghindari duplikasi.
- Urutan terbaru memakai publikasi/created_at turun lalu ID turun. Harga naik/turun memakai ID sebagai pembeda tetap.
- Cuplikan maksimal empat Sold berdasarkan sold_at turun lalu ID turun, hanya pada Dijual. sold_at harus dicatat saat transisi Sold, bukan updated_at umum.
- Tambahkan kontrol muat dengan label min(8, sisa), indikator, pencegahan request berulang, serta pesan coba lagi; pertahankan hasil sebelumnya saat request gagal.
- Partial kartu berisi URL detail nyata, fallback gambar, brand, judul, Rupiah, ukuran, kondisi, dan kota listing. Sold mempunyai badge teks; jangan membuat tautan seller yang mengasumsikan profil selalu tersedia.
- Favorit memerlukan route POST+CSRF dan constraint unik user/listing. Validasi member, kepemilikan, status, dan moderasi pada server. Jangan tambah pada listing sendiri/Sold; favorit lama Sold tetap bisa dihapus pemilik. Jangan mengandalkan keadaan saat kartu dirender.
- Tidak boleh mengirim kontak privat melalui DTO kartu, partial, atau respons data kepada guest/pengguna belum onboarding.

HTML biasa tetap fallback navigasi. HTMX mengganti `#storefront-listings` dan memperbarui URL. Permintaan history restore memperoleh HTML penuh; respons bervariasi menurut HX-Request, HX-History-Restore-Request, dan Cookie serta memakai private/no-store.

## Yang belum diimplementasikan/diuji

Daftar/kartu nyata, pagination 1/8/9/>16 barang, pengurutan data, total publik/status/moderasi, cuplikan Sold, transisi Sold, favorit dan race status. Jangan menandai checklist tersebut selesai sebelum modul tersedia dan tes integrasinya berjalan. Layout responsif dan fallback gambar profil tersedia; verifikasi visual lintas browser/keyboard tetap diperlukan.
