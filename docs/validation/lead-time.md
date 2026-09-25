# Kurva tenggang dan holdout temporal

Digenerate oleh `scripts/report_validation.py`. Jangan disunting tangan.

Ambang TINGGI: `ret_10d` ≥ 0.318182. Ambang SEDANG: 0.20 ≤ `ret_10d` < 0.318182 (batas bawah dipilih tetap, bukan diestimasi). Ambang yang sama dipakai di semua jarak.

## Kurva tenggang

| Jarak | Kejadian TINGGI | Kejadian SEDANG | Kejadian terukur | Kontrol TINGGI | Kontrol SEDANG | Kontrol terukur |
|---|---|---|---|---|---|---|
| T−1 | 37 | 4 | 55 | 0 | 2 | 57 |
| T−3 | 27 | 5 | 55 | 0 | 1 | 57 |
| T−5 | 17 | 9 | 55 | 1 | 0 | 57 |
| T−10 | 14 | 7 | 55 | 0 | 3 | 57 |

## Holdout temporal

Tercile dihitung dari 36 kejadian dan 40 kontrol dengan tanggal suspensi sebelum 2026-08-28. Ambang TINGGI hasilnya: 0.195980.

- Kejadian uji yang tertangkap TINGGI: 17 dari 19.
- Kontrol uji yang salah tertangkap TINGGI: 1 dari 17.

Sampel ini case-control 1:1. Hitungan di atas bukan peluang sebuah saham dibekukan.

Ambang yang sungguh dipakai ekstensi (0.318182) berbeda dari ambang refit di atas, karena ambang yang dipakai ekstensi dipasang dari data yang mencakup split uji ini juga. Pada ambang itu, kejadian uji yang tertangkap TINGGI: 16 dari 19. Kontrol uji yang salah tertangkap TINGGI: 0 dari 17.

## Gugur

- LCKM.JK: hanya 13 baris berdagang
- INCF.JK: hanya 10 baris berdagang
- ZINC.JK: hanya 13 baris berdagang
- WBSA.JK: hanya 20 baris berdagang
- BIMA.JK: hanya 0 baris berdagang
- ADCP.JK: hanya 0 baris berdagang
- BSWD.JK: hanya 15 baris berdagang
- DIGI.JK: hanya 0 baris berdagang
