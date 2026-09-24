# FREEZE BYTE

Analisis suspensi perdagangan IDX. Entri Sectors Hackathon 2026, Track 03 Market Intelligence.

Dua pilar di atas satu mesin fitur yang sama: anatomi forensik seluruh pembekuan yang
tercatat, dan daftar pantau emiten hari ini yang kondisinya menyerupai kejadian-kejadian itu.

## Ekstensi browser

FREEZE BYTE menandai saham IDX yang berada di zona tempat bursa secara historis
membekukan perdagangan, di Stockbit, TradingView, Google Finance, IDX, Sectors,
RTI, Investing.com, dan situs lain yang Anda aktifkan sendiri.

Tanpa API key, tanpa jaringan: seluruh data dibawa ekstensi.

**Pasang (Load unpacked):**
1. Unduh `freeze-byte-extension-<versi>.zip` dari halaman Releases, lalu ekstrak.
2. Buka `chrome://extensions` dan nyalakan Developer mode.
3. Klik "Load unpacked" dan pilih folder hasil ekstrak.
4. Buka halaman saham di Stockbit atau TradingView.

Lencana merah: di zona suspensi. Lencana kuning: mendekati zona. Tanpa lencana:
tidak dikenali, bukan berarti aman. Klik lencana untuk hitungan dan tautan bukti.

Halaman bukti: https://marshal-rizky.github.io/FREEZE-BYTE/site/

**Bangun ulang data** (butuh `SECTORS_API_KEY` di `.env`, memakan kredit):
`etl_suspensions.py` → `etl_prices.py` → `etl_overviews.py` →
`report_discovery.py` (salin tercile ke `baserates.py`) →
`etl_universe.py --count` lalu `--run` → `python -m freezebyte.build` →
`report_validation.py` → `python -m freezebyte.export_extension`.

**Bukan saran investasi.** Hitungan historis, bukan peluang. Tidak mengeksekusi order.

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

## Coverage

Dataset suspensi penuh berisi **595 record**. Dari situ, **120 masuk sampel forensik**
(60 kejadian + 60 kontrol, dibatasi anggaran kredit API), dan dari 120 itu **112
dianalisis, 8 dikecualikan**. Rincian lengkap alasan pengecualian per emiten, daftar
pantau terpisah, dan distribusi kategori alasan suspensi ada di bagian coverage pada
situs (`site/`, dibangun dari `data/web/coverage.json`).

## Batasan yang diakui

- Tag emiten bersifat kondisi sekarang. Tidak ada cara menanyakan tag pada tanggal
  lampau, jadi fitur struktural pada analisis forensik memakai nilai sekarang
  sebagai perkiraan.
- Pembekuan adalah peristiwa jarang. Framing yang dipakai bersifat kondisional dan
  berbasis frekuensi, bukan prediksi individual.
- Data order book tidak tersedia, jadi spoofing dan wash trade tidak bisa dideteksi.
- Sampel forensik dibatasi kejadian terbaru karena anggaran kredit API.
- Sampel base rate adalah desain case-control ~1:1 (kejadian vs kontrol), bukan
  sampel populasi acak. Porsi bucket memisahkan kedua kelompok itu, bukan
  frekuensi di dunia nyata.

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
node --test "extension/test/*.test.js"
```

Test berjalan offline memakai fixture di `tests/fixtures/`. Tidak butuh API key.

## Disclaimer

Bukan saran investasi. Produk ini bersifat deskriptif dan menyajikan statistik historis
serta frekuensi kondisional. Produk ini tidak merekomendasikan pembelian atau penjualan
efek apa pun, dan tidak mengeksekusi order.
