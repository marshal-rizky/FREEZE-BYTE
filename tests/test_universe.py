import datetime as dt

from freezebyte import scoring, universe

START = dt.date(2026, 1, 1)


def _rows(closes, zero_volume_days=()):
    return [
        {"symbol": "X", "date": (START + dt.timedelta(days=i)).isoformat(),
         "open": c, "high": c, "low": c, "close": c,
         "volume": 0 if i in zero_volume_days else 100}
        for i, c in enumerate(closes)
    ]


def test_latest_features_uses_last_trading_row():
    rows = _rows([float(100 + i) for i in range(30)], zero_volume_days={29})
    as_of, features = universe.latest_features(rows)
    assert as_of == dt.date(2026, 1, 29)
    assert features["ret_10d"] is not None


def test_latest_features_none_for_short_history():
    assert universe.latest_features(_rows([100.0] * 20)) is None


def test_latest_features_none_for_empty_prices():
    assert universe.latest_features([]) is None


def test_select_for_overview_keeps_flagged_highest_return_first():
    rows = [
        {"symbol": "A", "tier": scoring.SENYAP, "features": {"ret_10d": 0.9}},
        {"symbol": "B", "tier": scoring.SEDANG, "features": {"ret_10d": 0.25}},
        {"symbol": "C", "tier": scoring.TINGGI, "features": {"ret_10d": 0.6}},
        {"symbol": "D", "tier": scoring.TINGGI, "features": {"ret_10d": 0.4}},
    ]
    assert universe.select_for_overview(rows, limit=2) == ["C", "D"]
    assert universe.select_for_overview(rows, limit=10) == ["C", "D", "B"]
