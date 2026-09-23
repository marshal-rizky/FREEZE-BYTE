# FREEZE BYTE — ekstensi peringatan pembekuan

**Sectors Hackathon 2026 · Track 03 Market Intelligence**
Ditulis 2026-09-22, disetujui di sesi brainstorming 2026-09-23. Menggantikan
permukaan utama spec `2026-09-20-freeze-byte-design.md`; mesin analisis Python
di spec itu tetap berlaku.

## 1. Apa yang berubah

Produk utama pindah dari situs ke ekstensi browser. Ekstensi memberi lencana
pada saham yang sedang dilihat pembeli, di situs mana pun, ketika saham itu
berada di zona tempat IDX secara historis membekukan perdagangan.

Situs tidak dibuang. Ia dipangkas menjadi **halaman bukti**: studi kasus ALKA,
distribusi alasan, kurva tenggang, dan halaman coverage. Popup ekstensi tidak
muat memuat metodologi; halaman bukti yang membuktikan proyeknya nyata.

## 2. Klaim produk

Ekstensi **tidak meramal**. Ia memberitahu bahwa saham yang sedang dilihat
berada di zona tempat IDX secara historis bertindak.

Dasarnya, dari `data/web/baserates.json` (55 kejadian, 58 kontrol, fitur diukur
T−1 sebelum suspensi):

| Tercile `ret_10d` | Kejadian | Kontrol |
|---|---|---|
| r1 (< −1,15%) | 10 | 28 |
| r2 (−1,15% … +31,59%) | 7 | 30 |
| r3 (> +31,59%) | 38 | 0 |

Sumbu return memisah seluruhnya; sumbu volume hampir tidak memisah apa-apa.
r3 memisah sempurna, sehingga odds ratio-nya tak terdefinisi dan tidak dikutip.

Penyebabnya diketahui: 467 dari 592 record suspensi beralasan
`lonjakan_harga`. IDX membekukan saham karena saham itu melonjak. Temuan ini
pada dasarnya aturan IDX yang dinyatakan ulang secara statistik. Nilai
produknya adalah menyalakan aturan itu tepat di detik keputusan, bagi pembeli
yang tidak tahu aturan itu ada.

Ekstensi tidak pernah menampilkan probabilitas atau persentase peluang beku.
Desain case-control tidak menghasilkan base rate populasi.

## 3. Tiga tingkat

Ambang atas diambil dari `RET10_TERCILES` di `freezebyte/baserates.py` dan
tidak diketik ulang di mana pun.

| Tingkat | Syarat | Bunyi lencana |
|---|---|---|
| **TINGGI** | `ret_10d` > 0,315874 (batas atas tercile) | "Di zona suspensi" |
| **SEDANG** | 0,20 ≤ `ret_10d` ≤ 0,315874 | "Mendekati zona suspensi" |
| **SENYAP** | selain itu, atau `ret_10d` tidak tersedia | tidak ada lencana |

SEDANG adalah **jarak ke ambang, bukan tingkat risiko tersendiri**. Data tidak
mendukung tingkat risiko tengah: r1 dan r2 praktis identik (10/38 lawan 7/37).
Batas bawah 0,20 adalah pilihan tetap proyek ini, bukan hasil estimasi, dan
halaman bukti menyatakannya begitu. Lencana SEDANG tidak pernah memakai kata
"risiko sedang".

Popup untuk TINGGI dan SEDANG menampilkan hitungan mentah (38 kejadian, 0
kontrol), `ret_10d` saham itu, tanggal `as_of`, caveat case-control, dan
tautan ke halaman bukti. Flag struktural (float < 25%, insider menjual, di
puncak 52 minggu) tampil sebagai konteks berlabel "kondisi sekarang" dan tidak
ikut menentukan tingkat — tag emiten tidak tersedia secara historis, jadi
tidak bisa divalidasi.

## 4. Pembuktian

Dua uji, keduanya memakai deret harga sampel forensik yang sama (120 simbol).

Definisi yang dipakai keduanya, mengikuti `scripts/report_discovery.py`:
tercile dihitung dari gabungan kejadian dan kontrol. `as_of` kejadian adalah
hari bursa terakhir sebelum tanggal suspensi; `as_of` kontrol adalah baris
berdagang terakhir di window-nya. T−1 adalah `as_of` itu sendiri; T−k adalah
baris berdagang ke-(k−1) sebelum `as_of`, untuk kejadian maupun kontrol.

**Kurva tenggang.** Fitur dihitung ulang di T−1, T−3, T−5, dan T−10 hari
bursa sebelum suspensi, untuk kejadian dan kontrol. Ambang tetap memakai
tercile T−1 — tidak dipasang ulang per jarak — karena ekstensi memakai ambang
tetap. Untuk tiap jarak dilaporkan berapa kejadian dan berapa kontrol masuk
TINGGI, dan berapa masuk SEDANG.

**Holdout temporal.** Kejadian diurutkan menurut tanggal suspensi. Dua pertiga
tertua dipakai menghitung tercile; sepertiga terbaru diuji dengan tercile itu.
Kontrol mengikuti kejadian pasangannya. Dilaporkan berapa kejadian uji
tertangkap TINGGI dan berapa kontrol uji salah tertangkap.

Hasil ditulis ke `docs/validation/lead-time.md` dan tampil di halaman bukti,
apa pun hasilnya. Yang dilaporkan hitungan, bukan persentase akurasi. Kalau
pemisahan runtuh di T−5, halaman bukti menyatakan tenggangnya satu hari bursa.

## 5. Arsitektur

```
freezebyte/
  scoring.py            fungsi murni: fitur -> tingkat
  validation.py         kurva tenggang + holdout, fungsi murni
  export_extension.py   menulis extension/data/*.json
scripts/
  etl_universe.py       screener + harga semesta ekstensi
  report_validation.py  menulis docs/validation/lead-time.md
extension/
  manifest.json         Manifest V3
  data/universe.json    simbol -> tingkat, ret_10d, vol_ratio, as_of, flag
  data/thresholds.json  ambang, hitungan kejadian/kontrol, hasil validasi
  src/detect.js         Lapis 0 aturan URL + Lapis 1 sapuan teks
  src/overlay.js        lapisan overlay, satu-satunya modul yang menyentuh halaman
  src/verdict.js        tingkat -> bunyi lencana
  src/popup.html, popup.js
site/                   halaman bukti, menerima ?symbol=
```

**Satu sumber ambang.** `verdict.js` tidak menyimpan angka ambang. Ia membaca
`thresholds.json`, yang digenerate dari `baserates.py` oleh
`export_extension.py`. `universe.json` sudah membawa tingkat hasil
`scoring.py`; ekstensi tidak menghitung ulang tingkat.

**Batas modul.**
- `detect.js` menjawab "simbol apa, di rentang teks mana". Tidak tahu soal risiko.
- `verdict.js` menjawab "tingkat apa, bunyinya apa". Tidak tahu soal DOM.
- `overlay.js` menggambar. Tidak tahu soal risiko maupun aturan situs.

`detect.js` dan `verdict.js` murni dan diuji tanpa browser.

**Tanpa jaringan saat jalan.** Ekstensi tidak memanggil API apa pun dan tidak
pernah meminta API key. Data dibekukan saat build.

## 6. Deteksi

**Lapis 0 — aturan URL.** Simbol yang sedang dilihat diambil dari
`location.pathname` per situs yang dikenal: Stockbit, IDX, Sectors,
TradingView, Google Finance, RTI, Investing.com. Pola URL tiap situs
diverifikasi terhadap situs aslinya saat implementasi, lalu dibekukan sebagai
fixture tes. Simbol dari URL selalu dilencanai walau tidak disebut di teks.

**Lapis 1 — sapuan teks.** `TreeWalker` atas text node, pola
`\b[A-Z]{4}\b`, dicocokkan dengan daftar putih `universe.json`. Kecocokan di
dalam rentetan kapital (lebih dari tiga kata kapital berurutan, mis. judul
"BEI SUSPENSI SAHAM INI") ditolak. Node di dalam `input`, `textarea`,
`script`, `style`, dan elemen `contenteditable` dilewati. `MutationObserver`
menangkap konten yang muncul belakangan, dengan debounce.

**Lapis 2 — jangkar Stockbit.** Satu selector yang hanya menentukan di mana
lencana simbol Lapis 0 dipaku, supaya menempel di sebelah harga. Selector
tidak pernah dipakai untuk deteksi. Kalau selector meleset, lencana jatuh ke
pojok kanan atas viewport.

## 7. Overlay

Halaman tidak pernah dimodifikasi. `overlay.js` membuat satu host
`position: fixed; pointer-events: none` di `document.documentElement` dengan
Shadow DOM tertutup, sehingga CSS halaman tidak bocor ke dalam dan sebaliknya.
Posisi lencana Lapis 1 diukur dengan `Range.getBoundingClientRect()` dan
diukur ulang saat scroll, resize, dan mutasi, paling banyak sekali per frame.
Rentang di luar viewport tidak digambar.

Lencana menerima pointer (klik membuka kartu detail); host tidak.

## 8. Izin

`host_permissions` hanya mendaftar situs Lapis 0. Situs lain lewat
`optional_host_permissions`, diaktifkan pengguna dari popup. `<all_urls>`
tidak dipakai sebagai izin wajib. Izin `storage` hanya untuk menyimpan daftar
situs opsional yang diaktifkan.

## 9. Semesta dan anggaran kredit

Semesta ekstensi sekitar 150 simbol: sampel forensik yang masih
diperdagangkan, ditambah hasil screener Sectors (`client.screen`) untuk emiten
berisiko — `public-float-under-25`, papan Pengembangan, papan pemantauan
khusus. Klausa `where` persisnya ditentukan saat implementasi dari kosakata
tag di `docs/discovery/2026-09-21-suspensions.md`, dengan jumlah kandidat
dicek lewat satu panggilan screener sebelum harga ditarik.

Simbol di luar semesta tidak dilencanai. Popup dan halaman bukti menyatakan
terang bahwa "tidak dikenali" berbeda dari "aman".

| Pos | Kredit |
|---|---|
| Harga 120 simbol sampel forensik (kurva tenggang, holdout) | 120 |
| Screener semesta | ≤ 5 |
| Harga ~80 simbol semesta di luar irisan | 80 |
| Overview simbol TINGGI/SEDANG untuk flag struktural | ≤ 50 |
| **Total** | **≤ 255** |

Sisa saat ini 619. Cadangan 150 tidak disentuh. Aturan lama tetap: setiap
respons API di-cache ke disk sebelum diproses, parameter `?q=` tidak dipakai.

## 10. Halaman bukti

Situs `redesign/bento-glass` menjadi dasar. Perubahan:
- Panel "Pantau hari ini" menerima `#pantau?symbol=CCSI` dan menampilkan vonis
  yang sama dengan ekstensi untuk satu simbol. Tanpa `symbol`, panel
  menampilkan daftar semesta dengan pencarian yang sudah ada.
- Panel baru "Tenggang": kurva tenggang dan hasil holdout.
- Ikhtisar menyebut ekstensi sebagai produk utama.

Tautan ini satu-satunya jangkauan ke pengguna mobile. Ekstensi browser tidak
bisa menjangkau aplikasi broker mobile, dan spec ini tidak mengklaim
sebaliknya.

## 11. Penanganan kegagalan

| Kondisi | Perilaku |
|---|---|
| Simbol tidak ada di semesta | Senyap |
| `ret_10d` null (riwayat pendek) | Senyap; halaman bukti menulis "data tidak cukup" |
| Selector jangkar Stockbit meleset | Lencana jatuh ke pojok |
| Rentang teks di luar viewport | Tidak digambar |
| `universe.json` gagal dimuat | Ekstensi senyap total, error di console |
| `as_of` lebih tua dari 7 hari kalender | Lencana tetap tampil, kartu menandai data basi |

## 12. Pengujian

- `scoring.py`, `validation.py`: pytest, termasuk batas tepat 0,20 dan
  0,315874, `ret_10d` null, dan holdout pada data sintetis dengan jawaban
  yang diketahui.
- `export_extension.py`: tes bahwa `thresholds.json` sama dengan
  `baserates.py`.
- `detect.js`, `verdict.js`: `node --test` tanpa dependensi, termasuk judul
  ALL CAPS, kata umum empat huruf, dan setiap pola URL Lapis 0.
- Ekstensi utuh: halaman fixture statis yang meniru struktur Stockbit dan
  artikel berita, dimuat lewat Playwright dengan ekstensi terpasang; cek
  lencana muncul, posisinya mengikuti scroll, dan DOM halaman tidak berubah.
- `python -m pytest` tetap lulus dari clone bersih tanpa `.env`.

## 13. Batasan yang tetap berlaku

- Bukan saran investasi. Disclaimer ada di popup, halaman bukti, README, dan
  deskripsi ekstensi.
- Tidak mengeksekusi order, tidak menghubungi broker.
- Tidak ada API key di repo; cek `git grep` di `docs/SUBMISSION.md` tetap
  dijalankan sebelum submit.
- Repo `Stocklens` tidak dipakai sebagai sumber kode.
- Setelah submit, repo freeze total.

## 14. Di luar cakupan

- Aplikasi broker mobile.
- Pembaruan data otomatis di ekstensi; data diperbarui dengan build ulang.
- Publikasi ke Chrome Web Store. Juri memasang lewat "Load unpacked".
- Firefox. Manifest V3 Chromium saja (Chrome, Edge, Brave, Opera).
