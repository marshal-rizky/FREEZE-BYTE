from datetime import date

import pytest

from freezebyte.build import _base, build_alka, frozen_within_30d


SUSPENSIONS = [
    {"symbol": "AAAA", "suspension_date": "2026-09-20"},
    {"symbol": "BBBB", "suspension_date": "2026-09-20"},
]


def test_true_when_suspension_falls_inside_30_calendar_days():
    assert frozen_within_30d("AAAA", date(2026, 9, 1), SUSPENSIONS) is True


def test_false_when_suspension_is_beyond_30_calendar_days():
    assert frozen_within_30d("AAAA", date(2026, 8, 1), SUSPENSIONS) is False


def test_false_when_suspension_precedes_as_of():
    assert frozen_within_30d("AAAA", date(2026, 9, 25), SUSPENSIONS) is False


def test_window_is_calendar_days_not_trading_rows():
    """30 hari kalender persis masih dihitung masuk."""
    assert frozen_within_30d("AAAA", date(2026, 8, 21), SUSPENSIONS) is True
    assert frozen_within_30d("AAAA", date(2026, 8, 20), SUSPENSIONS) is False


def test_other_symbols_do_not_count():
    assert frozen_within_30d("ZZZZ", date(2026, 9, 1), SUSPENSIONS) is False


def test_frozen_within_30d_ignores_exchange_suffix():
    """I4 regression: daily endpoint symbols carry '.JK', suspensions may not."""
    suffixed = [{"symbol": "AAAA.JK", "suspension_date": "2026-09-20"}]
    assert frozen_within_30d("AAAA", date(2026, 9, 1), suffixed) is True


# --- I4: _base -----------------------------------------------------------

def test_base_strips_exchange_suffix():
    assert _base("ALKA.JK") == "ALKA"


def test_base_is_case_insensitive():
    assert _base("alka") == "ALKA"
    assert _base("alka.jk") == "ALKA"


def test_base_passes_through_plain_symbol():
    assert _base("ALKA") == "ALKA"


def test_base_handles_multiple_dots():
    assert _base("ALKA.JK.OLD") == "ALKA"


# --- I5: build_alka pre-freeze rally --------------------------------------

def test_build_alka_computes_pre_freeze_rally_return():
    """The fixture's final freeze window opens 2026-09-16. The last trading
    row before it is 2026-09-15 (close 7400); six trading rows back is
    2026-09-07 (close 3750). 7400 / 3750 - 1 == 0.9733...
    """
    suspensions = [{"symbol": "ALKA.JK", "suspension_date": "2026-09-17"}]
    result = build_alka(suspensions)
    assert result["pre_freeze_rally_rows"] == 6
    assert result["pre_freeze_rally_return"] == pytest.approx(0.97333, abs=1e-4)


def test_build_alka_rally_is_none_without_confirmed_window():
    """Without a real suspension date, every ALKA window is inferred, so the
    rally figure must not be fabricated from an unconfirmed window."""
    result = build_alka(suspensions=[])
    assert result["pre_freeze_rally_return"] is None
