# Naskah video

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
Klik tautan itu ke bagian Tenggang di halaman bukti. Tunjukkan kurva
tenggang: pada T−1, 37 dari 55 kejadian dan 0 dari 57 kontrol berada di
TINGGI. Tunjukkan holdout temporal: 17 dari 19 kejadian uji tertangkap
TINGGI, dengan 1 dari 17 kontrol uji ikut tertangkap. Ucapkan bahwa ini
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

Potong 0:00–0:15 dan 0:55–1:30 dari judging video, tambahkan kartu judul di
awal dan disclaimer di akhir.

Potongan mana pun yang menampilkan hitungan (37/55, 0/57, 17/19, 1/17, dst.)
wajib menyertakan kalimat "bukan peluang atau akurasi" secara utuh sampai
selesai — tidak boleh dipotong sebelum kalimat caveat itu tuntas.

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
