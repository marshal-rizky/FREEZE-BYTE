from datetime import date

from freezebyte.build import frozen_within_30d


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
