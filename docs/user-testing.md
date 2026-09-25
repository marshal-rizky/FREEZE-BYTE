# Pengujian pengguna

## Batasan

Tidak ada penguji yang aktif berinvestasi saham. Pengujinya perancang produk
sendiri, yang tahu arti setiap kata di lencana. Karena itu pengujian ini
**tidak bisa** menangkap salah baca kata-kata lencana. Yang diuji di bawah
adalah perilaku teknis dan kegunaan di situs asli.

## Uji teknis di situs asli

Dijalankan 2026-09-25 di Chrome, dengan ekstensi v0.1.0 dipasang lewat Load
unpacked dari aset Release `freeze-byte-extension-0.1.0.zip` dan data build
2026-09-24. Semua baris dilaporkan lulus oleh penguji.

Sejak strip empat keadaan, simbol di luar semesta tidak lagi "tanpa tanda":
halaman sahamnya mendapat strip bening "Tidak dipantau", dan kode di dalam teks
tetap tanpa tanda.

| Situs | Tanda/strip muncul untuk simbol TINGGI/SEDANG | Simbol di luar semesta: strip bening, tanpa tanda di teks | Ikut scroll dan resize | Halaman utuh dan tidak melambat | Kartu dan tautan bukti benar | Catatan |
|---|---|---|---|---|---|---|
| Stockbit (halaman simbol) | ya | ya | ya | ya | ya | CCSI: strip merah |
| TradingView | ya | ya | ya | ya | ya | CCSI merah, MITI kuning, AGII biru, BBCA bening |
| Google Finance | ya | ya | ya | ya | ya | CCSI: strip merah (URL dialihkan ke `/finance/beta/`) |
| IDX | ya | ya | ya | ya | ya | AGII: strip biru |
| Sectors | ya | ya | ya | ya | ya | BBCA: strip bening "Tidak dipantau" |
| RTI | ya | ya | ya | ya | ya | Tanpa strip (URL tanpa kode saham); tanda hanya di kode TINGGI/SEDANG dalam teks |
| Investing.com (Lapis 1) | ya | ya | ya | ya | ya | ▲ di "CCSI" dalam teks, tanpa strip |
| Satu artikel berita | ya | ya | ya | ya | ya | Awalnya tanpa tanda; aktif setelah "Aktifkan di situs ini" di popup |

Strip Lapis 0: tampil penuh, menciut jadi pil setelah 6 detik, pil membuka
lagi saat diklik, tidak menutupi tombol navbar situs: ya (Chrome, 2026-09-25,
TradingView CCSI dan MITI).

Strip untuk saham di luar zona (biru, "Di luar zona suspensi") dan yang tidak
dipantau (bening, "Tidak dipantau"): tampil di halaman saham, menciut setelah
3 detik, tidak ada kata "aman" sebagai penilaian: ya (Chrome, 2026-09-25,
TradingView AGII dan BBCA).

## Pertanyaan uji pemahaman

Siap dipakai kalau penguji tersedia. Tidak ada data pribadi yang disimpan.

1. "Apa arti lencana ini menurutmu?"
2. "Kalau kamu mau beli saham ini, apa yang kamu lakukan sekarang?"
3. "Berapa persen kemungkinan saham ini dibekukan?" — jawaban benar: tidak disebutkan.
4. Pada saham tanpa lencana: "Artinya saham ini aman?" — jawaban benar: tidak dikenali, bukan aman.

| Penguji | Q1 | Q2 | Q3 | Q4 | Perubahan kata yang dihasilkan |
|---|---|---|---|---|---|

Belum ada penguji.
