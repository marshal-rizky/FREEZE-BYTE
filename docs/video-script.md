# Naskah video

Catatan produksi: jangan pakai INPS sebagai contoh saat syuting. INPS sedang
disuspensi, jadi `as_of`-nya lebih tua dari seminggu pada hari build dan
kartunya akan menampilkan peringatan data basi.

## Judging video (maks 3 menit)

Aturan hackathon: walkthrough masalah, audiens, dan alur inti, maksimal 3
menit, boleh publik atau unlisted. Target 2:50 supaya ada ruang 10 detik.
Bobot nilai: video 30%, usability 40%, technical depth 30%.

### Sebelum merekam

- Rekam paling lambat 29 September. `as_of` data ekstensi 2026-09-23 dan
  strip menampilkan "data per ..." begitu lewat 7 hari.
- Reload ekstensi di `chrome://extensions` dari build terbaru (termasuk
  host `idx.co.id` tanpa `www`).
- Buka semua tab di bawah lebih dulu supaya tidak ada layar loading.
- Situs bukti dibuka dari GitHub Pages, bukan `file://`.
- Jangan pakai INPS (lihat catatan di atas).

Tab yang disiapkan:

| # | URL | Dipakai di |
|---|---|---|
| 1 | `https://stockbit.com/symbol/CCSI` | 0:00, 0:25 |
| 2 | `https://stockbit.com/symbol/MITI` | 0:50 |
| 3 | `https://www.tradingview.com/symbols/IDX-AGII/` | 0:55 |
| 4 | `https://www.google.com/finance/quote/BBCA:IDX` | 1:00 |
| 5 | Halaman berita/forum yang menyebut CCSI atau MITI di teks | 1:05 |
| 6 | `https://marshal-rizky.github.io/FREEZE-BYTE/site/` | 1:15 |
| 7 | PDF suspensi ALKA dari panel ALKA di situs | 1:50 |
| 8 | Terminal di folder kosong | 2:25 |

### 0:00–0:15 — Masalah

Layar: tab 1, strip merah CCSI terlihat di atas.

Voice-over:
> "Sepanjang 2025, ada 323 record suspensi saham di BEI karena harganya
> melonjak, menurut data Sectors. Saat saham dibekukan, pemegangnya tidak
> bisa menjual sampai perdagangan dibuka lagi."

### 0:15–0:25 — Untuk siapa

Layar: tetap di CCSI, zoom pelan ke strip.

> "FREEZE BYTE untuk investor ritel yang membeli saham yang sedang lari.
> Ekstensi ini memberi tahu, di halaman yang sedang mereka baca, kalau
> saham itu sedang berada di zona tempat bursa secara historis
> membekukan perdagangan."

### 0:25–1:15 — Alur inti di ekstensi

| Waktu | Layar | Voice-over |
|---|---|---|
| 0:25–0:50 | Tab 1 (CCSI). Strip merah "Di zona suspensi". Klik "Detail ›", kartu terbuka: naik 47,6% dalam 10 hari bursa, kalimat bukti, kondisi struktural, tautan "Lihat buktinya". | "CCSI naik 47,6% dalam sepuluh hari bursa. Sehari sebelum suspensi, 37 dari 55 kejadian terlihat seperti ini, dan tidak satu pun dari 57 emiten pembanding." |
| 0:50–0:55 | Tab 2 (MITI). Strip kuning. | "MITI kuning: mendekati zona, naik 28,2%." |
| 0:55–1:00 | Tab 3 (AGII, TradingView). Strip biru. | "AGII biru: di luar zona. Itu bukan berarti aman." |
| 1:00–1:05 | Tab 4 (BBCA, Google Finance). Strip bening "Tidak dipantau". | "BBCA tidak dipantau, tapi strip tetap muncul supaya jelas ekstensi aktif." |
| 1:05–1:15 | Tab 5. Kode saham di teks diberi bingkai dan ▲/△. Buka popup ekstensi di situs yang belum didukung, klik tombol aktifkan. | "Kode saham di teks berita juga ditandai. Situs lain bisa diaktifkan sendiri dari popup. Semua data dibawa ekstensi: tanpa akun, tanpa API key, tanpa jaringan." |

### 1:15–1:50 — Kenapa angkanya bisa dipercaya

Layar: dari kartu CCSI klik "Lihat buktinya". Halaman bukti terbuka di
panel Pantau dengan CCSI sudah tersaring. Klik manual ke panel Tenggang.

> "Angka di kartu berasal dari sini. Kami ambil 55 kejadian suspensi dan 57
> emiten pembanding, lalu mengukur profil masing-masing sehari sebelum
> suspensi. 37 kejadian berada di zona merah; pembandingnya nol.
> Untuk menguji ambangnya, kami pasang ulang hanya dari kejadian sebelum
> 28 Agustus, lalu uji ke kejadian sesudahnya: 17 dari 19 tertangkap,
> dengan 1 dari 17 pembanding ikut tertangkap. Ini hitungan sampel, bukan
> peluang sebuah saham dibekukan."

Tunjukkan juga baris T−3, T−5, T−10 di kurva: 27, 17, dan 14 dari 55
kejadian sudah merah, jadi zonanya sering terlihat beberapa hari lebih awal.

### 1:50–2:10 — Studi kasus ALKA

Layar: panel ALKA. Grafik, lalu klik satu PDF pengumuman IDX sampai
benar-benar terbuka.

> "ALKA naik dari 3.750 pada 7 September ke 7.400 pada 15 September, 97%
> dalam enam hari bursa. Keesokan harinya IDX membekukannya. Sampai data
> terakhir, 18 September, volumenya nol: pemegang saham terkunci di 7.400.
> Ini pengumuman resminya."

### 2:10–2:25 — Coverage dan satu mesin

Layar: panel Coverage. Tunjukkan 595 record, 120 sampel, 112 dianalisis,
8 dikecualikan beserta alasannya.

> "Dari 595 record suspensi, 112 dianalisis dan 8 dikecualikan karena
> riwayat perdagangannya terlalu pendek. Fungsi yang menghitung fitur
> kejadian lama ini sama persis dengan yang menghitung 73 saham di
> ekstensi hari ini; bedanya hanya tanggal `as_of`."

### 2:25–2:45 — Jalankan sendiri

Layar: terminal di folder kosong. Jalankan perintah di bawah (bagian
"Perintah terminal"). Potong waktu `pip install` di editor.

> "Semua bisa diperiksa sendiri. Clone repo, pasang tiga dependensi, lalu
> jalankan tes: 133 tes Python dan 38 tes ekstensi, lulus tanpa API key dan
> tanpa koneksi ke Sectors."

### 2:45–2:55 — Penutup

Layar: kartu penutup dengan link repo dan disclaimer penuh.

> "FREEZE BYTE bersifat deskriptif. Ini alat informasi, bukan saran
> investasi, dan tidak mengeksekusi order."

### Perintah terminal

Diuji di clone bersih dengan venv baru (Python 3.11, Node 24): 133 dan 38
tes lulus, tanpa `.env`.

```bash
git clone https://github.com/marshal-rizky/FREEZE-BYTE.git
cd FREEZE-BYTE
python -m venv .venv
source .venv/Scripts/activate      # PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m pytest                   # 133 passed
node --test "extension/test/*.test.js"   # pass 38, fail 0
ls .env                            # tidak ada: tanpa API key
python -m http.server 8000         # buka http://localhost:8000/site/
```

Di Command Prompt (cmd.exe) `source` dan `ls` tidak ada. Ganti dua baris itu:

```bat
.venv\Scriptsctivate
dir .env
```

### Sumber angka judging video

| Angka | Nilai | Sumber |
|---|---|---|
| T−1 | 37 dari 55 kejadian, 0 dari 57 kontrol di TINGGI | `data/web/validation.json`, `lags[lag=1]` |
| T−3 / T−5 / T−10 | 27 / 17 / 14 dari 55 kejadian di TINGGI | `data/web/validation.json`, `lags` |
| Holdout (ambang direfit) | batas 2026-08-28; 17/19 kejadian uji, 1/17 kontrol uji | `data/web/validation.json`, `holdout` |
| Holdout (ambang yang dipakai ekstensi) | 16/19 kejadian uji, 0/17 kontrol uji. Ambang ini dipasang dari seluruh data, termasuk split uji; sebut hanya kalau ditanya. | `holdout.shipped` |
| ALKA | 3.750 (7 Sep) ke 7.400 (15 Sep), +97,3% dalam 6 hari bursa; volume nol 16–18 Sep | `data/web/alka.json` |
| Coverage | 595 record; 120 sampel; 112 dianalisis; 8 dikecualikan (5 riwayat terlalu pendek, 3 riwayat kontrol terlalu pendek) | `data/web/coverage.json` |
| Semesta ekstensi | 73 saham: 7 TINGGI, 6 SEDANG, 60 senyap | `extension/data/universe.json` |
| CCSI / MITI / AGII | naik 47,6% / 28,2% / 18,9% | `extension/data/universe.json` |

## Teaser 1 menit

Aturan hackathon: teaser adalah rekaman layar produk yang sedang bekerja,
dipublikasikan publik di YouTube atau media sosial. Editing (potong, zoom,
teks, musik) boleh. Isinya harus ekstensi sungguhan, bukan mockup. Musik
harus bebas royalti (mis. YouTube Audio Library).

Rekam sebelum 30 September. Data ekstensi `as_of` 2026-09-23 dan dianggap
basi setelah 7 hari; sesudah itu strip menampilkan "data per ...".

Keadaan saham demo di `extension/data/universe.json` (as_of 2026-09-23):
CCSI TINGGI (naik 47,6%), MITI SEDANG (naik 28,2%), AGII di luar zona
(naik 18,9%), BBCA tidak dipantau.

### 0:00–0:08 — Hook angka
Layar hitam, angka besar muncul:
> **323**
> kali saham di BEI dibekukan karena harganya melonjak, sepanjang 2025.

Teks sumber kecil di bawah: "Record suspensi di data Sectors, 2025".

### 0:08–0:16 — Contoh ekstrem
Teks: **"NZIA naik 172% dalam 10 hari bursa. Lalu dikunci."** Potong ke
PDF pengumuman IDX NZIA yang terbuka di layar (zoom ke kalimat
"peningkatan harga kumulatif"). Teks penutup adegan: "Yang baru beli
tidak bisa keluar."

### 0:16–0:20 — Kartu judul
**FREEZE BYTE**: peringatan sebelum sahammu membeku. Ekstensi browser.

### 0:20–0:50 — Showcase empat keadaan
Rekaman layar TradingView (atau Stockbit), pindah halaman per saham:

| Waktu | Saham | Yang terlihat |
|---|---|---|
| 0:20–0:30 | CCSI | Strip merah berdenyut "Di zona suspensi". Klik "Detail ›", kartu terbuka sebentar. |
| 0:30–0:38 | MITI | Strip kuning "Mendekati zona suspensi". |
| 0:38–0:44 | AGII | Strip biru "Di luar zona suspensi · Bukan berarti aman". |
| 0:44–0:50 | BBCA | Strip bening "Tidak dipantau". Ekstensi tetap terlihat aktif. |

Boleh selipkan 2–3 detik halaman berita atau forum dengan kode saham yang
diberi bingkai ▲/△ di dalam teks.

### 0:50–1:00 — Penutup
Teks: "Gratis. Tanpa akun. Tanpa data yang dikirim ke mana pun."
Link: `github.com/marshal-rizky/FREEZE-BYTE`.
Disclaimer penuh di layar sampai akhir: **"Alat informasi, bukan saran
investasi."**

### Sumber angka teaser

Semua angka dihitung dari data yang sudah tersimpan di repo. Hitung ulang
dengan skrip di bawah; tanpa kredit API.

| Angka di video | Nilai | Sumber |
|---|---|---|
| Suspensi karena lonjakan harga, 2025 | 323 record, 182 saham berbeda | `data/raw/suspensions/all.json` (Sectors API, endpoint suspensi), alasan memuat "peningkatan harga" (bukan "penurunan harga") |
| NZIA sebelum suspensi | naik 171,9% dalam 10 hari bursa; disuspensi 2026-02-11 | `data/web/events.json`, `features.ret_10d` dari harga harian Sectors. [PDF IDX](https://www.idx.co.id/Portals/0/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/Exchange/2026/FEB/20260210-WAS_Suspensi_NZIA.pdf) |

Angka cadangan, kalau perlu mengganti atau menambah:

| Angka | Nilai | Sumber |
|---|---|---|
| 2026 sampai 22 September | 119 dari 140 suspensi (85%) karena lonjakan harga | `data/raw/suspensions/all.json` |
| Median kenaikan 10 hari bursa sebelum suspensi | +65% (55 kejadian); 13 dari 55 naik lebih dari dua kali lipat | `data/web/events.json` |
| AGAR | naik 162,3%, disuspensi 2026-08-19 | `data/web/events.json`, [PDF IDX](https://www.idx.co.id/Portals/0/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/Exchange/2026/AGU/20260818-WAS_Suspensi_AGAR.pdf) |
| FORU | naik 149,6%, disuspensi 2026-06-11 | `data/web/events.json`, [PDF IDX](https://www.idx.co.id/Portals/0/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/Exchange/2026/JUN/20260610-WAS_Suspensi_FORU.pdf) |
| UDNG | 6 kali disuspensi karena lonjakan harga | `data/raw/suspensions/all.json` |

Hitung ulang:

```bash
python - <<'EOF'
import json
a = json.load(open("data/raw/suspensions/all.json"))
surge = [r for r in a if "peningkatan harga" in r["reason"].lower()]
y25 = [r for r in surge if r["suspension_date"].startswith("2025")]
print(len(y25), len({r["symbol"] for r in y25}))  # 323 182
ev = {e["symbol"]: e for e in json.load(open("data/web/events.json"))}
print(ev["NZIA.JK"]["features"]["ret_10d"])        # 1.719...
EOF
```

### Aturan angka di teaser

- Sebut "record di data Sectors", bukan "total resmi BEI". Angka belum
  dicocokkan dengan statistik resmi BEI.
- Jangan membandingkan antartahun. Record sebelum 2025 sangat sedikit
  (2024: 17), kemungkinan karena cakupan data, bukan karena suspensi dulu
  jarang.
- Kalau hitungan tenggang (37/55, 0/57, 17/19, 1/17, dst.) ikut muncul,
  kalimat "bukan peluang atau akurasi" wajib tampil utuh.

## Hal yang DILARANG muncul di kedua video

- Angka akurasi apa pun yang berasal dari temuan n=2 (INPS dan MGLV)
- Kata "prediksi", "sinyal beli", "hindari saham ini", "rekomendasi"
- Klaim bahwa produk memprediksi suspensi emiten tertentu
- Menyajikan reopen −9,8% ALKA (jendela 24 Agustus – 2 September) sebagai
  reopen suspensi terkonfirmasi — jendela itu `inferred`, tidak ada
  pengumuman IDX di baliknya, dan hanya boleh muncul berlabel jendela
  zero-volume tak terkonfirmasi
- Menyajikan porsi arm kejadian sebuah bucket (mis. "27 dari 27 di r3v3
  berasal dari arm kejadian") sebagai probabilitas beku di dunia nyata —
  itu komposisi desain sampel case-control ~1:1, bukan frekuensi populasi
- Menyebut kurva tenggang atau holdout sebagai probabilitas atau akurasi
  prediksi
- Istilah tingkat SEDANG selain label lencana resmi "Mendekati zona suspensi"
