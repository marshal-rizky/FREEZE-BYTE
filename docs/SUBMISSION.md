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

- [ ] Bagian `## Coverage` masih harus ditambahkan ke README.md dengan angka
  sebenarnya dari `data/web/coverage.json`, setelah pipeline build dijalankan
- [ ] `git grep -i "SECTORS_API_KEY=" -- ':!*.example'` tidak mengembalikan apa pun
- [ ] `.env` tidak ada di `git ls-files`
- [ ] `python -m pytest` lulus dari clone bersih tanpa `.env`
- [ ] Situs terbuka dan lengkap dari clone bersih tanpa API key
- [ ] Disclaimer ada di halaman dan di README
- [ ] Tidak ada klaim akurasi berbasis n=2 di mana pun
