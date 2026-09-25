# Checklist submission

Deadline: 30 September 2026, 23:59 WIB. Setelah submit, repo freeze total.

| Syarat | Status |
|---|---|
| Link repo publik (wajib tetap publik 90 hari setelah pengumuman) | **Siap** — `github.com/marshal-rizky/FREEZE-BYTE`, publik |
| Video teaser 1 menit, publik di YouTube atau media sosial | **Belum** — naskah ada di `docs/video-script.md` |
| Video judging maks 3 menit, walkthrough lengkap | **Belum** — naskah ada di `docs/video-script.md` |
| Problem statement satu kalimat | **Siap** — lihat bagian di bawah |
| Pilihan track dan daftar nama peserta | **Siap** — Track 03, solo |
| Postingan media sosial (Instagram / LinkedIn / Threads / TikTok) tag akun Sectors, pakai template thumbnail | **Belum** |
| Ekstensi terpasang lewat Load unpacked dari zip Release | **Siap** (Release terbit) — [v0.1.0](https://github.com/marshal-rizky/FREEZE-BYTE/releases/tag/v0.1.0); dipasang dari folder `extension/` di Chrome, pemasangan dari zip belum dicoba |
| Halaman bukti publik di GitHub Pages | **Siap** — https://marshal-rizky.github.io/FREEZE-BYTE/site/ |
| Chrome Web Store | **belum disubmit** |

Sisa pekerjaan: memasang ekstensi dari zip Release sekali lewat Load
unpacked, mengisi sisa checklist situs asli di `docs/user-testing.md`, dua
video, dan satu postingan media sosial. Chrome Web Store opsional (butuh ikon
128px).

## Problem statement

Investor ritel IDX membeli saham yang sedang lari tanpa tahu bahwa kombinasi float
tipis, insider yang sedang menjual, dan harga di puncak adalah kondisi yang secara
historis berakhir dengan saham dibekukan — dan saat beku, mereka tidak bisa keluar.

## Track

Track 03 — Market Intelligence.

## Pemeriksaan akhir sebelum submit

- [x] `RET10_TERCILES` dan `VOL_TERCILES` di `freezebyte/baserates.py` sudah diisi
  tercile sebenarnya dari output `scripts/report_discovery.py`:
  `(-0.030303, 0.318182)` dan `(0.742330, 1.719077)`, dihitung dari 112 window
  yang riwayat perdagangannya cukup panjang. Bukan placeholder lagi.
  Penjaganya tetap ada: kalau nilainya kembali ke `(0.0, 0.0)`, `build.main()`
  menolak menulis `baserates.json` (kecuali
  `FREEZEBYTE_ALLOW_PLACEHOLDER_TERCILES=1` diset), karena dengan placeholder
  kesembilan bucket kolaps jadi satu (`r3v3`).
- [x] Bagian `## Coverage` sudah ada di README.md dengan angka sebenarnya dari
  `data/web/coverage.json`: 595 record total, 120 masuk sampel forensik
  (60 kejadian + 60 kontrol), 112 dianalisis dan 8 gugur.
- [x] `git grep -nE "SECTORS_API_KEY=[\"']?[A-Za-z0-9_-]{8,}"` tidak mengembalikan
  apa pun (dipersempit dari pola sebelumnya: pola lama juga kena tiga hit palsu --
  baris checklist ini sendiri, dikutip di sini dan di implementation plan, plus
  `.env.example` yang direproduksi kosong di plan -- tidak satu pun berisi key
  sungguhan, jadi kotaknya tidak pernah bisa dicentang jujur dengan pola lama).
  Hasil: nihil.
- [x] `.env` tidak ada di `git ls-files` -- 0 match.
- [x] `python -m pytest` lulus dari clone bersih tanpa `.env` -- di-clone ke
  direktori sementara, 93 passed.
- [x] Situs terbuka dan lengkap dari clone bersih tanpa API key -- disajikan dari
  clone bersih, halaman + 3 aset + ketujuh file JSON semuanya HTTP 200.
- [x] Disclaimer ada di halaman dan di README -- "Bukan saran investasi" ada di
  `site/index.html` maupun `README.md`.
- [x] Tidak ada klaim akurasi berbasis n=2 di mana pun -- tidak ada frasa akurasi
  INPS/MGLV di `site/` maupun README.md.
- [x] `node --test "extension/test/*.test.js"` lulus -- 38 passed (2026-09-25).
- [x] `python -m pytest` lulus dari clone bersih tanpa `.env` -- `main` di-clone
  ke direktori sementara, tanpa `.env`, 133 passed (2026-09-25).
- [ ] Zip Release terpasang tanpa error di `chrome://extensions`.
- [x] `extension/` tidak berisi string API key: `git grep -nE "SECTORS_API_KEY=[\"']?[A-Za-z0-9_-]{8,}"` kosong.
- [x] "Bukan saran investasi" ada di deskripsi manifest, kartu lencana, popup, situs, README
  -- dicek per berkas: `manifest.json`, `verdict.js` (caveat kartu), `popup.html`,
  `site/index.html`, `README.md`.
- [x] Frasa "risiko sedang" tidak ada di mana pun: `git grep -ni "risiko sedang" -- extension/src site` kosong.
- [x] `docs/validation/lead-time.md` sesuai `data/web/validation.json` build terakhir
  -- dibangun ulang dari cache (nol kredit), tidak ada perubahan.
- [ ] `docs/user-testing.md` terisi untuk seluruh baris uji teknis.
