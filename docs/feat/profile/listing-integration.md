# Status integrasi etalase dengan listing

## Keputusan cakupan

Modul Listing sudah tersedia (app `listings`) dan etalase profil kini membaca data nyata. Adapter kosong (`EmptyListingAdapter`) sudah diganti. Favorit **belum** ada (modul terpisah), jadi bagian favorit di kontrak di bawah masih menunggu. Spesifikasi utama tetap berlaku; dokumen ini mencatat apa yang sudah tersambung dan apa yang belum.

## Cara kerjanya

`profiles/storefront.py` menyediakan `listing_context(seller_id, viewer, query)` (argumen keyword-only). View profil sendiri dan publik memanggil interface yang sama. `StorefrontSelection` menormalisasi GET `tab=dijual|terjual`, `sort=terbaru|harga_terendah|harga_tertinggi`, dan `page` positif. Pilihan tidak valid kembali ke default. Pergantian tab/urutan menghilangkan posisi pemuatan sebelumnya.

Data barangnya diambil oleh `listings/storefront.py` (`for_profile(seller_id, viewer, selection)`), yang mengembalikan `available_count`, `sold_count`, `listings`, `sold_preview`, `has_more`, `next_count`, dan `next_page`. `templates/profiles/listings.html` merender kartu memakai partial bersama `templates/listings/components/listing_card.html` (yang sama dengan katalog).

## Kontrak adapter listing dan statusnya

Semua butir bertanda **selesai** diuji di `listings/test_storefront.py`.

- **Selesai.** Filter seller ke User, bukan Profile; hanya Available/Sold publik, kecualikan Hidden dan hasil moderasi pada daftar, total, dan cuplikan, termasuk untuk pemilik.
- **Selesai.** Hitung total masing-masing status secara terpisah. Dijual default; delapan barang per pemuatan. `page=N` bisa dibuka langsung dan memulihkan seluruh kartu yang sudah dimuat tanpa state JS (pemuatan kumulatif: `?page=3` menampilkan 24 barang pertama sekaligus). Angka `page` dibatasi (`MAX_LOADED_PAGES`) supaya nilai raksasa tidak membuat query bermasalah.
- **Selesai.** Urutan terbaru memakai created_at turun lalu ID turun. Harga naik/turun memakai ID sebagai pembeda tetap.
- **Selesai.** Cuplikan maksimal empat Sold berdasarkan sold_at turun lalu ID turun, hanya pada Dijual. sold_at dicatat saat transisi Sold (bukan updated_at umum). Barang Sold lama yang sold_at-nya kosong ditaruh paling akhir.
- **Selesai.** Kontrol muat dengan label min(8, sisa) dan indikator `…`; `hx-sync="this:drop"` mencegah request berulang. Pesan "coba lagi" tersedia (`#storefront-error`) dan hasil sebelumnya dipertahankan saat request gagal. *Perilaku gagal-memuat ini diverifikasi manual di browser, belum otomatis.*
- **Selesai.** Partial kartu berisi URL detail nyata, fallback gambar, brand, judul, Rupiah, ukuran, kondisi, dan kota listing. Sold mempunyai badge teks; kartu tidak menautkan ke seller.
- **Belum (menunggu modul Favorit).** Favorit memerlukan route POST+CSRF dan constraint unik user/listing. Validasi member, kepemilikan, status, dan moderasi pada server. Jangan tambah pada listing sendiri/Sold; favorit lama Sold tetap bisa dihapus pemilik. Jangan mengandalkan keadaan saat kartu dirender. Parameter `viewer` sudah diteruskan ke `for_profile` untuk keperluan ini.
- **Selesai.** Tidak ada kontak privat yang dikirim melalui kartu, partial, atau respons data kepada guest/pengguna belum onboarding.

HTML biasa tetap fallback navigasi. HTMX mengganti `#storefront-listings` dan memperbarui URL. Permintaan history restore memperoleh HTML penuh; respons bervariasi menurut HX-Request, HX-History-Restore-Request, dan Cookie serta memakai private/no-store.

## Catatan teknis

- HTMX menjalankan ulang semua `<script>` saat tombol back dipakai. Karena itu skrip di halaman tidak boleh memakai `const`/`let` di tingkat paling luar (akan error "already been declared"); variabel dibuat di dalam fungsi. Ada test yang menjaganya (`listings/test_scripts.py`).

## Yang belum diimplementasikan/diuji

Favorit (aksi tambah/hapus, constraint unik, favorit lama pada Sold, race status pada aksi favorit), pengujian otomatis untuk kegagalan pemuatan di browser, serta verifikasi visual lintas browser/keyboard. Jangan menandai butir-butir itu selesai sebelum modul Favorit tersedia dan tes integrasinya berjalan.
