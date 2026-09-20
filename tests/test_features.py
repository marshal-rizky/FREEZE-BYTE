import json
from datetime import date

import pytest

from freezebyte import config
from freezebyte.features import (
    compute_features,
    consecutive_up_days,
    dist_from_high,
    ret_n,
    vol_ratio,
)


@pytest.fixture
def alka_rows():
    return json.loads((config.FIXTURE_DIR / "alka_daily.json").read_text(encoding="utf-8"))


def _row(day, close, volume, high=None):
    return {"symbol": "TEST", "date": day, "close": close, "open": close,
            "high": close if high is None else high, "low": close,
            "volume": volume, "market_cap": 0}


def test_alka_six_row_return_matches_known_move(alka_rows):
    """3.750 pada 2026-09-07 ke 7.400 pada 2026-09-15 = +97,3% dalam 6 baris bursa."""
    assert ret_n(alka_rows, date(2026, 9, 15), 6) == pytest.approx(0.9733, abs=1e-3)


def test_ret_n_returns_none_when_history_too_short():
    rows = [_row("2026-03-05", 100, 10), _row("2026-03-06", 110, 10)]
    assert ret_n(rows, date(2026, 3, 6), 20) is None


def test_ret_n_uses_row_offset_not_calendar_offset():
    rows = [
        _row("2026-03-05", 100, 10),
        _row("2026-03-06", 110, 10),
        _row("2026-03-09", 121, 10),
    ]
    assert ret_n(rows, date(2026, 3, 9), 2) == pytest.approx(0.21)


def test_vol_ratio_excludes_frozen_rows_from_the_average():
    """Baris ber-volume nol tidak boleh menarik rata-rata ke bawah."""
    rows = [
        _row("2026-03-02", 100, 100),
        _row("2026-03-03", 100, 0),
        _row("2026-03-04", 100, 0),
        _row("2026-03-05", 100, 300),
        _row("2026-03-06", 100, 800),
    ]
    # rata-rata dari baris berdagang saja: (100 + 300) / 2 = 200; 800 / 200 = 4.0
    assert vol_ratio(rows, date(2026, 3, 6), window=4) == pytest.approx(4.0)


def test_vol_ratio_returns_none_when_no_trading_history():
    rows = [_row("2026-03-03", 100, 0), _row("2026-03-04", 100, 500)]
    assert vol_ratio(rows, date(2026, 3, 4), window=1) is None


def test_dist_from_high_ignores_zero_and_null_high():
    """Baris dengan high nol atau null muncul di data nyata dan merusak pembagian."""
    null_high_row = _row("2026-03-04", 100, 0)
    null_high_row["high"] = None

    rows = [
        _row("2026-03-02", 100, 10, high=120),
        _row("2026-03-03", 100, 0, high=0),
        null_high_row,
        _row("2026-03-05", 90, 10, high=95),
    ]
    assert dist_from_high(rows, date(2026, 3, 5), window=90) == pytest.approx(90 / 120)


def test_dist_from_high_returns_none_when_every_high_is_unusable():
    rows = [_row("2026-03-04", 100, 0, high=0), _row("2026-03-05", 100, 0, high=0)]
    assert dist_from_high(rows, date(2026, 3, 5)) is None


def test_consecutive_up_days_stops_at_flat_row():
    rows = [
        _row("2026-03-02", 100, 10),
        _row("2026-03-03", 110, 10),
        _row("2026-03-04", 110, 0),
        _row("2026-03-05", 120, 10),
    ]
    assert consecutive_up_days(rows, date(2026, 3, 5)) == 1


def test_compute_features_returns_every_documented_key(alka_rows):
    result = compute_features(alka_rows, date(2026, 9, 15))
    assert set(result) == {
        "ret_5d", "ret_10d", "ret_20d", "vol_ratio", "dist_from_high",
        "prior_freeze_count", "consecutive_up_days", "structural",
    }


def test_prior_freeze_count_only_counts_confirmed_windows_before_as_of(alka_rows):
    """Hanya jendela confirmed yang dihitung.

    Fixture punya empat deret volume nol; tiga di antaranya selesai sebelum
    2026-09-15. Dengan satu tanggal suspensi resmi (24 Agustus), hanya satu yang
    confirmed. Dua sisanya inferred dan tidak boleh ikut dihitung.
    """
    result = compute_features(
        alka_rows, date(2026, 9, 15), suspension_dates=["2026-08-24"]
    )
    assert result["prior_freeze_count"] == 1


def test_prior_freeze_count_is_zero_without_official_suspension_dates(alka_rows):
    result = compute_features(alka_rows, date(2026, 9, 15))
    assert result["prior_freeze_count"] == 0


def test_as_of_not_in_series_raises():
    rows = [_row("2026-03-05", 100, 10)]
    with pytest.raises(ValueError, match="2026-03-06"):
        compute_features(rows, date(2026, 3, 6))
