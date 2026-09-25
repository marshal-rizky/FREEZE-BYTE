# FREEZE BYTE — strip untuk saham di luar zona dan yang tidak dipantau

Ditulis 2026-09-25, disetujui di sesi brainstorming hari yang sama (mockup
empat keadaan di visual companion). Melanjutkan
`2026-09-25-pinned-strip-design.md`; yang tidak disebut di sini tetap
berlaku dari spec itu.

## 1. Masalah

Strip Lapis 0 hanya muncul untuk TINGGI dan SEDANG. Di halaman saham lain
tidak ada apa pun, sehingga pengguna tidak tahu apakah ekstensi aktif.

## 2. Keputusan

Strip juga muncul untuk dua keadaan baru, **hanya untuk saham yang sedang
dibuka lewat URL** (Lapis 0). Tanda di dalam teks (Lapis 1) tetap hanya
untuk TINGGI dan SEDANG.

| Keadaan | Kapan | Warna | Label | Tampil penuh |
|---|---|---|---|---|
| TINGGI | ada di semesta, tingkat `tinggi` | merah (tetap) | Di zona suspensi | 6000 ms, denyut 2× |
| SEDANG | ada di semesta, tingkat `sedang` | kuning (tetap) | Mendekati zona suspensi | 6000 ms, tanpa denyut |
| **LUAR** | ada di semesta, tingkat `senyap` | **biru** | **Di luar zona suspensi** | **3000 ms**, tanpa denyut |
| **TIDAK** | simbol dari URL tidak ada di semesta | **bening** | **Tidak dipantau** | **3000 ms**, tanpa denyut |

**Tidak ada kata "aman"** sebagai penilaian, dan warna hijau tidak dipakai.
Data hanya menyatakan saham tidak berada di zona tempat IDX biasanya
bertindak karena lonjakan harga. Suspensi karena alasan lain tetap bisa
terjadi. Label hijau "aman" akan terbaca sebagai rekomendasi beli, yang
dilarang disclaimer "bukan saran investasi".

## 3. Copy

Semua kalimat berasal dari `verdict.js`.

**LUAR**
- `label`: `Di luar zona suspensi`
- `move`: `Naik <pct(ret_10d)> dalam 10 hari bursa` kalau `ret_10d` ≥ 0,
  `Turun <pct(-ret_10d)> dalam 10 hari bursa` kalau negatif; dihilangkan
  kalau `ret_10d` null.
- `headline`: `Belum melonjak seperti saham yang biasanya disuspensi. Bukan berarti aman.`
- `evidence` (kartu detail): `Kenaikan 10 hari bursa masih di bawah batas zona (naik <pct(upper)>). Suspensi karena alasan lain tetap bisa terjadi.`
- `caveat`, `stale`, `asOf`, `evidenceUrl`, `flags`: sama seperti TINGGI/SEDANG.

**TIDAK**
- `label`: `Tidak dipantau`
- `move`: tidak ada.
- `headline`: `FREEZE BYTE aktif. Saham ini di luar <jumlah semesta> emiten yang dipantau. Tidak dikenali, bukan berarti aman.`
- Tidak ada kartu detail, tidak ada tautan bukti, tidak ada `asOf`.

## 4. Tampilan

Posisi, ukuran, tipografi, dan perilaku (tahan saat kursor di atas strip, ×,
klik pil, tidak dibuat ulang saat pindai ulang dengan simbol sama) sama
dengan strip yang sudah ada.

- **LUAR**: latar `rgba(12,27,54,.94)`, border `#5b9dff`, cincin
  `0 0 0 6px rgba(91,157,255,.16)`, bayangan `0 18px 40px rgba(0,0,0,.3)`,
  glyph `○` `#8ab8ff`, label `#cfe0ff`. Pil berwarna sama.
- **TIDAK**: latar `rgba(20,24,33,.52)` dengan
  `backdrop-filter: blur(14px) saturate(140%)`, border
  `rgba(255,255,255,.45)`, bayangan
  `inset 0 1px 0 rgba(255,255,255,.25), 0 14px 34px rgba(0,0,0,.25)`,
  glyph `◌` dan label putih 85–90%. Tanpa tombol "Detail ›". Pil berwarna
  sama. Kaca gelap dipilih supaya terbaca di situs terang maupun gelap.
- Pil: `○ AGII · Di luar zona suspensi`, `◌ BBCA · Tidak dipantau`.
- Animasi masuk sama (420 ms). LUAR dan TIDAK tidak berdenyut.
  `prefers-reduced-motion` tetap mematikan animasi.

## 5. Arsitektur

- `extension/src/verdict.js`: fungsi baru
  `pinnedVerdict(entry, symbol, thresholds, now, universeSize)`.
  - `entry` bertingkat `tinggi`/`sedang` → hasil `verdict()` apa adanya.
  - `entry` bertingkat `senyap` → objek LUAR (`tier: "luar"`).
  - `entry` null → objek TIDAK (`tier: "tidak"`, `symbol` dari argumen).
  - `verdict()` tidak berubah: Lapis 1 tetap memakainya dan tetap `null`
    untuk `senyap`.
- `extension/src/content.js`:
  - Menyimpan semua entri semesta dalam Map.
  - Untuk simbol dari URL, item pinned dibuat dengan `pinnedVerdict(...)`,
    apa pun tingkatnya.
  - Pengembalian dini `if (!verdicts.size) return;` diganti supaya strip
    tetap bisa tampil walau tidak ada saham TINGGI/SEDANG.
  - Daftar putih Lapis 1 tetap dari `verdict()`.
- `extension/src/overlay.js`:
  - Kelas `.pin.luar` dan `.pin.tidak`.
  - Lama tampil per tingkat: 6000 ms untuk `tinggi`/`sedang`, 3000 ms
    untuk `luar`/`tidak`.
  - Tombol "Detail ›" tidak dirender untuk `tidak`.
  - Denyut hanya untuk `tinggi`.

## 6. Pengujian

- `node --test`, untuk `pinnedVerdict`:
  - Tinggi dan sedang sama dengan `verdict()`.
  - Senyap memberi `tier` `luar` dengan label, `headline` (memuat "Bukan
    berarti aman"), dan `move` naik/turun yang benar.
  - Entri null memberi `tier` `tidak` dengan `headline` yang memuat jumlah
    semesta dan tanpa `evidenceUrl`.
  - Tidak ada "risiko sedang" di keluaran mana pun.
- `harness-pinned.html` ditambah `window.__luar()` (entri senyap dari
  fixture) dan `window.__tidak()` (simbol di luar fixture). Uji Playwright:
  - Keduanya tampil.
  - Keduanya menjadi pil setelah sekitar 3,5 detik.
  - TIDAK tanpa tombol Detail.
  - Hitungan `badges` tetap 1.
- Chrome sungguhan: TradingView AGII atau saham senyap lain (biru), dan
  BBCA (bening).
