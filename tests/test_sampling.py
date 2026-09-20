from freezebyte.sampling import pick_controls, pick_events


def test_pick_events_takes_most_recent_first():
    records = [
        {"symbol": "AAAA", "suspension_date": "2026-01-05"},
        {"symbol": "BBBB", "suspension_date": "2026-09-01"},
        {"symbol": "CCCC", "suspension_date": "2026-05-05"},
    ]
    assert [e["symbol"] for e in pick_events(records, limit=2)] == ["BBBB", "CCCC"]


def test_pick_events_keeps_only_latest_event_per_symbol():
    records = [
        {"symbol": "AAAA", "suspension_date": "2026-01-05"},
        {"symbol": "AAAA", "suspension_date": "2026-09-01"},
        {"symbol": "BBBB", "suspension_date": "2026-08-01"},
    ]
    picked = {e["symbol"]: e["suspension_date"] for e in pick_events(records, limit=10)}
    assert picked == {"AAAA": "2026-09-01", "BBBB": "2026-08-01"}


def test_pick_controls_excludes_every_suspended_symbol():
    controls = pick_controls(
        ["AAAA", "BBBB", "CCCC", "DDDD"], {"BBBB", "CCCC"}, limit=10, seed=1
    )
    assert set(controls) == {"AAAA", "DDDD"}


def test_pick_controls_is_deterministic_for_a_given_seed():
    universe = [f"S{i:03}" for i in range(200)]
    first = pick_controls(universe, set(), limit=20, seed=42)
    second = pick_controls(universe, set(), limit=20, seed=42)
    assert first == second


def test_pick_controls_respects_limit():
    universe = [f"S{i:03}" for i in range(200)]
    assert len(pick_controls(universe, set(), limit=20, seed=42)) == 20
