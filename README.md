# FREEZE BYTE

Analisis suspensi perdagangan IDX. Entri Sectors Hackathon 2026, Track 03 Market Intelligence.

Dua pilar di atas satu mesin fitur yang sama: anatomi forensik seluruh pembekuan yang
tercatat, dan daftar pantau emiten hari ini yang kondisinya menyerupai kejadian-kejadian itu.

## Masalah yang diselesaikan

Investor ritel IDX membeli saham yang sedang lari tanpa tahu bahwa kombinasi float
tipis, insider yang sedang menjual, dan harga di puncak adalah kondisi yang secara
historis berakhir dengan saham dibekukan — dan saat beku, mereka tidak bisa keluar.

## Cara kerjanya

`features.py` menerima `(price_series, as_of_date)` dan mengembalikan satu dict fitur.
Analisis forensik memanggilnya dengan `as_of` sehari sebelum suspensi. Daftar pantau
memanggilnya dengan `as_of` hari bursa terakhir. Kode yang sama, dua sudut pandang.

Jendela beku dideteksi dari deret `volume == 0`, lalu di-cross-check terhadap record
suspensi resmi. Jendela `confirmed` punya record resmi di dalam rentangnya; jendela
`inferred` hanya tersimpulkan dari volume dan tidak pernah masuk statistik.

## Sumber data

Sectors API v2: `/v2/suspensions/`, `/v2/daily/{symbol}/`, `/v2/company/report/{symbol}/`,
`/v2/companies/`. Produk ini kehilangan seluruh fungsinya tanpa data Sectors.

## Batasan yang diakui

- Tag emiten bersifat kondisi sekarang. Tidak ada cara menanyakan tag pada tanggal
  lampau, jadi fitur struktural pada analisis forensik memakai nilai sekarang
  sebagai perkiraan.
- Pembekuan adalah peristiwa jarang. Framing yang dipakai bersifat kondisional dan
  berbasis frekuensi, bukan prediksi individual.
- Data order book tidak tersedia, jadi spoofing dan wash trade tidak bisa dideteksi.
- Sampel forensik dibatasi kejadian terbaru karena anggaran kredit API.

## Menjalankan situs tanpa API key

Seluruh data hasil build sudah di-commit di `data/web/`. Situs statis membacanya langsung.

```bash
python -m http.server 8000
# buka http://localhost:8000/site/
```

Situs harus dibuka lewat server lokal ini, bukan dengan membuka `site/index.html`
langsung sebagai file `file://`: `fetch()` diblokir CORS pada skema `file://`,
dan halaman akan menampilkan pesan "gagal memuat".

## Menjalankan ulang pipeline (butuh API key)

```bash
cp .env.example .env    # isi SECTORS_API_KEY
pip install -r requirements.txt
pip install -e .        # supaya `freezebyte` bisa di-import dari scripts/
python scripts/etl_suspensions.py
python scripts/etl_prices.py
python scripts/etl_overviews.py
python -m freezebyte.build
```

## Test

```bash
python -m pytest
```

Test berjalan offline memakai fixture di `tests/fixtures/`. Tidak butuh API key.

## Disclaimer

Bukan saran investasi. Produk ini bersifat deskriptif dan menyajikan statistik historis
serta frekuensi kondisional. Produk ini tidak merekomendasikan pembelian atau penjualan
efek apa pun, dan tidak mengeksekusi order.
