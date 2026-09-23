from freezebyte import baserates, export_extension

VALIDATION = {
    "lags": [
        {"lag": 1,
         "events": {"tinggi": 38, "sedang": 3, "senyap": 14, "tidak_terukur": 0},
         "controls": {"tinggi": 0, "sedang": 2, "senyap": 56, "tidak_terukur": 0}},
        {"lag": 3,
         "events": {"tinggi": 20, "sedang": 5, "senyap": 30, "tidak_terukur": 0},
         "controls": {"tinggi": 0, "sedang": 1, "senyap": 57, "tidak_terukur": 0}},
    ],
    "holdout": {"boundary_date": "2026-08-01"},
    "n_samples": {"events": 55, "controls": 58},
}


def test_thresholds_upper_comes_from_baserates(monkeypatch):
    monkeypatch.setattr(baserates, "RET10_TERCILES", (-0.02, 0.4))
    payload = export_extension.thresholds_payload(VALIDATION, "https://x.test/", "2026-09-23")
    assert payload["upper"] == 0.4
    assert payload["near_lower"] == 0.20


def test_thresholds_counts_are_the_lag_one_row():
    payload = export_extension.thresholds_payload(VALIDATION, "https://x.test/", "2026-09-23")
    assert payload["counts"] == {
        "tinggi": {"events": 38, "controls": 0},
        "sedang": {"events": 3, "controls": 2},
    }
    assert payload["n"] == {"events": 55, "controls": 58}
    assert payload["stale_after_days"] == 7
    assert payload["evidence_url"] == "https://x.test/"


def test_universe_strips_exchange_suffix_and_keeps_tier():
    watchlist = [{
        "symbol": "CCSI.JK", "as_of": "2026-09-18", "tier": "tinggi",
        "features": {"ret_10d": 0.49, "vol_ratio": 0.99},
        "structural": {"available": True, "float_under_25": True,
                       "single_entity_70": False, "insider_1m_sell": False,
                       "at_52w_high": True, "tags": ["x"], "market_cap": 1},
    }]
    payload = export_extension.universe_payload(watchlist)
    assert payload == {"symbols": [{
        "symbol": "CCSI", "tier": "tinggi", "ret_10d": 0.49, "vol_ratio": 0.99,
        "as_of": "2026-09-18",
        "flags": {"float_under_25": True, "single_entity_70": False,
                  "insider_1m_sell": False, "at_52w_high": True},
    }]}


def test_universe_flags_are_none_without_overview():
    watchlist = [{"symbol": "ABCD.JK", "as_of": "2026-09-18", "tier": "senyap",
                  "features": {"ret_10d": 0.01, "vol_ratio": 1.1},
                  "structural": {"available": False}}]
    assert export_extension.universe_payload(watchlist)["symbols"][0]["flags"] is None
