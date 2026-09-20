"""Klasifikasi teks alasan resmi IDX ke kategori. Fungsi murni.

Urutan aturan menentukan: kategori yang lebih spesifik diperiksa lebih dulu.
Kosakata di bawah berasal dari 10 record terbaru yang dibaca manual pada
2026-09-19 dan diperluas setelah ETL penuh (lihat docs/discovery/).
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
