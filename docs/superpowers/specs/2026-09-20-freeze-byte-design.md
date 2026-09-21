# FREEZE BYTE — design spec

**Sectors Hackathon 2026 · Track 03 Market Intelligence**
Ditulis 2026-09-20. Submit 2026-09-30 23:59 WIB. Solo. Python.

---

## 1. Problem statement

> Investor ritel IDX membeli saham yang sedang lari tanpa tahu bahwa kombinasi float tipis, insider yang sedang menjual, dan harga di puncak adalah kondisi yang secara historis berakhir dengan saham dibekukan — dan saat beku, mereka tidak bisa keluar.

Kalimat ini masuk form submission dan jadi pembuka video. Fitur yang tidak melayani kalimat ini dipotong.

## 2. Apa yang dibangun

Dua pilar setara di atas **satu mesin fitur yang sama**:

1. **Forensik** — anatomi seluruh pembekuan IDX yang tercatat: apa yang terjadi pada harga dan volume sebelum saham dibekukan, dan apa yang terjadi saat dibuka kembali. Setiap kejadian punya PDF pengumuman resmi IDX sebagai bukti.
2. **Pantau hari ini** — mesin yang sama dijalankan pada emiten hari ini, menghasilkan daftar yang kondisinya menyerupai kejadian-kejadian lampau itu.

Yang membuat ini satu proyek dan bukan dua: `features.py` menerima `(price_series, as_of_date)` dan mengembalikan satu dict fitur. Forensik memanggilnya dengan `as_of` = sehari sebelum suspensi. Pantau memanggilnya dengan `as_of` = hari bursa terakhir. Kode yang sama.

Memenuhi syarat Track 3 — *"must produce derived insight: analysis generated from the data rather than the data itself"* — karena output utamanya fitur turunan, base rate, dan klasifikasi, bukan tampilan data.

## 3. Temuan data terverifikasi

Semua di bawah ini hasil panggilan API nyata pada 2026-09-19/20, bukan asumsi.

### 3.1 Endpoint suspensi

`fetch-suspensions`: **592 record**, paginated maks 30/halaman. Field: `symbol`, `suspension_date`, `reason` (teks resmi IDX), `pdf_url` (PDF pengumuman IDX). Filter: `symbol`, `start`, `end`.

Dari 10 record terbaru: 8 beralasan lonjakan harga / cooling down, 1 karena berada di papan pemantauan khusus lebih dari 1 tahun, 1 karena ketidakpastian kelangsungan usaha. **Distribusi di 592 record belum diketahui** — dihitung pada tahap ETL pertama, sebelum layer analisis ditulis.

Jadwal hari-per-hari tidak ada di dokumen ini; itu isi implementation plan.

### 3.2 Tag bisa dirangkai

```
where = tags in ['insider-1-month-sell'] and tags in ['public-float-under-25'] and tags in ['52-w-high']
```

Hasil: **2 emiten dari 962** — INPS dan MGLV. Keduanya disuspensi dalam 11 hari sebelum query (INPS 2026-09-17, MGLV 2026-09-09).

Pembanding: satu tag `insider-1-month-sell` = 44 emiten. Dua tag dengan OR = 541 emiten.

Semantik: `tags in [...]` dalam satu klausa berlaku **OR**; untuk AND rangkai klausa terpisah dengan `and`. Biaya 1 kredit per query, berapa pun jumlah tag.

**n=2 bukan bukti.** Ini pengamatan yang memicu investigasi, bukan angka akurasi. Tidak boleh ditampilkan sebagai "2 dari 2" di video atau README.

### 3.3 Volume nol sebagai jejak pembekuan

`fetch-daily-price` ALKA, 2026-08-20 s/d 2026-09-19:

| Tanggal | Close | Volume |
|---|---|---|
| 2026-09-07 | 3.750 | 136.900 |
| 2026-09-10 | 4.980 | 92.800 |
| 2026-09-14 | 6.225 | 435.800 |
| 2026-09-15 | 7.400 | 894.800 |
| 2026-09-16 | 7.400 | 0 |
| 2026-09-17 | 7.400 | 0 |
| 2026-09-18 | 7.400 | 0 |

> **Koreksi 2026-09-21 (setelah ETL penuh).** Jendela 24 Agustus – 2 September
> ternyata **tidak punya record suspensi resmi**; record ALKA hanya
> 2026-09-16, 2026-07-29, dan 2026-03-13. Jendela itu karena itu `inferred`,
> bukan `confirmed`, sehingga −9,8% tidak boleh disajikan sebagai reopen
> suspensi. Jendela `confirmed` 29 Juli reopen di +9,9%; pembekuan 16
> September masih berlangsung sampai baris data terakhir (18 September,
> 7.400, volume nol). Angka +97,3% dalam 6 hari bursa tetap benar.

Naik +97,3% dari 7 ke 15 September (6 hari bursa), lalu volume nol. Jendela beku sebelumnya di window yang sama: 24 Agustus – 2 September di 4.580, buka 3 September di 4.130 = **−9,8% saat dibuka**.

Data ini jadi fixture test utama. Jawaban yang benar sudah diketahui: dua jendela beku, dan reopen return −9,8%. (Lihat koreksi 2026-09-21 di atas: jendela 24 Agustus itu `inferred`, bukan `confirmed` — `test_reopen_return_alka` tetap benar karena hanya memverifikasi aritmetika reopen, bukan status konfirmasinya.)

### 3.4 Tag di `overview`

`fetch-company-report` sections=['overview'], 1 kredit. Contoh INPS:

```
tags: ["52-w-high", "90-d-high", "insider-1-month-sell",
       "public-float-under-25", "single-entity-holding-70", "ytd-high"]
```

Field lain yang dipakai: `all_time_price` (berisi `all_time_high/low`, `52_w_high/low`, `90_d_high/low`, `ytd_high/low`, masing-masing dengan tanggal), `market_cap`, `market_cap_rank`, `listing_date`, `listing_board`.

**Kosakata tag lengkap belum diketahui.** Dipetakan lewat sampling `overview` pada tahap ETL pertama.

### 3.5 Sudah dites dan gagal — jangan bangun di atasnya

| Hal | Hasil | Konsekuensi |
|---|---|---|
| `right_issue` di `fetch-corporate-actions` | `null` di BUMI dan TLKM | Coverage tidak bisa diandalkan. Angle dilusi mati. |
| Status papan pemantauan khusus | `listing_board` INPS = `"Development"` padahal INPS disuspensi karena berada di papan pemantauan khusus >1 tahun | Status PPK **bukan field**. Hanya bisa disimpulkan dari teks `reason`. |
| `fetch-listing-performance` | 404 untuk ALKA | Hanya emiten listing setelah Mei 2005. |
| `agm_result` | Terisi hanya di RUPS terakhir | Tidak ada deret waktu. Bukan pilar. |
| `fetch-company-segments` | Dekomposisi laporan laba rugi, bukan segmen bisnis per divisi | Opsional, prioritas rendah. |

### 3.6 Konteks regulasi (riset web, bukan API)

**Papan Pemantauan Khusus**, notasi **"X"**. Sejak **25 Maret 2024** seluruh saham di papan ini diperdagangkan lewat **Full Call Auction** — lelang berkala, bukan tawar-menawar kontinu. Akibatnya likuiditas turun, order tidak langsung tereksekusi, dan harga bisa jatuh sampai Rp1 karena batas bawah dilonggarkan.

Sekitar 11 kriteria masuk, cukup memenuhi satu. Pemicu tersering: harga rata-rata 6 bulan di bawah ~Rp51, likuiditas sangat tipis selama 6 bulan, opini auditor disclaimer, ekuitas negatif.

Notasi lain: **B** permohonan pailit/PKPU, **E** ekuitas negatif, **L** belum sampaikan laporan keuangan, **M** sedang PKPU, **S** tidak ada pendapatan usaha.

Jalur eskalasi yang terlihat di data: papan pemantauan khusus → 1 tahun → suspensi.

---

## 4. Arsitektur

```
freezebyte/
  client.py       fetch + cache ke disk. Satu-satunya yang menyentuh jaringan.
  freeze.py       deteksi jendela beku dari deret volume==0. Fungsi murni.
  features.py     MESIN. (price_series, as_of) -> dict fitur. Fungsi murni.
  baserates.py    bucket kejadian, hitung base rate. Fungsi murni.
  build.py        orkestrasi. Baca cache, jalankan mesin, tulis data/web/*.json
data/
  raw/            cache mentah per endpoint, tidak di-commit
  web/            output build, DI-COMMIT
site/             HTML/CSS/JS statis, baca data/web/*.json
tests/            pytest + fixture ALKA
```

Aliran data satu arah, tanpa loop:

```
Sectors API -> client (cache) -> freeze + features -> baserates -> data/web/*.json -> site
```

Situs statis membaca JSON yang sudah di-commit. **Juri bisa clone dan menjalankan tanpa API key dan tanpa kredit.** Ini keputusan sengaja, bukan kebetulan.

**Tanpa LLM.** Track 3 tidak mewajibkannya dan penambahannya hanya menambah titik gagal.

## 5. Kontrak antar komponen

### `client.py`

Satu tugas: ambil data, cache ke disk, jangan pernah memanggil endpoint yang sama dua kali.

```
get_suspensions() -> list[dict]
get_prices(symbol: str, end: date) -> list[dict]     # window 90 hari berakhir di end
get_overview(symbol: str) -> dict
screen(where: str, limit: int) -> list[dict]
```

Cache key = nama endpoint + parameter. Miss baru memanggil jaringan. Bergantung pada: `requests`, disk. Bisa dites dengan mem-mock lapisan HTTP.

### `freeze.py`

Satu tugas: dari deret harga, kembalikan daftar jendela beku. Tidak tahu apa-apa soal API maupun UI.

```
detect_freeze_windows(rows: list[dict], min_days: int = 1) -> list[FreezeWindow]
```

`FreezeWindow` berisi `start_date`, `end_date`, `n_days`, `price_at_freeze`, `reopen_close`, `reopen_return`, `confirmed` (bool).

**Algoritma.** Sebuah baris dianggap beku kalau `volume == 0`. Jendela beku adalah deret berurutan maksimal dari baris beku, diukur **berdasarkan urutan baris, bukan selisih kalender** — baris yang tidak ada berarti hari non-bursa, bukan hari beku. `reopen_return` = close baris non-beku pertama setelah jendela dibagi close baris beku terakhir, minus 1.

**Peringatan penting.** `volume == 0` pada saham yang sangat tidak likuid bisa berarti tidak ada transaksi, bukan suspensi. Karena itu setiap jendela di-cross-check terhadap record `fetch-suspensions` untuk emiten yang sama: `confirmed = True` kalau ada record suspensi yang tanggalnya jatuh di dalam jendela itu, `False` kalau hanya tersimpulkan dari volume. **UI wajib membedakan keduanya.** Ini bukan detail kosmetik — mencampur keduanya berarti mengklaim pembekuan yang tidak pernah terjadi.

`min_days` default 1 supaya jendela satu hari tetap terdeteksi, tapi **seluruh angka forensik dan base rate dihitung hanya dari jendela `confirmed`.** Jendela `inferred` hanya ditampilkan sebagai konteks pada grafik per emiten, dengan gaya visual berbeda, dan tidak pernah masuk statistik.

### `features.py`

Fungsi murni, tanpa I/O. Inti proyek.

```
compute_features(rows: list[dict], as_of: date) -> dict
```

Fitur dari data harga, tersedia historis:

| Fitur | Definisi |
|---|---|
| `ret_5d`, `ret_10d`, `ret_20d` | `close[as_of] / close[as_of - N baris] - 1`, offset baris bukan kalender |
| `vol_ratio` | `volume[as_of]` dibagi rata-rata volume 20 baris sebelumnya, **baris ber-volume nol dikeluarkan dari rata-rata** |
| `dist_from_high` | `close[as_of]` dibagi `max(high)` dari 90 baris terakhir sampai `as_of`, **baris dengan `high == 0` dibuang** |
| `prior_freeze_count` | jumlah jendela beku sebelum `as_of` |
| `consecutive_up_days` | panjang deret hari naik terakhir |

Fitur struktural dari `overview` — **kondisi sekarang, bukan historis, dan wajib ditandai begitu di UI**: float di bawah 25%, satu entitas memegang 70%, insider menjual sebulan terakhir.

**Jebakan data yang harus ditangani eksplisit.** Baris dengan `volume == 0` mengacaukan rata-rata volume kalau tidak dikeluarkan. Baris dengan `high == 0` dan `open == 0` muncul di data nyata (ALKA 2026-09-18) dan akan merusak `dist_from_high` kalau ikut dihitung. Dua-duanya harus difilter, dan filternya harus punya test sendiri.

### `baserates.py`

```
bucket(features: dict) -> str
base_rate(events: list[Event], bucket: str) -> BaseRate
```

Kejadian dikelompokkan berdasarkan `ret_10d` dan `vol_ratio`. `BaseRate` berisi `n`, `n_frozen_within_30d`, `median_reopen_return`.

`n_frozen_within_30d` dihitung dalam **30 hari kalender** sejak `as_of`, bukan 30 baris bursa, supaya bisa dibandingkan dengan tanggal suspensi resmi apa adanya.

**Batas bucket ditetapkan dari distribusi yang teramati** — tercile `ret_10d` dan tercile `vol_ratio` dari sampel yang berhasil ditarik, menghasilkan 9 bucket. Batasnya tidak dikarang di muka; dihitung setelah ETL pertama selesai, lalu dituliskan sebagai konstanta di kode dengan komentar yang menyebut dari sampel mana angka itu berasal.

**Aturan: kalau `n` terlalu kecil untuk suatu bucket, tampilkan "sampel tidak cukup", bukan angka.** Ambang: n < 10.

## 6. Penanganan error dan laporan coverage

Setiap pengecualian **dihitung dan ditampilkan**, tidak pernah dibuang diam-diam.

- 404 dari endpoint (misal listing sebelum Mei 2005) — catat sebagai tidak tersedia, lanjut, masuk hitungan coverage
- Data harga tidak cukup jauh ke belakang — keluarkan dari sampel, catat alasannya
- Emiten tanpa tag — catat, jangan asumsikan nilai default

Halaman punya satu bagian coverage: dari 592 kejadian, berapa yang benar-benar bisa dianalisis, dan berapa gugur karena apa. Sebagian besar peserta akan menyembunyikan angka ini; menampilkannya yang membuat produk terbaca jujur, dan kriteria technical depth menilai apakah proyeknya nyata atau dipoles untuk demo.

## 7. Testing

`pytest`. Fixture di-commit sebagai JSON supaya test jalan offline tanpa API key.

| Test | Yang diuji | Jawaban yang sudah diketahui |
|---|---|---|
| `test_freeze_alka` | `detect_freeze_windows` pada fixture ALKA | 2 jendela: 2026-08-24 s/d 2026-09-02, dan 2026-09-16 ke depan |
| `test_reopen_return_alka` | reopen return jendela pertama | −9,8% (4.580 → 4.130) (jendela `inferred`, bukan `confirmed` — lihat koreksi 2026-09-21 di §3.3) |
| `test_features_alka` | `ret_10d` pada as_of 2026-09-15 | +97,3% dari 3.750 (2026-09-07) |
| `test_vol_ratio_excludes_frozen` | baris volume nol tidak masuk rata-rata | rata-rata dihitung dari baris berdagang saja |
| `test_dist_from_high_ignores_zero_high` | baris `high == 0` dibuang | tidak ada pembagian dengan nol atau hasil sesat |
| `test_confirmed_vs_inferred` | cross-check ke record suspensi | jendela ALKA 16 Sep = confirmed |
| `test_base_rate_small_sample` | bucket dengan n < 10 | mengembalikan "sampel tidak cukup" |

Test untuk `freeze.py` dan `features.py` ditulis **sebelum** implementasinya, karena jawabannya sudah kita tahu dari data ALKA.

## 8. Tampilan

Satu halaman, tiga bagian, urutan menentukan.

**Bagian 1 — studi kasus ALKA, terbuka saat halaman dimuat.** Grafik harga 20 Agustus – 19 September, dua jendela beku diberi shading dan label, anotasi +97,3% dan −9,8% saat dibuka (jendela −9,8% itu `inferred`, bukan `confirmed` — lihat koreksi 2026-09-21 di §3.3). Pembaca harus paham produknya dalam sepuluh detik tanpa mengklik apa pun.

**Bagian 2 — anatomi pembekuan.** Distribusi alasan resmi, sebaran kenaikan harga sebelum pembekuan dibanding kelompok kontrol, median perubahan harga saat dibuka. Setiap kejadian menampilkan `pdf_url` ke pengumuman resmi IDX. Link itu aset kredibilitas terbesar produk ini — tampilkan, jangan sembunyikan di tooltip.

**Bagian 3 — pantau hari ini.** Daftar emiten yang kondisinya menyerupai, dengan komponen pembentuknya sebagai chip, base rate di sampingnya, dan label status pengujian yang jujur.

Setiap fitur struktural diberi penanda "kondisi sekarang" supaya tidak terbaca sebagai data historis.

## 9. Anggaran kredit (total 1.000)

| Pos | Kredit |
|---|---|
| Tarik seluruh suspensi (20 halaman) | 20 |
| Eksperimen screener tag | 25 |
| Sampling `overview` untuk kosakata tag (60 emiten) | 60 |
| Harga historis, 60 kejadian suspensi | 60 |
| Harga historis, 60 kontrol | 60 |
| `overview` kandidat aktif (~80 emiten) | 80 |
| Refresh data final sebelum submit | 150 |
| **Subtotal** | **455** |
| Cadangan | 545 |

Aturan keras: **cache setiap respons ke disk sebelum diolah.** Jangan pakai parameter `?q=` natural language — 3 kredit, versi terstruktur 1 kredit.

Catatan: `fetch-daily-price` maks 90 hari per panggilan, tapi window bisa digeser ke masa lalu lewat parameter `end`. Untuk 592 kejadian butuh 592 panggilan, jadi sampel dibatasi ~60 kejadian terbaru ditambah ~60 kontrol. Pembatasan ini disebutkan terbuka di halaman coverage.

## 10. Batasan yang diakui

- **Tag bersifat kondisi-sekarang.** Tidak ada cara menanyakan tag apa yang dimiliki sebuah emiten pada tanggal lampau. Fitur struktural pada analisis forensik memakai nilai sekarang sebagai perkiraan, dan itu dinyatakan di halaman.
- **Pembobotan setara** antar komponen sebagai konvensi prototype, bukan hasil riset kuantitatif.
- **Pembekuan adalah peristiwa jarang.** Base rate absolutnya rendah, jadi framing yang benar bersifat kondisional dan berbasis frekuensi, bukan prediksi individual.
- **Data order book tidak tersedia** di Sectors. Spoofing dan wash trade tidak bisa dideteksi. Jangan janjikan.
- Sampel forensik dibatasi ~60 kejadian dari 592 karena anggaran kredit.

## 11. Kepatuhan

Aturan melarang financial advice dan eksekusi trade otomatis. Kalimat aman: *"dari N kejadian dengan profil serupa, M berakhir dibekukan dalam 30 hari"*. Kalimat yang dilarang: *"hindari saham ini"*, *"jual sekarang"*.

Disclaimer "bukan saran investasi" wajib ada di halaman dan README.

Repo `Stocklens` milik penulis tidak boleh jadi sumber kode — aturan melarang memakai kode dari project sebelumnya. Seluruh kode di repo ini ditulis dalam build period.

Setelah submit, repo freeze total: tidak ada commit, push, atau edit, termasuk bugfix. Satu-satunya pengecualian adalah kebocoran kredensial — lapor Slack #support, rotate dulu, lalu push commit yang isinya hanya penghapusan.

## 12. Non-goals

Akun pengguna. Portofolio tersimpan. Integrasi sekuritas. Alert real-time atau bot Telegram (itu Track 2, dan sudah ada `OkyWoww/sentinel-flow` plus Matrix Saham komersial). Layer chat LLM. Aplikasi mobile. Prediksi harga. Data order book. Analisis SGX/KLSE.

## 13. Risiko

| Risiko | Mitigasi |
|---|---|
| Sinyal historis ternyata lemah | Pilar prediktif tidak hilang, hanya berubah label jadi "daftar pantau, akurasi belum diketahui" dengan snapshot bertanggal di repo. Diputuskan segera setelah ETL pertama, bukan di minggu kedua. |
| n=2 ternyata kebetulan | Jangan pernah tampilkan sebagai angka akurasi. Sebut sebagai pengamatan awal, lalu tunjukkan angka dari sampel penuh. |
| `volume == 0` disalahartikan sebagai suspensi pada saham tidak likuid | Cross-check wajib ke record suspensi, label `confirmed` vs `inferred` di UI. |
| Data harga tidak tersedia cukup jauh ke belakang | Dites di panggilan API pertama, sebelum kode analisis ditulis. Kalau gagal, batasi ke kejadian dalam 90 hari terakhir dan katakan terus terang. |
| Waktu habis di analisis, video terbengkalai | Video dapat dua hari penuh di implementation plan. Bobotnya 30%, sama besar dengan technical depth. |

## 14. Lanskap pesaing per 2026-09-20

11 repo hackathon sudah publik; ini batas bawah karena sebagian besar tim menyimpan repo privat sampai submit.

Penumpukan terbesar: **mining 3 entri** (`RicoRafael/aliran`, `mocharil/gali`, `rxseven36-hub/rx-mining-divergence-investigator`), **aliran dana 2 entri** (`johnhendrickh/arus-idx`, `RahmatAbdurrahman/arus-terminal-v2`). Portofolio: `Fresky21/pekaporto` (overlap sektor penghasilan vs portofolio, level sektor saja). Track 1 terkuat: `autokeren/kerenscope`.

**Suspensi, pembekuan, papan pemantauan khusus: nol entri.** Pencarian GitHub kosong, tidak ada produk komersial.

Produk komersial Indonesia yang relevan sebagai pesaing pasar, bukan pesaing hackathon: SENTRIDX dan StockMap (ownership map dari data KSEI), Matrix Saham (bot Telegram, alert KSEI ownership diff dan foreign flow anomaly), TraderTekno (daily brief otomatis), The Thesis (asisten AI riset). Tidak ada yang menggarap suspensi.
