# Discovery: dataset suspensi

Dijalankan 2026-09-21. Sumber: `GET /v2/suspensions/`, 20 halaman, 20 kredit.
Klasifikasi ulang di bawah dihitung dari cache lokal `data/raw/suspensions/all.json`
(592 record) tanpa panggilan jaringan tambahan.

| Angka | Nilai |
|---|---|
| Total record | 592 |
| Emiten unik | 332 |
| Record dengan `pdf_url` | 592 dari 592 |
| Tanggal tertua | 2018-12-28 |
| Tanggal terbaru | 2026-09-17 |

Catatan: endpoint mengembalikan simbol bersufiks bursa (mis. `UDNG.JK`, `MGLV.JK`),
sehingga `build.py` membandingkan simbol lewat `_base()` (memotong sufiks `.JK` dan
menyamakan huruf besar/kecil) alih-alih perbandingan string langsung.

## Distribusi alasan

Sebelum Task 5 Step 7 (enam kategori awal):

| Kategori | Jumlah | Proporsi |
|---|---|---|
| lonjakan_harga | 467 | 78.9% |
| lainnya | 93 | 15.7% |
| keterbukaan_informasi | 16 | 2.7% |
| papan_pemantauan_khusus | 8 | 1.4% |
| kelangsungan_usaha | 8 | 1.4% |

Setelah Task 5 Step 7 (tiga kategori baru ditambahkan ke `freezebyte/reasons.py`):

| Kategori | Jumlah | Proporsi |
|---|---|---|
| lonjakan_harga | 467 | 78.9% |
| suspensi_berkepanjangan | 56 | 9.5% |
| ketentuan_pencatatan | 32 | 5.4% |
| keterbukaan_informasi | 16 | 2.7% |
| papan_pemantauan_khusus | 8 | 1.4% |
| kelangsungan_usaha | 8 | 1.4% |
| aksi_korporasi_delisting | 4 | 0.7% |
| lainnya | 1 | 0.2% |
| **Total** | **592** | **100.0%** |

`lainnya` turun dari 15.7% menjadi 0.2%, di bawah gerbang 10% pada plan.
`lonjakan_harga` tidak berubah (masih tepat 467 record) — kata kunci baru tidak
mencuri dari kategori dominan.

## Yang masih masuk kategori "lainnya"

Satu record, emiten **ZINC.JK**:

> "Perseroan telah menunda pembayaran amortisasi pokok ke-12 dan bunga ke-24 dari
> Obligasi I Kapuas Prima Coal Tahun 2018 (ZINC01E) yang seharusnya efektif
> dibayarkan pada tanggal 13 Februari 2025"

Ini adalah gagal bayar kupon/amortisasi obligasi korporasi — bukan gejolak harga,
bukan keraguan kelangsungan usaha generik, bukan pelanggaran ketentuan pencatatan,
dan bukan aksi korporasi menuju delisting. Teks ini unik (hanya satu record di
seluruh 592), sehingga sengaja **tidak** diberi kata kunci baru: membuat kategori
khusus atau menambah keyword untuk satu record adalah overfitting pada kosakata
sampel, bukan generalisasi yang berguna. Kategori `lainnya` pada 0.2% (1 dari 592)
dianggap dapat diterima secara permanen.

## Kata kunci baru dan urutan aturan

Ditambahkan ke `RULES` di `freezebyte/reasons.py`, setelah keempat aturan lama
(`lonjakan_harga`, `kelangsungan_usaha`, `papan_pemantauan_khusus`,
`keterbukaan_informasi`), karena `classify()` mengembalikan hasil pada kecocokan
pertama:

- `suspensi_berkepanjangan`: `"suspend more than 6 month"` — 56 record, teks
  endpoint berbahasa Inggris untuk suspensi berjalan lebih dari 6 bulan. Ini
  adalah status durasi, bukan sinyal harga atau kelangsungan usaha.
- `ketentuan_pencatatan`: `"belum memenuhi ketentuan"`, `"peraturan bursa nomor
  i-a"` (pelanggaran Peraturan I-A V.1.1/V.1.2, 25 record), dan
  `"keterlambatan pembayaran"` (keterlambatan pembayaran biaya pencatatan
  tahunan, 7 record) — total 32 record. Kata kunci ini sengaja dipilih berbeda
  dari `"keterlambatan penyampaian"` milik `keterbukaan_informasi` — kata kedua
  berbeda (pembayaran vs. penyampaian), diverifikasi tidak ada tabrakan.
- `aksi_korporasi_delisting`: `"pembelian kembali saham"` (buyback untuk
  delisting, 2 record), `"penggabungan usaha"` (merger yang menghapus
  pencatatan, 1 record), `"voluntary delisting"` (go-private, 1 record) —
  total 4 record.

Setiap kata kunci diverifikasi dengan menghitung kemunculannya pada seluruh 592
teks alasan (bukan hanya pada 93 record `lainnya` semula) untuk memastikan tidak
ada kecocokan tak terduga di kategori lain, termasuk pada 467 record
`lonjakan_harga`.

## Cacat jendela harga dan perbaikannya

Jendela harga yang dipakai untuk menghitung `reopen_return` semula berakhir tepat
di tanggal suspensi (`[susp − 59d, susp]`), sehingga tidak ada satu pun baris
sesudah pembekuan untuk dibaca — setiap `reopen_return` tidak pernah teramati.
Diperbaiki di komit `ec586de` (`fix(etl): span suspension date in price windows to
enable reopen_return`): jendela sekarang membentang `[susp − 59d, susp + 30d]`,
yang memungkinkan reopen teramati untuk **48 dari 55 kejadian**.

Perbaikan ini juga yang membuka temuan bahwa jendela zero-volume ALKA 24 Agustus –
2 September tidak punya record suspensi resmi di dalamnya (lihat koreksi di
`notes.md`) — cross-check `confirmed` vs `inferred` hanya berarti sesuatu kalau
jendela harganya benar-benar mencakup periode sesudah pembekuan.

## Temuan utama — median reopen return per bucket

Base rate dipool dari 55 kejadian + 58 kontrol. Lima dari sembilan bucket mencapai
`MIN_SAMPLE=10`:

| Bucket | n | dari arm kejadian | median reopen |
|---|---|---|---|
| r1v1 (paling sepi) | 19 | 3 | **+17,3%** |
| r1v2 | 16 | 6 | +2,5% |
| r2v1 | 17 | 1 | +1,0% |
| r2v2 | 12 | 2 | +0,0% |
| r3v3 (paling ramai) | 27 | 27 | **−3,0%** |

Saham yang lari paling kencang dan paling ramai sebelum dibekukan cenderung
reopen **turun**; yang paling sepi cenderung reopen naik. Kolom "dari arm kejadian"
menggambarkan komposisi desain sampel case-control ~1:1, bukan probabilitas beku
di dunia nyata — di r3v3, "27 dari 27" berarti seluruh anggota bucket itu berasal
dari kelompok kejadian (tidak ada kontrol yang jatuh ke bucket ini), bukan "100%
saham seperti ini akan dibekukan".
