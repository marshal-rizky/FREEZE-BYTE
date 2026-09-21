import pytest

from freezebyte.reasons import classify


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Penghentian Sementara Perdagangan Efek PT ALKA Tbk dalam rangka cooling down",
         "lonjakan_harga"),
        ("terjadi peningkatan harga kumulatif yang signifikan", "lonjakan_harga"),
        ("telah berada di Papan Pemantauan Khusus selama lebih dari 1 tahun",
         "papan_pemantauan_khusus"),
        ("adanya ketidakpastian kelangsungan usaha perusahaan tercatat",
         "kelangsungan_usaha"),
        ("keterlambatan penyampaian laporan keuangan", "keterbukaan_informasi"),
        ("alasan yang belum pernah kita lihat sebelumnya", "lainnya"),
        (None, "tanpa_alasan"),
        ("", "tanpa_alasan"),
        # Real texts from the full 592-record ETL (2026-09-21), one per new keyword.
        ("Suspend more than 6 month", "suspensi_berkepanjangan"),
        ("Belum memenuhi ketentuan V.1.1. dan/atau V.1.2. peraturan bursa nomor I-A",
         "ketentuan_pencatatan"),
        ("Keterlambatan pembayaran biaya pencatatan tahunan 2025", "ketentuan_pencatatan"),
        ("Dalam rangka pengalihan saham hasil pelaksanaan pembelian kembali saham "
         "(buyback) dalam rangka delisting perseroan", "aksi_korporasi_delisting"),
        ("Perseroan akan melakukan tindakan korporasi berupa penggabungan usaha yang "
         "akan mengakibatkan saham Perseroan menjadi tidak tercatat di Bursa",
         "aksi_korporasi_delisting"),
        ("Terdapat rencana perubahan status Perseroan dari Perusahaan Terbuka menjadi "
         "Perusahaan Tertutup (Go Private) dan rencana voluntary delisting saham "
         "Perseroan di Bursa Efek Indonesia.", "aksi_korporasi_delisting"),
        # Deliberately left unclassified: a keyword for a single record is overfitting.
        ("Perseroan telah menunda pembayaran amortisasi pokok ke-12 dan bunga ke-24 "
         "dari Obligasi I Kapuas Prima Coal Tahun 2018 (ZINC01E) yang seharusnya "
         "efektif dibayarkan pada tanggal 13 Februari 2025", "lainnya"),
    ],
)
def test_classify(text, expected):
    assert classify(text) == expected


def test_classify_is_case_insensitive():
    assert classify("COOLING DOWN") == "lonjakan_harga"


def test_price_surge_wins_when_text_mentions_both_surge_and_special_board():
    text = "peningkatan harga kumulatif signifikan pada saham di papan pemantauan khusus"
    assert classify(text) == "lonjakan_harga"


def test_price_surge_still_wins_against_new_categories():
    """Regression guard: a future keyword addition must not silently steal
    from the dominant lonjakan_harga category (467 of 592 real records)."""
    text = "Penghentian Sementara Perdagangan Efek PT ALKA Tbk dalam rangka cooling down"
    assert classify(text) == "lonjakan_harga"
