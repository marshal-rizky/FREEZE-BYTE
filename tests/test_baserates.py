from datetime import date

import pytest

from freezebyte import baserates
from freezebyte.baserates import BaseRate, Event, base_rate, bucket, terciles


def _event(ret10, vol, frozen, reopen=None):
    return Event(
        symbol="TEST",
        as_of=date(2026, 9, 1),
        features={"ret_10d": ret10, "vol_ratio": vol},
        frozen_within_30d=frozen,
        reopen_return=reopen,
    )


def test_terciles_split_values_into_three_parts():
    low, high = terciles([float(i) for i in range(1, 10)])
    assert low == pytest.approx(3.67, abs=0.2)
    assert high == pytest.approx(6.33, abs=0.2)


def test_bucket_uses_configured_boundaries(monkeypatch):
    monkeypatch.setattr(baserates, "RET10_TERCILES", (0.05, 0.20))
    monkeypatch.setattr(baserates, "VOL_TERCILES", (1.0, 3.0))
    assert bucket({"ret_10d": 0.01, "vol_ratio": 0.5}) == "r1v1"
    assert bucket({"ret_10d": 0.10, "vol_ratio": 2.0}) == "r2v2"
    assert bucket({"ret_10d": 0.90, "vol_ratio": 9.0}) == "r3v3"


def test_bucket_is_unknown_when_a_feature_is_missing():
    assert bucket({"ret_10d": None, "vol_ratio": 2.0}) == "unknown"
    assert bucket({"ret_10d": 0.1, "vol_ratio": None}) == "unknown"


def test_base_rate_reports_insufficient_sample_below_threshold(monkeypatch):
    monkeypatch.setattr(baserates, "RET10_TERCILES", (0.05, 0.20))
    monkeypatch.setattr(baserates, "VOL_TERCILES", (1.0, 3.0))
    events = [_event(0.90, 9.0, True) for _ in range(9)]
    result = base_rate(events, "r3v3")
    assert result.n == 9
    assert result.sufficient is False


def test_base_rate_counts_frozen_and_takes_median_reopen(monkeypatch):
    monkeypatch.setattr(baserates, "RET10_TERCILES", (0.05, 0.20))
    monkeypatch.setattr(baserates, "VOL_TERCILES", (1.0, 3.0))
    events = (
        [_event(0.90, 9.0, True, -0.10) for _ in range(6)]
        + [_event(0.90, 9.0, False, -0.30) for _ in range(6)]
    )
    result = base_rate(events, "r3v3")
    assert result.n == 12
    assert result.n_frozen_within_30d == 6
    assert result.sufficient is True
    assert result.median_reopen_return == pytest.approx(-0.20)


def test_base_rate_ignores_events_from_other_buckets(monkeypatch):
    monkeypatch.setattr(baserates, "RET10_TERCILES", (0.05, 0.20))
    monkeypatch.setattr(baserates, "VOL_TERCILES", (1.0, 3.0))
    events = [_event(0.90, 9.0, True)] + [_event(0.01, 0.5, True) for _ in range(20)]
    assert base_rate(events, "r3v3").n == 1


def test_median_reopen_is_none_when_no_event_has_reopened(monkeypatch):
    monkeypatch.setattr(baserates, "RET10_TERCILES", (0.05, 0.20))
    monkeypatch.setattr(baserates, "VOL_TERCILES", (1.0, 3.0))
    events = [_event(0.90, 9.0, True, None) for _ in range(12)]
    assert base_rate(events, "r3v3").median_reopen_return is None
