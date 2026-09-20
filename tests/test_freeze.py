import json
from datetime import date

import pytest

from freezebyte import config
from freezebyte.freeze import detect_freeze_windows


@pytest.fixture
def alka_rows():
    return json.loads((config.FIXTURE_DIR / "alka_daily.json").read_text(encoding="utf-8"))


def _row(day, close, volume):
    return {"symbol": "TEST", "date": day, "close": close, "high": close,
            "open": close, "low": close, "volume": volume, "market_cap": 0}


def test_detects_four_zero_volume_runs_in_alka(alka_rows):
    """Fixture nyata punya empat deret volume nol, bukan dua.

    Dua di antaranya (2026-07-27 sehari, dan 2026-07-29..2026-08-05) tidak punya
    record suspensi resmi — persis kasus yang membuat flag `confirmed` ada.
    """
    windows = detect_freeze_windows(alka_rows)
    assert len(windows) == 4
    assert [w.n_days for w in windows] == [1, 6, 7, 3]
    assert windows[2].start_date == date(2026, 8, 24)
    assert windows[2].end_date == date(2026, 9, 2)
    assert windows[3].start_date == date(2026, 9, 16)


def test_reopen_return_of_the_august_alka_window(alka_rows):
    august = detect_freeze_windows(alka_rows)[2]
    assert august.price_at_freeze == 4580
    assert august.reopen_close == 4130
    assert august.reopen_return == pytest.approx(-0.0983, abs=5e-4)


def test_open_window_has_no_reopen_values(alka_rows):
    last = detect_freeze_windows(alka_rows)[-1]
    assert last.reopen_close is None
    assert last.reopen_return is None


def test_window_measured_by_row_order_not_calendar_gap():
    """Akhir pekan bukan hari beku. Dua baris beku yang dipisah akhir pekan tetap satu jendela."""
    rows = [
        _row("2026-03-05", 100, 500),
        _row("2026-03-06", 100, 0),   # Jumat
        _row("2026-03-09", 100, 0),   # Senin, ada jeda 2 hari kalender
        _row("2026-03-10", 90, 400),
    ]
    windows = detect_freeze_windows(rows)
    assert len(windows) == 1
    assert windows[0].n_days == 2
    assert windows[0].reopen_return == pytest.approx(-0.10)


def test_confirmed_when_suspension_date_falls_inside_window():
    rows = [
        _row("2026-03-05", 100, 500),
        _row("2026-03-06", 100, 0),
        _row("2026-03-09", 90, 400),
    ]
    confirmed = detect_freeze_windows(rows, suspension_dates=["2026-03-06"])
    assert confirmed[0].confirmed is True


def test_inferred_when_no_matching_suspension_record():
    rows = [
        _row("2026-03-05", 100, 500),
        _row("2026-03-06", 100, 0),
        _row("2026-03-09", 90, 400),
    ]
    inferred = detect_freeze_windows(rows, suspension_dates=["2025-01-02"])
    assert inferred[0].confirmed is False


def test_rows_are_sorted_before_scanning():
    rows = [
        _row("2026-03-09", 90, 400),
        _row("2026-03-05", 100, 500),
        _row("2026-03-06", 100, 0),
    ]
    windows = detect_freeze_windows(rows)
    assert len(windows) == 1
    assert windows[0].start_date == date(2026, 3, 6)


def test_min_days_filters_short_windows():
    rows = [
        _row("2026-03-05", 100, 500),
        _row("2026-03-06", 100, 0),
        _row("2026-03-09", 90, 400),
    ]
    assert detect_freeze_windows(rows, min_days=2) == []
