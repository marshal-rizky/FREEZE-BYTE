# Naskah video

Catatan produksi: jangan pakai INPS sebagai contoh saat syuting. INPS sedang
disuspensi, jadi `as_of`-nya lebih tua dari seminggu pada hari build dan
kartunya akan menampilkan peringatan data basi.

## Judging video (maks 3 menit)

### 0:00–0:20 — Ekstensi di halaman Stockbit
Buka halaman Stockbit. Ucapkan problem statement satu kalimat sebagai
voice-over. Tunjukkan ticker yang disebut di teks halaman mendapat bingkai
tipis dengan tanda kecil ▲/△ di pojoknya. Lalu tunjukkan simbol yang sedang
dilihat pengguna mendapat lencana penuh: "Di zona suspensi" atau "Mendekati
zona suspensi". Klik lencana sampai kartu detail terbuka.

### 0:20–0:55 — Isi kartu detail
Tunjukkan isi kartu: kenaikan harga dalam 10 hari bursa, kalimat bukti
("sehari sebelum suspensi, profil ini muncul pada ... dari ... kejadian
suspensi"), kondisi struktural yang aktif (float tipis, insider menjual,
puncak 52 minggu), dan tautan "Lihat buktinya" yang membuka halaman bukti.

### 0:55–1:30 — Kenapa angkanya bisa dipercaya (Tenggang)
Klik "Lihat buktinya" -- tautan itu membuka halaman bukti di panel Pantau
dengan simbolnya sudah tersaring (`#pantau?symbol=...`), bukan langsung ke
Tenggang. Klik manual ke panel Tenggang. Tunjukkan kurva
tenggang: pada T−1, 37 dari 55 kejadian dan 0 dari 57 kontrol berada di
TINGGI. Tunjukkan holdout temporal: dengan ambang yang direfit dari kejadian
lama saja, 17 dari 19 kejadian uji tertangkap TINGGI dan 1 dari 17 kontrol
uji ikut tertangkap; dengan ambang yang sungguh dipakai ekstensi (dipasang
dari seluruh data, termasuk split uji ini), 16 dari 19 kejadian uji
tertangkap dan 0 dari 17 kontrol uji ikut tertangkap. Ucapkan bahwa ini
hitungan sampel kejadian dan pembanding, bukan peluang atau akurasi sebuah
saham dibekukan.

### 1:30–2:15 — Studi kasus ALKA
Tampilkan grafik ALKA. Harga naik +97,3% dalam enam hari bursa (3.750 pada
7 September ke 7.400 pada 15 September), lalu ALKA resmi disuspensi IDX pada
16 September — dan masih beku sampai baris data terakhir, 18 September, tutup
di 7.400 dengan volume nol. Pada titik itu pemegang saham tidak bisa keluar.
Klik satu PDF pengumuman IDX sampai benar-benar terbuka di layar — ini aset
kredibilitas terbesar produk. Tunjukkan sebaran kenaikan harga sebelum
pembekuan dibanding kelompok kontrol.

### 2:15–2:45 — Coverage dan mesin yang sama
Tunjukkan bagian coverage: berapa yang dianalisis, berapa yang gugur, dan
kenapa. Tunjukkan bucket yang berbunyi "sampel tidak cukup". Sebutkan bahwa
forensik dan daftar pantau ekstensi memanggil fungsi yang sama dengan as_of
yang berbeda — mesin yang menghasilkan kurva tenggang di atas adalah mesin
yang sama yang memasang lencana barusan.

### 2:45–2:55 — Jalankan sendiri
Terminal: clone, pytest lulus, buka halaman. Tanpa API key, tanpa kredit.

### 2:55–3:00 — Disclaimer dan penutup
Tampilkan disclaimer di layar dan ucapkan bahwa produk ini deskriptif.

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
