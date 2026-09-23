import pytest

from freezebyte import baserates, scoring


def test_exact_upper_bound_is_tinggi():
    assert scoring.tier(0.315874, upper=0.315874) == scoring.TINGGI


def test_just_below_upper_bound_is_sedang():
    assert scoring.tier(0.315873, upper=0.315874) == scoring.SEDANG


def test_exact_near_lower_is_sedang():
    assert scoring.tier(0.20, upper=0.315874) == scoring.SEDANG


def test_just_below_near_lower_is_senyap():
    assert scoring.tier(0.1999, upper=0.315874) == scoring.SENYAP


def test_missing_return_is_senyap():
    assert scoring.tier(None, upper=0.315874) == scoring.SENYAP


def test_default_upper_is_read_from_baserates_at_call_time(monkeypatch):
    monkeypatch.setattr(baserates, "RET10_TERCILES", (-0.1, 0.5))
    assert scoring.upper_bound() == 0.5
    assert scoring.tier(0.4) == scoring.SEDANG
    assert scoring.tier(0.5) == scoring.TINGGI


def test_upper_below_near_leaves_no_sedang_band():
    # Kalau tercile hasil hitung ulang jatuh di bawah 0,20, SEDANG kosong --
    # bukan terbalik.
    assert scoring.tier(0.15, upper=0.1) == scoring.TINGGI
    assert scoring.tier(0.05, upper=0.1) == scoring.SENYAP


@pytest.mark.parametrize("value", [-0.5, 0.0, 0.2, 0.315873, 0.315874, 0.9])
def test_tinggi_agrees_with_r3_bucket(value):
    in_r3 = baserates.bucket({"ret_10d": value, "vol_ratio": 1.0}).startswith("r3")
    assert (scoring.tier(value) == scoring.TINGGI) == in_r3
