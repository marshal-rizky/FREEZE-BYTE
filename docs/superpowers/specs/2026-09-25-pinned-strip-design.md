# FREEZE BYTE — strip peringatan untuk saham yang sedang dibuka

Ditulis 2026-09-25, disetujui di sesi brainstorming hari yang sama (mockup
di visual companion). Melengkapi `2026-09-22-freeze-byte-extension-design.md`
§6 Lapis 0/2 dan §7; bagian lain spec itu tetap berlaku.

## 1. Masalah

Lencana Lapis 0 (saham yang dideteksi dari URL) sekarang berupa pil kecil di
pojok kanan atas. Di TradingView ia menimpa tombol "Get started" situs, dan
di video demo ia terlalu kecil untuk terbaca sebagai peringatan.

## 2. Keputusan

Lencana Lapis 0 diganti **strip lebar di atas-tengah** yang tampil penuh
selama 6 detik lalu menciut menjadi pil di posisi yang sama.

Tidak berubah: tanda Lapis 1 (garis tepi + glyph ▲/△ di kode dalam teks),
kartu detail, deteksi, data, dan aturan copy (tanpa angka peluang, tanpa
"risiko sedang", "Bukan saran investasi" tetap di kartu).

## 3. Tampilan

Posisi: `position: fixed`, `top: 56px`, tengah horizontal
(`left: 50%; transform: translateX(-50%)`), lebar `min(680px, calc(100vw - 32px))`.
56px menaruhnya di bawah navbar kebanyakan situs keuangan.

**Strip penuh**, satu baris flex:
- glyph tingkat: ▲ (TINGGI, `#ff6b70`) atau △ (SEDANG, `#f2c46d`), 22px;
- baris utama: kode saham (800, 17px, putih) lalu label tingkat (700, 15px);
- baris kedua (12px, putih 72%): `move` + " · " + `headline` (lihat §5);
- kanan: tombol "Detail ›" (membuka kartu detail yang sudah ada) dan tombol ×.

Warna: TINGGI latar `rgba(58,13,16,.95)`, border `#f2555a`, cincin
`0 0 0 6px rgba(242,85,90,.18)`; SEDANG latar `rgba(51,37,10,.95)`, border
`#e0a43a`, cincin `rgba(224,164,58,.18)`. Radius 14px, padding 11px 14px,
bayangan `0 18px 40px rgba(0,0,0,.35)`.

Kalau data basi (`verdict.stale`), baris kedua ditambah " · data per <asOf>".

**Pil** (setelah menciut): `inline-flex`, posisi sama, teks
"▲ CCSI · Di zona suspensi" (△ untuk SEDANG), 700 12px, radius 999px, warna
tingkat yang sama. Pil adalah tombol.

## 4. Perilaku

| Pemicu | Hasil |
|---|---|
| Strip pertama kali tampil untuk suatu simbol | Masuk: dari `translateY(-12px)` + opacity 0 ke posisi akhir, 420ms, `cubic-bezier(0.16, 1, 0.3, 1)`. TINGGI: lalu cincin berdenyut dua kali (2 × 900ms). SEDANG: tanpa denyut. Timer 6000ms mulai. |
| Timer habis | Strip menciut jadi pil (transisi 240ms, ease-out). |
| Kursor masuk strip | Timer ditahan. Kursor keluar: timer dimulai ulang penuh (6000ms). |
| Klik × | Menciut seketika, timer dibatalkan. |
| Klik pil | Strip penuh lagi, tanpa denyut; timer mulai ulang. |
| Klik "Detail ›" | Kartu detail yang sudah ada terbuka; strip tidak berubah keadaan. |
| Scan ulang dengan simbol yang sama | **Tidak ada apa pun**: strip tidak dibuat ulang, keadaan penuh/pil dipertahankan. Scan ulang terjadi paling lambat tiap 1,5 detik di halaman hidup; membuat ulang strip akan memutar ulang animasi tanpa henti. |
| Scan ulang dengan simbol lain (navigasi SPA) | Strip lama dibuang, strip baru untuk simbol baru masuk seperti baris pertama. |
| URL tidak lagi menunjuk saham di semesta | Strip dibuang. |

`prefers-reduced-motion: reduce`: tanpa animasi masuk, tanpa denyut,
transisi menciut seketika. Timer dan perilaku lain tetap.

`host.dataset.badges` menghitung strip/pil sebagai satu item terlihat, sama
seperti lencana lama.

## 5. Copy

`verdict.js` mendapat satu field baru, `headline`, supaya seluruh kalimat
tetap berasal dari modul yang sudah dites:
- TINGGI: `Sehari sebelum suspensi, <counts.events> dari <n.events> kejadian terlihat seperti ini`
- SEDANG: `Batas zona: naik <pct(upper)>`

`move` yang sudah ada dipakai apa adanya ("Naik 47,6% dalam 10 hari bursa").
Tidak ada angka peluang atau akurasi.

## 6. Arsitektur

- `extension/src/verdict.js`: tambah `headline`.
- `extension/src/strip.js` (baru, UMD seperti `detect.js`, murni):
  `createCollapseTimer(onCollapse, delay, timers)` →
  `{ start(), hold(), release(), collapseNow(), cancel() }`. `timers` default
  `{ setTimeout, clearTimeout }` global, bisa diganti di tes.
- `extension/src/overlay.js`: item `pinned` dirender sebagai strip/pil,
  dikelola terpisah dari daftar item Lapis 1 dan dipertahankan antar
  `setItems` selama simbolnya sama. Tidak ada lagi posisi dari jangkar.
- `extension/src/anchors.js` dan `extension/test/anchors.test.js` dihapus.
  Jangkar Stockbit tidak pernah terisi dan strip selalu di atas-tengah, jadi
  modul itu tinggal kode mati. `content.js` berhenti memanggil
  `FB.anchorFor`; `manifest.json`, `popup.js` (`SCRIPTS`), dan
  `test/harness.html` berhenti memuatnya. Spec utama §6 Lapis 2 dan
  `docs/user-testing.md` (baris jangkar) disesuaikan.
- `extension/src/strip.js` dimuat sebelum `overlay.js` di ketiga tempat itu.

## 7. Pengujian

- `node --test`: `headline` untuk TINGGI/SEDANG (dan tetap tanpa "risiko
  sedang"); `createCollapseTimer` dengan timer palsu: runtuh tepat setelah
  `delay`; `hold()` menahan; `release()` memulai ulang penuh;
  `collapseNow()` memanggil sekali dan membatalkan timer; `cancel()` tidak
  memanggil.
- Harness: halaman baru `extension/test/harness-pinned.html` yang memuat
  `verdict.js`, `strip.js`, dan `overlay.js` (tanpa `content.js`, karena
  deteksi URL tidak bisa jalan di localhost), membaca fixture yang sama, lalu
  memanggil `FB.createOverlay(document)` dan `setItems([{ pinned: true,
  verdict }])` untuk AAAA. Halaman itu juga menyediakan
  `window.__rescan()` yang memanggil `setItems` lagi dengan item yang sama,
  dan `window.__switch()` yang memanggilnya dengan BBBB. Playwright: strip
  tampil; setelah ~6,5 detik menjadi pil; klik pil → strip penuh; scan ulang
  paksa dengan simbol sama tidak memutar ulang animasi (elemen strip yang
  sama tetap ada); hitungan `badges` benar; halaman tidak berubah.
- Chrome sungguhan: TradingView CCSI (TINGGI) dan MITI (SEDANG); strip tidak
  menutupi tombol navbar; menciut; pil terbuka lagi.
