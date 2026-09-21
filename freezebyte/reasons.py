"""Klasifikasi teks alasan resmi IDX ke kategori. Fungsi murni.

Urutan aturan menentukan: kategori yang lebih spesifik diperiksa lebih dulu.
Kosakata di bawah berasal dari ETL penuh atas 592 record pada 2026-09-21
(lihat docs/discovery/2026-09-21-suspensions.md), yang menggantikan sampel
awal 10 record yang dibaca manual pada 2026-09-19.
"""

RULES = [
    ("lonjakan_harga", ["cooling down", "peningkatan harga", "penurunan harga",
                        "harga kumulatif", "pergerakan harga di luar kebiasaan",
                        "unusual market activity"]),
    ("kelangsungan_usaha", ["kelangsungan usaha", "going concern", "pkpu",
                            "kepailitan", "pailit"]),
    ("papan_pemantauan_khusus", ["papan pemantauan khusus", "pemantauan khusus"]),
    ("keterbukaan_informasi", ["laporan keuangan", "keterbukaan informasi",
                               "keterlambatan penyampaian", "belum menyampaikan"]),
    # Suspensi durasi: teks endpoint berbahasa Inggris untuk suspensi >6 bulan,
    # bukan gejolak harga maupun keraguan kelangsungan usaha. 56 record.
    ("suspensi_berkepanjangan", ["suspend more than 6 month"]),
    # Pelanggaran ketentuan pencatatan bursa (Peraturan I-A V.1.1/V.1.2) dan
    # keterlambatan pembayaran biaya pencatatan tahunan -- kegagalan
    # administratif, bukan kegagalan keterbukaan informasi. 25 + 7 = 32 record.
    ("ketentuan_pencatatan", ["belum memenuhi ketentuan",
                              "peraturan bursa nomor i-a",
                              "keterlambatan pembayaran"]),
    # Aksi korporasi yang mengarah ke delisting: buyback-untuk-delisting,
    # merger yang menghapus pencatatan, go-private/voluntary delisting.
    # 2 + 1 + 1 = 4 record.
    ("aksi_korporasi_delisting", ["pembelian kembali saham",
                                  "penggabungan usaha",
                                  "voluntary delisting"]),
]

UNKNOWN = "lainnya"
MISSING = "tanpa_alasan"


def classify(reason: str | None) -> str:
    if not reason or not reason.strip():
        return MISSING
    text = reason.lower()
    for label, keywords in RULES:
        if any(keyword in text for keyword in keywords):
            return label
    return UNKNOWN
