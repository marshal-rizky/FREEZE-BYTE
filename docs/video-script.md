# Naskah video

## Judging video (maks 3 menit)

### 0:00–0:25 — Masalahnya, lewat ALKA
Tampilkan grafik ALKA. Harga naik +97,3% dalam enam hari bursa (3.750 pada
7 September ke 7.400 pada 15 September), lalu ALKA resmi disuspensi IDX pada
16 September — dan masih beku sampai baris data terakhir, 18 September, tutup
di 7.400 dengan volume nol. Pada titik itu pemegang saham tidak bisa keluar.
Ucapkan problem statement satu kalimat.

### 0:25–1:10 — Anatomi kejadian yang tercatat
Scroll ke bagian 2. Tunjukkan distribusi alasan resmi. Klik satu PDF pengumuman
IDX sampai benar-benar terbuka di layar — ini aset kredibilitas terbesar produk.
Tunjukkan sebaran kenaikan harga sebelum pembekuan dibanding kelompok kontrol.

### 1:10–1:55 — Mesin yang sama, dijalankan hari ini
Buka features.py di editor. Tunjukkan bahwa forensik dan daftar pantau memanggil
fungsi yang sama dengan as_of yang berbeda. Lalu scroll ke bagian 3 dan tunjukkan
daftar pantau beserta chip kondisi struktural dan base rate di sebelahnya.

### 1:55–2:25 — Kenapa angkanya bisa dipercaya
Tunjukkan bagian coverage: berapa yang dianalisis, berapa yang gugur, dan kenapa.
Tunjukkan bucket yang berbunyi "sampel tidak cukup". Tunjukkan perbedaan visual
antara jendela terkonfirmasi dan yang hanya tersimpulkan dari volume nol.

### 2:25–2:50 — Jalankan sendiri
Terminal: clone, pytest lulus, buka halaman. Tanpa API key, tanpa kredit.

### 2:50–3:00 — Disclaimer dan penutup
Tampilkan disclaimer di layar dan ucapkan bahwa produk ini deskriptif.

## Teaser 1 menit

Potong 0:00–0:25 dan 1:55–2:15 dari judging video, tambahkan kartu judul di awal
dan disclaimer di akhir.

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
