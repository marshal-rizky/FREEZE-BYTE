# FREEZE BYTE

Analisis suspensi perdagangan IDX. Entri Sectors Hackathon 2026, Track 03 Market Intelligence.

Dua pilar di atas satu mesin fitur yang sama: anatomi forensik seluruh pembekuan yang
tercatat, dan daftar pantau emiten hari ini yang kondisinya menyerupai kejadian-kejadian itu.

## Menjalankan situs tanpa API key

Seluruh data hasil build sudah di-commit di `data/web/`. Situs statis membacanya langsung.

```bash
python -m http.server 8000
# buka http://localhost:8000/site/
```

## Menjalankan ulang pipeline (butuh API key)

```bash
cp .env.example .env    # isi SECTORS_API_KEY
pip install -r requirements.txt
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
