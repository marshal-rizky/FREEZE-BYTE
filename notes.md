# Catatan sesi — handoff

Diperbarui 2026-09-21. Dokumen ini untuk melanjutkan kerja di sesi atau perangkat lain tanpa kehilangan konteks. Kalau isinya bertabrakan dengan spec, spec yang menang.

## Status sekarang

Proyek: **FREEZE BYTE**, entri Sectors Hackathon 2026, Track 03 Market Intelligence. Solo. Python.

Repo: `github.com/marshal-rizky/FREEZE-BYTE`, dibuat 2026-09-20, publik. Dikloning lokal ke `C:\Users\User\FREEZE-BYTE`.

Sudah ada: spec desain lengkap di `docs/superpowers/specs/2026-09-20-freeze-byte-design.md`, implementation plan 13 task di `docs/superpowers/plans/2026-09-20-freeze-byte-implementation.md`, dan kode untuk seluruh bagian offline Task 1 sampai Task 7. Repo sudah tersinkron dengan `origin/main`.

Modul yang sudah jadi dan lulus test:

- `freezebyte/config.py`, `client.py` — cache disk, retry 429 terbatas, cache key dari digest seluruh parameter
- `freezebyte/freeze.py` — deteksi jendela beku, `confirmed` vs `inferred`
- `freezebyte/features.py` — mesin fitur, penjaga volume nol dan `high` null
- `freezebyte/reasons.py` — klasifikasi teks alasan suspensi
- `freezebyte/sampling.py` — pemilihan kejadian dan kontrol berpasangan
- `freezebyte/structural.py` — fitur struktural dari overview
- `scripts/etl_suspensions.py`, `etl_prices.py`, `etl_overviews.py` — siap jalan, belum dijalankan
- `tests/` — 58 test, `python -m pytest` lulus offline tanpa API key

Belum ada: `baserates.py`, `coverage.py`, `build.py`, seluruh `site/`, README final, `docs/SUBMISSION.md`, video, postingan media sosial.

**Belum ada satu kredit pun yang dipakai untuk ETL.** Direktori `data/` belum terbentuk.

## Langkah berikutnya

Task 5 Step 6 di plan: jalankan `scripts/etl_suspensions.py`, sekitar 20 kredit. Hasilnya dipakai menyetel aturan klasifikasi sampai kategori `lainnya` turun di bawah 10% (Task 5 Step 7, yang sekaligus keputusan Jev di bawah), lalu membuka Task 6.

Gerbang keputusan risiko ada di Task 6 Step 8, dijalankan segera setelah ETL harga selesai — bukan ditunda ke minggu kedua.

Deadline: **submit 30 September 2026 23:59 WIB.** Registrasi dan onboarding sudah selesai, jadi tidak ada urusan administrasi lagi. Batas registrasi resmi 22 September, tapi itu sudah tidak relevan.

## Ide produknya

Menganalisis **suspensi perdagangan IDX** — saham yang dibekukan bursa. Dua pilar setara di atas satu mesin fitur yang sama:

1. **Forensik** — anatomi pembekuan yang tercatat: apa yang terjadi pada harga dan volume sebelum dibekukan, dan apa yang terjadi saat dibuka kembali.
2. **Pantau hari ini** — mesin yang sama dijalankan pada emiten hari ini.

Yang membuat ini satu proyek, bukan dua: `features.py` menerima `(price_series, as_of_date)`. Forensik memanggil dengan `as_of` sehari sebelum suspensi, pantau memanggil dengan hari bursa terakhir.

Detail lengkap ada di spec. Jangan mengulang riset yang sudah ada di sana.

## Temuan kunci yang memicu ide ini

Rangkaian tiga tag Sectors lewat screener:

```
tags in ['insider-1-month-sell'] and tags in ['public-float-under-25'] and tags in ['52-w-high']
```

Mengembalikan **2 emiten dari 962** — INPS dan MGLV. Keduanya disuspensi dalam 11 hari sebelum query.

**n=2 bukan bukti.** Tidak boleh ditampilkan sebagai angka akurasi di video atau README. Ini pengamatan yang memicu investigasi.

Studi kasus utama: **ALKA.** Naik +97,3% dalam 6 hari bursa (3.750 pada 7 Sep ke 7.400 pada 15 Sep), lalu volume nol dari 16 Sep. Sebelumnya sudah pernah beku 24 Agustus – 2 September, buka di −9,8%. Fixture-nya sudah ditarik dan di-commit di `tests/fixtures/alka_daily.json`. Ini juga pembuka video.

## Yang sudah dites dan GAGAL — jangan ulangi

- `right_issue` di `fetch-corporate-actions` → null di BUMI dan TLKM. Angle dilusi mati.
- Status papan pemantauan khusus → bukan field. `listing_board` INPS berbunyi "Development" padahal INPS disuspensi justru karena berada di papan pemantauan khusus lebih dari 1 tahun. Hanya bisa disimpulkan dari teks `reason`.
- `fetch-listing-performance` → 404 untuk emiten listing sebelum Mei 2005.
- `agm_result` → terisi hanya di RUPS terakhir, tidak ada deret waktu.
- `fetch-company-segments` → dekomposisi laporan laba rugi, bukan segmen bisnis per divisi.

## Ide yang ditinggalkan dan alasannya

**Ide awal: diagnosa konsentrasi portofolio** (tempel holdings, kolaps ke entitas pengendali, ukur HHI dan free float). Tidak dibuang karena buruk — bagian uniknya masih belum ditempati siapa pun. Tapi tiga hal melemahkannya: nama "X-ray" bentrok dengan Morningstar Portfolio X-Ray, ownership graph IDX sudah dikerjakan tiga pihak komersial, dan HHI portofolio sudah ada versi gratisnya. Sisa idenya hidup sebagai fitur struktural di dalam mesin FREEZE BYTE.

**Angle mining** — sudah diambil tiga pesaing.

## Lanskap pesaing

11 repo hackathon publik per 2026-09-20; ini batas bawah karena sebagian besar tim menyimpan repo privat. Daftar lengkap ada di §14 spec.

Yang penting: **suspensi dan papan pemantauan khusus nol entri.** Penumpukan ada di mining (3) dan aliran dana (2).

## Keputusan yang masih menggantung

1. **Pakai Jev untuk `reasons.py`?** Ditunda ke Task 5 Step 7, diputuskan dari angka nyata.

   Jev adalah model dari TypeSafe AI, bukan LLM — mereka menyebutnya System One Model. Tidak autoregresif, output keluar sekali jalan secara paralel. Tidak bisa menghasilkan string sama sekali; yang keluar hanya nilai terstruktur sesuai skema yang ditetapkan di muka (pilihan, skor, atau probabilitas) berikut angka kalibrasi kepercayaan. Karena output dibatasi secara matematis ke skema, klaimnya tidak bisa halusinasi dan tidak pernah salah tipe. Batas keras: maksimal 255 opsi per pilihan, dan dirancang untuk state program terstruktur. Harga input 0,042 dolar per juta token, output gratis. Klaim internal 193x lebih cepat dan 444x lebih murah dari LLM frontier; uji independen Every mengukur sekitar 25x lebih cepat dan 580x lebih murah dari Claude Fable 5.1 untuk tugas ekstraksi.

   Satu-satunya titik yang cocok di proyek ini adalah `classify()` di `freezebyte/reasons.py` — memetakan teks alasan resmi IDX ke enam kategori atas ~592 record. `features.py` dan `baserates.py` aritmetika murni, tidak ada yang perlu diklasifikasi.

   Alasan ditunda, bukan ditolak: klasifikasi kata kunci mungkin sudah cukup, dan kalau cukup, Jev tidak menambah apa pun yang bisa dilihat juri sementara klasifikasinya jadi lebih sulit diaudit. Aturan kata kunci terbaca langsung di diff. Spec juga menyatakan "Tanpa LLM" dengan alasan komponen tambahan hanya menambah titik gagal.

   Keberatannya soal bukti dan waktu, bukan arsitektur: seluruh pipeline menulis ke disk dan `data/web/*.json` di-commit, jadi panggilan Jev akan jadi dependency saat build saja — sifat "juri clone tanpa API key" tetap utuh.

   Aturan keputusan: ambang di Task 5 Step 7 adalah kategori `lainnya` di bawah 10% memakai aturan kata kunci saja. Di bawah 10%, pertahankan kata kunci dan lupakan Jev. Di atas 10% dan penambahan kata kunci sudah mentok, Jev jadi fallback.

   Sumber: <https://typesafe.ai/blog/introducing-system-one-models-and-jev>, <https://www.langchain.com/blog/building-a-harness-with-jev>, <https://www.seangoedecke.com/jev-means-structured-output-is-interesting-again/>

## Koreksi terhadap spec yang ditemukan saat menulis plan

1. **API v1 sudah mati.** `GET /v1/daily/{ticker}/` mengembalikan HTTP 410 Gone sejak 2026-05-11. Base URL yang benar `https://api.sectors.app/v2`. Header `Authorization: <raw key>`, tanpa prefiks `Bearer`. Spec tidak menyebut versi sama sekali.
2. **Spec §7 salah menamai test.** `test_features_alka` menyebut "`ret_10d` pada as_of 2026-09-15 = +97,3%". Angka +97,3% itu perjalanan 3.750 (7 Sep) ke 7.400 (15 Sep) = **6 baris bursa**, bukan 10. Plan mengujinya sebagai `ret_n(..., n=6)`.
3. **Deliverable submission kurang di spec.** Aturan §08 minta lima hal: repo publik, teaser video 1 menit, judging video maks 3 menit, problem statement satu kalimat, **dan postingan media sosial** tag akun Sectors pakai template thumbnail. Spec cuma membahas satu video. Checklist lengkap ada di `docs/SUBMISSION.md` (dibuat pada Task 12).
4. **`open`, `high`, `low` di endpoint daily bersifat nullable**, bukan hanya bisa bernilai nol. Filter di `features.py` harus menangani keduanya.

## Kredit API

Terpakai sejauh ini: sekitar **15 dari 1.000** — riset eksplorasi ditambah satu panggilan untuk fixture ALKA. ETL sungguhan belum jalan. Anggaran rencana 455, sisanya cadangan. Rinciannya di §9 spec.

Aturan keras yang mudah dilanggar:

- Cache setiap respons ke disk sebelum diolah.
- Jangan pakai parameter `?q=` natural language — 3 kredit versus 1 untuk query terstruktur.
- `/v2/company/report/` memakan 1 kredit **per section**. Selalu sebut `?sections=overview`; tanpa itu jadi 8 kredit sekali panggil.
- `/v2/tags/` adalah kosakata tag berita, **bukan** tag screener seperti `52-w-high`. Kosakata tag emiten tetap harus dipetakan lewat sampling overview (Task 7).

## Kepatuhan yang mudah terlupa

- Repo `Stocklens` milik sendiri **tidak boleh** jadi sumber kode — aturan melarang memakai kode dari project sebelumnya.
- Produk harus deskriptif. Dilarang memberi saran investasi dan eksekusi trade otomatis. Disclaimer wajib di halaman dan README.
- Setelah submit, repo **freeze total** — tidak ada commit, push, atau edit, termasuk bugfix.
- Video 30% dari nilai, sama besar dengan technical depth. Sisakan dua hari penuh.

## File

| Lokasi | Isi |
|---|---|
| `C:\Users\User\FREEZE-BYTE\docs\superpowers\specs\2026-09-20-freeze-byte-design.md` | Spec desain final. Dokumen otoritatif untuk keputusan desain. |
| `C:\Users\User\FREEZE-BYTE\docs\superpowers\plans\2026-09-20-freeze-byte-implementation.md` | Implementation plan. 13 task, TDD, urutan eksekusi sampai submit. |
| `C:\Users\User\FREEZE-BYTE\notes.md` | Dokumen ini. |
| `C:\Users\User\study\sectors-hackathon\spec-titik-beku.md` | Spec versi pertama, lebih awal. Sebagian isinya sudah masuk spec final; simpan sebagai catatan riset, jangan jadikan acuan. |

`Sectors Hackathon 2026.pdf` adalah salinan aturan resmi. Sengaja tidak di-commit; ada di `.gitignore`.

Sectors MCP sudah tersambung ke setup Claude Code ini, tapi kode produk memakai REST API langsung lewat `client.py`. MCP untuk eksplorasi, REST untuk pipeline.
