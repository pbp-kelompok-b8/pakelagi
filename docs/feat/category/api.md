# API kategori (mobile)

`GET /api/v1/categories/` mengembalikan array JSON publik, tanpa login atau paginasi. Urutan dan nilainya sama dengan halaman `/categories/`. Kategori tanpa listing tetap ada dengan `count: 0`; listing `Sold` dan `Hidden` tidak dihitung.

Contoh satu elemen:

```json
{
  "value": "Modest Wear",
  "label": "Modest Wear",
  "slug": "modest-wear",
  "count": 4,
  "image_url": "https://pakelagi.example/static/images/categories/modest-wear.svg",
  "image_mobile_url": "https://pakelagi.example/static/images/categories/modest-wear-mobile.svg"
}
```

Pakai `value` sebagai nilai filter `category`, bukan `slug`. URL gambar absolut; asetnya SVG. Endpoint hanya menyediakan metadata kategori, bukan daftar listing.
