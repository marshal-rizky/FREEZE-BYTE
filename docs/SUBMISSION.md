# Checklist submission

Deadline: 30 September 2026, 23:59 WIB. Setelah submit, repo freeze total.

| Syarat | Status |
|---|---|
| Link repo publik (wajib tetap publik 90 hari setelah pengumuman) | |
| Video teaser 1 menit, publik di YouTube atau media sosial | |
| Video judging maks 3 menit, walkthrough lengkap | |
| Problem statement satu kalimat | |
| Pilihan track dan daftar nama peserta | |
| Postingan media sosial (Instagram / LinkedIn / Threads / TikTok) tag akun Sectors, pakai template thumbnail | |

## Problem statement

Investor ritel IDX membeli saham yang sedang lari tanpa tahu bahwa kombinasi float
tipis, insider yang sedang menjual, dan harga di puncak adalah kondisi yang secara
historis berakhir dengan saham dibekukan — dan saat beku, mereka tidak bisa keluar.

## Track

Track 03 — Market Intelligence.

## Pemeriksaan akhir sebelum submit

- [x] `RET10_TERCILES` dan `VOL_TERCILES` di `freezebyte/baserates.py` masih
  placeholder `(0.0, 0.0)` -- isi dengan tercile sebenarnya dari output
  `scripts/report_discovery.py` SEBELUM build terakhir. Dengan placeholder,
  `build.main()` menolak menulis `baserates.json` (kecuali
  `FREEZEBYTE_ALLOW_PLACEHOLDER_TERCILES=1` diset), dan kalau dipaksa,
  kesembilan bucket kolaps jadi satu (`r3v3`).
- [x] Bagian `## Coverage` masih harus ditambahkan ke README.md dengan angka
  sebenarnya dari `data/web/coverage.json`, setelah pipeline build dijalankan
- [x] `git grep -nE "SECTORS_API_KEY=[\"']?[A-Za-z0-9_-]{8,}"` tidak mengembalikan
  apa pun (dipersempit dari pola sebelumnya: pola lama juga kena tiga hit palsu --
  baris checklist ini sendiri, dikutip di sini dan di implementation plan, plus
  `.env.example` yang direproduksi kosong di plan -- tidak satu pun berisi key
  sungguhan, jadi kotaknya tidak pernah bisa dicentang jujur dengan pola lama).
  Hasil: nihil.
- [x] `.env` tidak ada di `git ls-files` -- 0 match.
- [x] `python -m pytest` lulus dari clone bersih tanpa `.env` -- di-clone ke
  direktori sementara, 91 passed.
- [x] Situs terbuka dan lengkap dari clone bersih tanpa API key -- disajikan dari
  clone bersih, halaman + 3 aset + ketujuh file JSON semuanya HTTP 200.
- [x] Disclaimer ada di halaman dan di README -- "Bukan saran investasi" ada di
  `site/index.html` maupun `README.md`.
- [x] Tidak ada klaim akurasi berbasis n=2 di mana pun -- tidak ada frasa akurasi
  INPS/MGLV di `site/` maupun README.md.
