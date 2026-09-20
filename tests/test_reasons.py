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
    ],
)
def test_classify(text, expected):
    assert classify(text) == expected


def test_classify_is_case_insensitive():
    assert classify("COOLING DOWN") == "lonjakan_harga"


def test_price_surge_wins_when_text_mentions_both_surge_and_special_board():
    text = "peningkatan harga kumulatif signifikan pada saham di papan pemantauan khusus"
    assert classify(text) == "lonjakan_harga"
