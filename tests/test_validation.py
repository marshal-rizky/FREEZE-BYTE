import datetime as dt

import pytest

from freezebyte import scoring, validation
from freezebyte.validation import Sample

START = dt.date(2026, 1, 1)


def _rows(closes, start=START, symbol="X"):
    return [
        {"symbol": symbol, "date": (start + dt.timedelta(days=i)).isoformat(),
         "open": c, "high": c, "low": c, "close": c, "volume": 100}
        for i, c in enumerate(closes)
    ]


def _sample(role, closes, anchor, symbol="X"):
    rows = tuple(_rows(closes, symbol=symbol))
    return Sample(symbol=symbol, role=role, anchor_date=anchor,
                  as_of=dt.date.fromisoformat(rows[-1]["date"]), rows=rows)


def _with_return(r, n=30):
    """Deret datar 100 yang baris terakhirnya 100*(1+r): ret_10d di T-1 = r."""
    return [100.0] * (n - 1) + [100.0 * (1 + r)]


def test_ret10_at_lag_one_is_return_ending_at_as_of():
    closes = [float(100 + i) for i in range(30)]
    s = _sample("event", closes, START + dt.timedelta(days=30))
    assert validation.ret10_at_lag(s, 1) == pytest.approx(closes[29] / closes[19] - 1)


def test_ret10_at_lag_three_ends_two_trading_rows_earlier():
    closes = [float(100 + i) for i in range(30)]
    s = _sample("event", closes, START + dt.timedelta(days=30))
    assert validation.ret10_at_lag(s, 3) == pytest.approx(closes[27] / closes[17] - 1)


def test_ret10_at_lag_skips_zero_volume_rows_when_stepping_back():
    rows = _rows([float(100 + i) for i in range(30)])
    rows[28]["volume"] = 0  # hari beku, bukan hari bursa
    s = Sample("X", "event", START + dt.timedelta(days=30),
               dt.date.fromisoformat(rows[-1]["date"]), tuple(rows))
    # lag 2 melompati baris 28 dan mendarat di baris 27
    assert validation.ret10_at_lag(s, 2) == pytest.approx(127 / 117 - 1)


def test_ret10_at_lag_too_far_back_is_none():
    s = _sample("event", [100.0] * 25, START + dt.timedelta(days=25))
    assert validation.ret10_at_lag(s, 20) is None


def test_build_samples_uses_last_trading_day_before_suspension_for_events():
    rows = _rows([float(100 + i) for i in range(30)], symbol="EVT")
    manifest = {
        "events": [{"symbol": "EVT", "suspension_date": "2026-01-26",
                    "window": ["2026-01-01", "2026-01-30"]}],
        "controls": [{"symbol": "CTL", "paired_suspension_date": "2026-01-26",
                      "window": ["2026-01-01", "2026-01-30"]}],
    }
    loaded = {"EVT": rows, "CTL": _rows([50.0] * 30, symbol="CTL")}
    samples, skipped = validation.build_samples(manifest, lambda s, w: loaded[s])

    event = next(s for s in samples if s.role == "event")
    control = next(s for s in samples if s.role == "control")
    assert event.as_of == dt.date(2026, 1, 25)
    assert event.anchor_date == dt.date(2026, 1, 26)
    assert control.as_of == dt.date(2026, 1, 30)
    assert control.anchor_date == dt.date(2026, 1, 26)
    assert skipped == []


def test_build_samples_skips_short_and_missing_histories():
    manifest = {
        "events": [{"symbol": "SHORT", "suspension_date": "2026-01-26",
                    "window": ["2026-01-01", "2026-01-30"]}],
        "controls": [{"symbol": "NONE", "paired_suspension_date": "2026-01-26",
                      "window": ["2026-01-01", "2026-01-30"]}],
    }
    loaded = {"SHORT": _rows([100.0] * 10, symbol="SHORT"), "NONE": None}
    samples, skipped = validation.build_samples(manifest, lambda s, w: loaded[s])
    assert samples == []
    assert ("SHORT", "hanya 10 baris berdagang") in skipped
    assert ("NONE", "tidak ada baris") in skipped


def test_lead_time_curve_counts_by_role_and_tier():
    anchor = START + dt.timedelta(days=31)
    # Lonjakan hanya di dua baris terakhir: TINGGI di T-1, SENYAP di T-3.
    spike = [100.0] * 28 + [150.0, 150.0]
    samples = [
        _sample("event", spike, anchor, "E1"),
        _sample("control", [100.0] * 30, anchor, "C1"),
    ]
    curve = validation.lead_time_curve(samples, lags=(1, 3), upper=0.3, near=0.2)

    assert curve[0] == {
        "lag": 1,
        "events": {"tinggi": 1, "sedang": 0, "senyap": 0, "tidak_terukur": 0},
        "controls": {"tinggi": 0, "sedang": 0, "senyap": 1, "tidak_terukur": 0},
    }
    assert curve[1]["lag"] == 3
    assert curve[1]["events"]["senyap"] == 1


def test_lead_time_curve_reports_unmeasurable_separately():
    s = _sample("event", [100.0] * 12, START + dt.timedelta(days=12))
    curve = validation.lead_time_curve([s], lags=(5,), upper=0.3, near=0.2)
    assert curve[0]["events"]["tidak_terukur"] == 1
    assert curve[0]["events"]["senyap"] == 0


def test_temporal_holdout_fits_on_oldest_and_tests_on_newest():
    samples = []
    for i in range(6):
        anchor = dt.date(2026, 3, 1) + dt.timedelta(days=i)
        r_event = 0.5 if i < 4 else 0.6
        samples.append(_sample("event", _with_return(r_event), anchor, f"E{i}"))
        samples.append(_sample("control", _with_return(0.0), anchor, f"C{i}"))

    result = validation.temporal_holdout(samples, train_fraction=2 / 3, near=0.2)

    assert result["boundary_date"] == "2026-03-05"
    assert result["train"] == {"events": 4, "controls": 4}
    assert result["upper"] == pytest.approx(0.5)
    assert result["test_events"] == {"n": 2, "tinggi": 2}
    assert result["test_controls"] == {"n": 2, "tinggi": 0}


def test_temporal_holdout_refuses_too_few_events():
    samples = [_sample("event", _with_return(0.5), dt.date(2026, 3, 1), "E0")]
    with pytest.raises(ValueError):
        validation.temporal_holdout(samples)


def test_render_markdown_reports_counts_and_never_a_percentage():
    curve = [{
        "lag": 1,
        "events": {"tinggi": 38, "sedang": 3, "senyap": 14, "tidak_terukur": 0},
        "controls": {"tinggi": 0, "sedang": 2, "senyap": 56, "tidak_terukur": 0},
    }]
    holdout = {"boundary_date": "2026-08-01", "upper": 0.31,
               "train": {"events": 37, "controls": 39},
               "test_events": {"n": 18, "tinggi": 12},
               "test_controls": {"n": 19, "tinggi": 0}}
    md = validation.render_markdown(curve, holdout, upper=0.315874, near=0.2,
                                    skipped=[("BIMA.JK", "tidak ada baris")])

    assert "| T−1 | 38 | 3 | 55 | 0 | 2 | 58 |" in md
    assert "12 dari 18" in md
    assert "0 dari 19" in md
    assert "BIMA.JK" in md
    assert "%" not in md
