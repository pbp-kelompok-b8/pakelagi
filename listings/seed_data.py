# Data contoh untuk deployment pertama (spesifikasi §14): 50 listing tersedia (10 per kategori) dan 10 yang sudah terjual.
# Semua sintetis. Penjualnya akun contoh berawalan "sample_" yang tidak bisa login, dan kontaknya memakai
# example.com (domain yang memang dicadangkan untuk contoh), jadi tidak ada data pribadi anggota kelompok.
# Dipakai oleh: python manage.py seed_listings

SAMPLE_USERNAME_PREFIX = "sample_"


def photo(photo_id):
    # Semua foto sudah dicek bisa diakses (HTTP 200). Kalau suatu hari gagal dimuat, kartu menampilkan
    # placeholder lokal "Foto tidak tersedia" seperti biasa.
    return f"https://images.unsplash.com/photo-{photo_id}?auto=format&fit=crop&w=640&h=800&q=70"


# kunci -> (nama tampilan, bio)
SELLERS = {
    "nina": ("Nina Arum", "Lemari kedua yang masih cantik: atasan dan outer pilihan. Akun contoh untuk data awal Pakelagi."),
    "raka": ("Raka Pratama", "Pindahan dan beres-beres lemari, semua dijelaskan apa adanya. Akun contoh untuk data awal Pakelagi."),
    "tika": ("Tika Lestari", "Suka thrifting, sekarang gantian melepas koleksi. Akun contoh untuk data awal Pakelagi."),
    "bagas": ("Bagas Wicaksono", "Jual pakaian yang sudah tidak muat dan jarang terpakai. Akun contoh untuk data awal Pakelagi."),
    "dewi": ("Dewi Anggraini", "Pakaian bersih dan terawat, siap dipakai lagi. Akun contoh untuk data awal Pakelagi."),
}

# kunci -> (teks kota seperti hasil saran Nominatim, latitude, longitude). Koordinat sudah dibulatkan ke 2 desimal.
CITIES = {
    "bandung": ("Kota Bandung, Jawa Barat", "-6.91", "107.61"),
    "bogor": ("Kota Bogor, Jawa Barat", "-6.60", "106.80"),
    "bekasi": ("Kota Bekasi, Jawa Barat", "-6.24", "106.99"),
    "depok": ("Depok, Jawa Barat", "-6.40", "106.82"),
    "jaksel": ("Jakarta Selatan, DKI Jakarta", "-6.26", "106.81"),
    "yogya": ("Kota Yogyakarta, Daerah Istimewa Yogyakarta", "-7.80", "110.36"),
    "semarang": ("Kota Semarang, Jawa Tengah", "-6.97", "110.42"),
    "surabaya": ("Kota Surabaya, Jawa Timur", "-7.25", "112.75"),
    "malang": ("Kota Malang, Jawa Timur", "-7.98", "112.63"),
    "medan": ("Kota Medan, Sumatera Utara", "3.59", "98.67"),
    "makassar": ("Kota Makassar, Sulawesi Selatan", "-5.15", "119.43"),
    "denpasar": ("Kota Denpasar, Bali", "-8.65", "115.22"),
}


def row(seller, city, title, brand, category, size, condition, price, flags, photo_id, description, sold_days_ago=None):
    # flags berisi huruf tag keberlanjutan yang aktif: R = bisa diperbaiki, U = upcycled,
    # L = tersedia lokal, E = memperpanjang usia pakaian. Huruf yang tidak ditulis berarti tidak aktif.
    return {
        "seller": seller,
        "city": city,
        "title": title,
        "brand": brand,
        "category": category,
        "size": size,
        "condition": condition,
        "price": price,
        "is_repairable": "R" in flags,
        "is_upcycled": "U" in flags,
        "is_locally_available": "L" in flags,
        "extends_clothing_life": "E" in flags,
        "image_url": photo(photo_id),
        "description": description,
        "sold_days_ago": sold_days_ago,   # None = masih tersedia
    }


# ---------------------------------------------------------------- 50 listing tersedia (10 per kategori)
AVAILABLE = [
    # --- Top
    row("nina", "bandung", "Kemeja flanel kotak merah", "Uniqlo", "Top", "M", "Good", 85000, "LE", "1523381210434-271e8be1f52b",
        "Flanel tebal warna merah-hitam, sudah dipakai beberapa kali. Kancing lengkap dan warna tidak luntur."),
    row("raka", "jaksel", "Kaos putih polos oversize", "Erigo", "Top", "L", "Like New", 55000, "LE", "1521572163474-6864f9cf17ab",
        "Katun combed yang jatuh dan adem. Baru dipakai dua kali, belum pernah luntur atau melar."),
    row("dewi", "depok", "Kaos grafis tangan perdamaian", "Pull&Bear", "Top", "S", "Good", 65000, "LE", "1503342217505-b0a15ec3261c",
        "Sablon masih utuh dan tidak retak. Cocok dipadukan dengan jeans atau rok."),
    row("bagas", "surabaya", "Kaos polos satu set tiga warna", "H&M", "Top", "M", "Good", 120000, "E", "1562157873-818bc0726f68",
        "Hitam, putih, dan navy dijual sepaket. Ada bekas lipatan lemari, selebihnya bersih dan tidak bernoda."),
    row("tika", "yogya", "Kaos hitam logo kecil", "Cotton Ink", "Top", "XL", "Like New", 70000, "LE", "1618354691373-d851c5c3a990",
        "Bahan lembut dan tidak berbulu. Logo di dada kecil dan rapi."),
    row("nina", "bogor", "Sweatshirt putih crewneck", "Zara", "Top", "M", "Good", 110000, "E", "1620799140408-edc6dcb6d633",
        "Bagian dalam fleece masih tebal, rib di lengan dan pinggang belum kendur."),
    row("raka", "bekasi", "Sweatshirt oranye cerah", "Bershka", "Top", "S", "Fair", 60000, "RE", "1578587018452-892bacefd3f2",
        "Ada noda kecil di lengan kiri yang sudah dicoba dihilangkan sebagian. Harga sudah disesuaikan."),
    row("tika", "malang", "Poncho rajut krem berumbai", "", "Top", "Free Size", "Like New", 95000, "LE", "1434389677669-e08b4cac3105",
        "Rajutan longgar dengan rumbai di pinggir. Cocok untuk ruangan ber-AC atau jalan-jalan sore."),
    row("dewi", "medan", "Sweater rajut tebal krem", "Mango", "Top", "L", "Good", 130000, "LE", "1558769132-cb1aea458c5e",
        "Rajutan padat dan hangat, tidak berbulu. Dicuci dengan deterjen khusus wol."),
    row("bagas", "makassar", "Kemeja hijau sage lengan panjang", "Cotton Ink", "Top", "M", "Like New", 75000, "E", "1523381210434-271e8be1f52b",
        "Warna hijau sage yang kalem, bahan jatuh. Hanya dipakai untuk acara sekali."),
    # --- Bottom
    row("raka", "jaksel", "Jeans robek high waist", "Levi's", "Bottom", "M", "Good", 150000, "LE", "1541099649105-f69ad21f3246",
        "Robek di lutut memang modelnya. Pinggang tinggi, tidak ada jahitan yang lepas."),
    row("bagas", "surabaya", "Jeans lurus biru tua", "Levi's", "Bottom", "L", "Good", 175000, "LE", "1542272604-787c3835535d",
        "Denim tebal dengan potongan lurus klasik. Warna masih pekat karena jarang dicuci mesin."),
    row("nina", "bandung", "Celana jogger khaki", "Uniqlo", "Bottom", "M", "Like New", 95000, "LE", "1473966968600-fa801b869a1a",
        "Karet pinggang dan ujung kaki masih kencang. Bahan ringan, nyaman untuk sehari-hari."),
    row("dewi", "depok", "Jeans skinny biru muda", "H&M", "Bottom", "S", "Good", 80000, "E", "1584370848010-d7fe6bc767ec",
        "Stretch dan nyaman. Warna sedikit memudar sesuai gaya washed."),
    row("tika", "semarang", "Jeans ripped model santai", "Pull&Bear", "Bottom", "M", "Fair", 70000, "RE", "1582552938357-32b906df40cb",
        "Sobekan di lutut sudah agak melebar dan butuh dijahit bila ingin dipakai lebih lama."),
    row("tika", "yogya", "Kulot dari jeans bekas (upcycle)", "", "Bottom", "L", "Like New", 125000, "ULE", "1604176354204-9268737828e4",
        "Dibuat dari dua celana jeans bekas yang disambung menjadi kulot lebar. Satu-satunya model ini."),
    row("nina", "bogor", "Celana bahan hitam slim", "Zara", "Bottom", "M", "Like New", 140000, "LE", "1624378439575-d8705ad7ae80",
        "Potongan rapi untuk kerja. Sudah disetrika uap dan tidak ada bekas lipatan."),
    row("dewi", "denpasar", "Celana pull-on biru keabuan", "Uniqlo", "Bottom", "L", "Good", 85000, "LE", "1506629082955-511b1aa562c8",
        "Pinggang karet, ada dua saku samping. Adem untuk cuaca panas."),
    row("bagas", "malang", "Celana kulot garis hitam putih", "Stradivarius", "Bottom", "S", "Like New", 110000, "LE", "1509631179647-0177331693ae",
        "Motif garis tegas, kaki lebar. Dipakai dua kali untuk foto, selebihnya tersimpan."),
    row("raka", "bekasi", "Celana jogger kuning mustard", "Bershka", "Bottom", "M", "Good", 90000, "E", "1515886657613-9f3515b0c78f",
        "Warna cerah yang masih segar. Bisa dibeli bersama atasannya, tanya penjual."),
    # --- Dress
    row("nina", "bandung", "Dress wrap motif bunga", "Mango", "Dress", "M", "Like New", 185000, "LE", "1496747611176-843222e1e57c",
        "Model wrap dengan tali di pinggang, bahan jatuh dan tidak menerawang. Cantik untuk piknik atau kondangan siang."),
    row("dewi", "depok", "Dress merah selutut", "Zara", "Dress", "S", "Good", 150000, "LE", "1572804013309-59a88b7e92f1",
        "Merah berani dengan pita di pinggang. Ritsleting belakang lancar."),
    row("bagas", "surabaya", "Gaun panjang merah untuk pesta", "", "Dress", "L", "Good", 275000, "E", "1595777457583-95e059d581b8",
        "Rok lebar yang berputar indah. Pernah dipakai satu kali pemotretan. Dry clean sudah dilakukan."),
    row("raka", "jaksel", "Dress off-shoulder ungu", "H&M", "Dress", "XS", "Like New", 160000, "LE", "1566174053879-31528523f8ae",
        "Bagian bahu dilengkapi karet agar tidak melorot. Warna ungu tua yang elegan."),
    row("tika", "yogya", "Dress denim kancing depan", "Pomelo", "Dress", "M", "Good", 135000, "LE", "1591369822096-ffd140ec948f",
        "Denim ringan dengan kancing sampai bawah. Nyaman untuk dipakai berjalan seharian."),
    row("dewi", "medan", "Dress beludru marun lengan panjang", "Mango", "Dress", "M", "Like New", 210000, "LE", "1585487000160-6ebcfceb0d03",
        "Beludru halus dengan kancing di dada. Hangat dan terlihat mewah, hanya dipakai satu musim."),
    row("nina", "bogor", "Dress linen sage tanpa lengan", "Cotton Ink", "Dress", "M", "Good", 120000, "E", "1496747611176-843222e1e57c",
        "Linen yang adem dan wajar kusutnya. Bagian ketiak bersih."),
    row("raka", "bekasi", "Dress slip satin hitam", "Zara", "Dress", "S", "Fair", 110000, "R", "1566174053879-31528523f8ae",
        "Satin licin dan jatuh. Jahitan di bahu kiri sedikit longgar dan perlu dirapikan."),
    row("bagas", "makassar", "Dress katun polos terracotta", "Uniqlo", "Dress", "L", "Good", 95000, "LE", "1572804013309-59a88b7e92f1",
        "Katun tebal tidak menerawang, ada saku di kedua sisi. Warnanya hangat dan mudah dipadukan."),
    row("tika", "semarang", "Dress midi bunga kecil", "Hijabenka", "Dress", "XL", "Good", 130000, "LE", "1591369822096-ffd140ec948f",
        "Motif bunga kecil di dasar krem. Panjang menutup betis, bahan tidak panas."),
    # --- Outerwear
    row("raka", "jaksel", "Jaket kulit sintetis hitam", "Zara", "Outerwear", "M", "Good", 320000, "LE", "1551028719-00167b16eac5",
        "Model biker dengan ritsleting miring. Lapisan dalam utuh, tidak ada kulit yang mengelupas."),
    row("bagas", "surabaya", "Bomber jacket terracotta", "Uniqlo", "Outerwear", "M", "Like New", 250000, "LE", "1591047139829-d91aecb6caea",
        "Ringan dan hangat, ritsleting lancar. Bagian rib masih kencang."),
    row("nina", "bandung", "Coat wol marun panjang", "Mango", "Outerwear", "S", "Good", 380000, "LE", "1483985988355-763728e1935b",
        "Wol campuran dengan kerah lebar. Cocok untuk perjalanan ke daerah dingin."),
    row("tika", "yogya", "Blazer kotak biru navy", "Massimo Dutti", "Outerwear", "M", "Like New", 420000, "LE", "1485968579580-b6d095142e6e",
        "Motif kotak halus, potongan rapi dan berlapis dalam penuh. Sudah dicuci kering."),
    row("dewi", "depok", "Parka olive dengan tudung", "Uniqlo", "Outerwear", "L", "Good", 220000, "LE", "1529139574466-a303027c1d8b",
        "Tahan gerimis dan punya banyak saku. Tali tudung masih lengkap."),
    row("nina", "bogor", "Blazer krem oversize", "Zara", "Outerwear", "L", "Like New", 290000, "LE", "1571513722275-4b41940f54b8",
        "Potongan longgar yang masih rapi di bahu. Krem netral mudah dipadukan."),
    row("raka", "bekasi", "Jaket denim klasik", "Levi's", "Outerwear", "M", "Good", 260000, "LE", "1445205170230-053b83016050",
        "Denim padat dengan kancing logam. Warna memudar alami di siku."),
    row("tika", "malang", "Cardigan rajut abu-abu", "Uniqlo", "Outerwear", "L", "Good", 120000, "E", "1556905055-8f358a7a47b2",
        "Rajutan halus dan tidak berbulu. Kancing lengkap, cocok untuk ruang kantor yang dingin."),
    row("bagas", "malang", "Windbreaker hitam tipis", "Nike", "Outerwear", "M", "Needs Repair", 45000, "R", "1529139574466-a303027c1d8b",
        "Ritsleting macet di bagian atas dan perlu diganti. Bahan dan jahitan lainnya masih baik."),
    row("dewi", "denpasar", "Coat camel panjang", "COS", "Outerwear", "M", "Like New", 450000, "LE", "1445205170230-053b83016050",
        "Camel klasik dengan potongan oversized dan dua kancing tanduk. Dipakai sekitar empat kali."),
    # --- Modest Wear
    row("tika", "yogya", "Outer panjang biru pastel", "Ria Miranda", "Modest Wear", "M", "Like New", 230000, "LE", "1539109136881-3be0616acf4b",
        "Panjang sampai bawah lutut dengan ikat pinggang. Bahan jatuh dan tidak menerawang."),
    row("nina", "bandung", "Gamis beludru marun", "Zoya", "Modest Wear", "L", "Good", 260000, "LE", "1585487000160-6ebcfceb0d03",
        "Beludru lembut dengan kancing depan sampai pinggang. Cocok untuk acara malam."),
    row("dewi", "depok", "Gamis flowy sage dengan dupatta", "Elzatta", "Modest Wear", "M", "Like New", 280000, "LE", "1583391733956-3750e0ff4e8b",
        "Rok berlapis yang jatuh indah beserta selendang tipis. Dipakai satu kali untuk acara keluarga."),
    row("bagas", "surabaya", "Tunik panjang navy lengan panjang", "Hijabenka", "Modest Wear", "L", "Good", 120000, "E", "1544717305-2782549b5136",
        "Potongan lurus dengan lengan panjang rapi. Bahan menyerap keringat."),
    row("raka", "jaksel", "Tunik rajut panjang krem", "Rabbani", "Modest Wear", "XL", "Good", 100000, "LE", "1558769132-cb1aea458c5e",
        "Rajutan tipis yang adem. Panjang menutup pinggul."),
    row("dewi", "medan", "Abaya putih bersih", "Dian Pelangi", "Modest Wear", "M", "Like New", 310000, "LE", "1583391733956-3750e0ff4e8b",
        "Putih bersih dengan lengan lebar. Dipakai satu kali untuk acara kajian."),
    row("tika", "semarang", "Gamis katun polos hitam", "Zoya", "Modest Wear", "XXL", "Good", 180000, "LE", "1539109136881-3be0616acf4b",
        "Katun tebal tidak transparan, ada saku di sisi. Sudah dicuci dan disetrika."),
    row("nina", "bogor", "Setelan kulot dan tunik", "Elzatta", "Modest Wear", "M", "Good", 190000, "LE", "1544717305-2782549b5136",
        "Satu set, atasan dan kulot sewarna. Bisa dipakai terpisah."),
    row("raka", "bekasi", "Rok plisket panjang hitam", "Hijabenka", "Modest Wear", "M", "Like New", 95000, "LE", "1585487000160-6ebcfceb0d03",
        "Plisket rapi dengan karet pinggang. Panjang sampai mata kaki."),
    row("bagas", "makassar", "Kemeja koko putih lengan panjang", "Rabbani", "Modest Wear", "L", "Good", 85000, "E", "1523381210434-271e8be1f52b",
        "Kerah koko dengan kancing tersembunyi. Dua kali dipakai untuk Jumatan."),
]

# ---------------------------------------------------------------- 10 listing yang sudah terjual (mengisi etalase profil)
SOLD = [
    row("nina", "bandung", "Kemeja linen biru langit", "Uniqlo", "Top", "M", "Like New", 90000, "LE", "1523381210434-271e8be1f52b",
        "Sudah laku. Linen ringan berwarna biru langit.", sold_days_ago=3),
    row("nina", "bogor", "Dress rajut hijau", "Mango", "Dress", "S", "Good", 140000, "E", "1496747611176-843222e1e57c",
        "Sudah laku. Rajut halus dengan kancing di punggung.", sold_days_ago=12),
    row("raka", "jaksel", "Kaos band vintage", "", "Top", "L", "Fair", 60000, "RE", "1503342217505-b0a15ec3261c",
        "Sudah laku. Sablon memudar sesuai gaya vintage.", sold_days_ago=5),
    row("raka", "bekasi", "Jaket varsity biru tua", "Pull&Bear", "Outerwear", "M", "Good", 230000, "LE", "1445205170230-053b83016050",
        "Sudah laku. Lengan kulit sintetis dengan bordir huruf.", sold_days_ago=20),
    row("tika", "yogya", "Jeans mom fit", "Levi's", "Bottom", "M", "Good", 160000, "LE", "1541099649105-f69ad21f3246",
        "Sudah laku. Pinggang tinggi, kaki lurus.", sold_days_ago=8),
    row("tika", "malang", "Cardigan oversized abu tua", "Uniqlo", "Outerwear", "XL", "Like New", 130000, "LE", "1556905055-8f358a7a47b2",
        "Sudah laku. Rajut tebal yang hangat.", sold_days_ago=15),
    row("bagas", "surabaya", "Celana cargo hijau army", "Bershka", "Bottom", "L", "Good", 110000, "E", "1473966968600-fa801b869a1a",
        "Sudah laku. Saku di samping banyak.", sold_days_ago=2),
    row("bagas", "makassar", "Gamis motif kecil biru", "Zoya", "Modest Wear", "L", "Good", 170000, "LE", "1539109136881-3be0616acf4b",
        "Sudah laku. Katun adem dengan motif bunga kecil.", sold_days_ago=25),
    row("dewi", "depok", "Dress batik modern", "", "Dress", "M", "Like New", 200000, "LE", "1583391733956-3750e0ff4e8b",
        "Sudah laku. Batik tulis dalam potongan modern.", sold_days_ago=9),
    row("dewi", "medan", "Tunik bordir putih", "Elzatta", "Modest Wear", "M", "Good", 115000, "LE", "1544717305-2782549b5136",
        "Sudah laku. Bordir halus di bagian dada.", sold_days_ago=30),
]
