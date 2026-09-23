"""I8: build offline dari cache sintetis, end-to-end lewat build.main().

Setiap test_build.py yang lain hanya menyentuh frozen_within_30d. Modul ini
adalah satu-satunya yang menjalankan build_events, build_watchlist, build_alka
dan main() bersama-sama -- di sinilah seluruh aturan kejujuran data (C1, I1,
I3, I7) sebenarnya diberlakukan.

Tidak ada apa pun di sini yang menyentuh repo/data/ yang sebenarnya: seluruh
cache disusun di bawah tmp_path milik pytest, dan requests.get dipatch untuk
melempar exception kalau sampai dipanggil -- membuktikan build sepenuhnya
dilayani dari cache tanpa menyentuh jaringan sama sekali.
"""
import datetime as dt
import json

import pytest

from freezebyte import baserates, build, client, config

START = dt.date(2026, 1, 1)
N_ROWS = 30
# Blok volume nol: 01-09..01-11 (akan dikonfirmasi lewat suspensi EVTA di
# 2026-01-10) dan satu baris tunggal 01-20 (tidak ada record suspensi yang
# jatuh di situ -- tetap `inferred`, dan harus tetap TIDAK masuk statistik).
FREEZE_DAYS = {dt.date(2026, 1, 9), dt.date(2026, 1, 10), dt.date(2026, 1, 11),
               dt.date(2026, 1, 20)}


def _rows(symbol: str, seed_close: int, freeze_days: set = frozenset()) -> list[dict]:
    rows = []
    last_close = seed_close
    for i in range(N_ROWS):
        d = START + dt.timedelta(days=i)
        if d in freeze_days:
            rows.append({
                "symbol": symbol, "date": d.isoformat(),
                "open": last_close, "high": last_close, "low": last_close,
                "close": last_close, "volume": 0, "market_cap": last_close * 1000,
            })
            continue
        close = seed_close + i * 5
        rows.append({
            "symbol": symbol, "date": d.isoformat(),
            "open": close - 2, "high": close + 3, "low": close - 5,
            "close": close, "volume": 1000 + i * 7, "market_cap": close * 1000,
        })
        last_close = close
    return rows


def _seed_envelope(path, endpoint, params, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"endpoint": endpoint, "params": params, "payload": payload}),
        encoding="utf-8",
    )


@pytest.fixture
def cache(tmp_path, monkeypatch):
    """Susun cache data/raw sintetis dan arahkan config ke tmp_path."""
    raw_dir = tmp_path / "raw"
    web_dir = tmp_path / "web"
    monkeypatch.setattr(config, "RAW_DIR", raw_dir)
    monkeypatch.setattr(config, "WEB_DIR", web_dir)
    # config.FIXTURE_DIR SENGAJA tidak dipatch -- build_alka harus tetap
    # membaca tests/fixtures/alka_daily.json yang benar-benar dikomit.

    # Terciles placeholder akan membuat _check_terciles_ready() menolak
    # build (itu perilaku yang diinginkan di repo nyata -- lihat I7). Untuk
    # test integrasi ini kita perlu build yang benar-benar jalan, jadi
    # dipatch ke nilai non-placeholder di memori saja; tidak ditulis ke file
    # mana pun.
    monkeypatch.setattr(baserates, "RET10_TERCILES", (0.0, 0.5))
    monkeypatch.setattr(baserates, "VOL_TERCILES", (1.0, 2.0))

    suspensions = [
        {"symbol": "EVTA", "suspension_date": "2026-01-10",
         "reason": "Papan Pemantauan Khusus", "pdf_url": None},
        {"symbol": "EVTA", "suspension_date": "2026-01-31",
         "reason": "Lonjakan harga", "pdf_url": "https://example.test/evta.pdf"},
        {"symbol": "ZZZZ", "suspension_date": "2026-01-05",
         "reason": "Laporan keuangan", "pdf_url": None},
    ]
    (raw_dir / "suspensions").mkdir(parents=True)
    (raw_dir / "suspensions" / "all.json").write_text(
        json.dumps(suspensions), encoding="utf-8"
    )

    manifest = {
        "events": [
            {"symbol": "EVTA", "suspension_date": "2026-01-31",
             "reason": "Lonjakan harga", "pdf_url": "https://example.test/evta.pdf",
             "window": ["2026-01-01", "2026-01-30"], "n_rows": N_ROWS},
        ],
        "controls": [
            {"symbol": "CTRL", "window": ["2026-01-01", "2026-01-30"],
             "n_rows": N_ROWS, "paired_event": "EVTA",
             "paired_suspension_date": "2026-01-31"},
        ],
        "failures": [],
    }
    (raw_dir / "manifest_prices.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )

    (raw_dir / "tag_vocabulary.json").write_text("{}", encoding="utf-8")

    # I2: window daftar pantau dipinkan ke cache supaya build_watchlist tidak
    # memakai date.today() dan diam-diam mencari harga di window yang tidak
    # kita seed (yang akan memicu network call sungguhan).
    (raw_dir / "watchlist_window.json").write_text(
        json.dumps({"start": "2026-01-01", "end": "2026-01-30"}), encoding="utf-8"
    )

    # Semesta ekstensi menggantikan penemuan kandidat lewat folder overview.
    # CAND2 sengaja tidak punya overview di cache: semesta tidak menarik
    # overview untuk simbol SENYAP, dan build tidak boleh menariknya diam-diam.
    (raw_dir / "manifest_universe.json").write_text(
        json.dumps({
            "where": "tags in ['public-float-under-25']",
            "window": ["2026-01-01", "2026-01-30"],
            "total_count": 2,
            "symbols": ["CAND1", "CAND2"],
            "overview_symbols": ["CAND1"],
        }),
        encoding="utf-8",
    )

    evta_rows = _rows("EVTA", seed_close=1000, freeze_days=FREEZE_DAYS)
    ctrl_rows = _rows("CTRL", seed_close=500)
    cand_rows = _rows("CAND1", seed_close=700)

    _seed_envelope(
        raw_dir / "daily" / "EVTA_2026-01-01_2026-01-30.json",
        "/daily/EVTA/", {"start": "2026-01-01", "end": "2026-01-30"}, evta_rows,
    )
    _seed_envelope(
        raw_dir / "daily" / "CTRL_2026-01-01_2026-01-30.json",
        "/daily/CTRL/", {"start": "2026-01-01", "end": "2026-01-30"}, ctrl_rows,
    )
    _seed_envelope(
        raw_dir / "daily" / "CAND1_2026-01-01_2026-01-30.json",
        "/daily/CAND1/", {"start": "2026-01-01", "end": "2026-01-30"}, cand_rows,
    )
    _seed_envelope(
        raw_dir / "daily" / "CAND2_2026-01-01_2026-01-30.json",
        "/daily/CAND2/", {"start": "2026-01-01", "end": "2026-01-30"},
        _rows("CAND2", seed_close=300),
    )

    _seed_envelope(
        raw_dir / "overview" / "EVTA.json",
        "/company/report/EVTA/", {"sections": "overview"},
        {"tags": ["public-float-under-25"], "market_cap": 123456, "listing_board": "Utama"},
    )
    _seed_envelope(
        raw_dir / "overview" / "CAND1.json",
        "/company/report/CAND1/", {"sections": "overview"},
        {"tags": [], "market_cap": 99999, "listing_board": "Utama"},
    )

    def explode(*args, **kwargs):
        raise AssertionError(
            "requests.get dipanggil -- build seharusnya sepenuhnya dilayani cache"
        )

    monkeypatch.setattr(client.requests, "get", explode)
    client.NETWORK_CALLS.clear()

    return {"raw_dir": raw_dir, "web_dir": web_dir}


def test_build_main_is_fully_cache_served_and_writes_all_outputs(cache):
    build.main()

    web_dir = cache["web_dir"]
    expected_files = {
        "alka.json", "events.json", "distribution.json", "baserates.json",
        "watchlist.json", "coverage.json", "meta.json",
    }
    written = {p.name for p in web_dir.glob("*.json")}
    assert expected_files <= written

    # Bukti utama I8: seluruh build dilayani cache, tidak satu pun
    # requests.get sungguhan terjadi.
    assert client.NETWORK_CALLS == []


def test_coverage_analyzed_plus_excluded_equals_total(cache):
    build.main()
    coverage = json.loads((cache["web_dir"] / "coverage.json").read_text(encoding="utf-8"))

    assert coverage["analyzed"] + coverage["excluded"] == coverage["total"]
    assert coverage["total"] == 2  # 1 event (EVTA) + 1 kontrol (CTRL)
    assert coverage["total_suspension_records"] == 3
    assert coverage["sample_events"] == 1
    assert coverage["sample_controls"] == 1
    # I1: kandidat daftar pantau punya counter sendiri, terpisah dari sampel
    # forensik di atas.
    assert coverage["watchlist"]["total"] == 2  # CAND1 + CAND2 dari semesta
    assert coverage["watchlist"]["analyzed"] + coverage["watchlist"]["excluded"] == \
        coverage["watchlist"]["total"]


def test_c1_prior_freeze_count_uses_all_suspension_dates_for_symbol(cache):
    """C1 regression guard: EVTA punya DUA record suspensi. Jendela beku
    01-09..01-11 hanya terkonfirmasi kalau build_events memakai keduanya,
    bukan cuma tanggal suspensi milik kejadian yang tersampel (2026-01-31)."""
    build.main()
    events = json.loads((cache["web_dir"] / "events.json").read_text(encoding="utf-8"))
    evta = next(e for e in events if e["symbol"] == "EVTA")

    assert evta["features"]["prior_freeze_count"] == 1

    windows = evta["windows"]
    assert len(windows) == 2
    confirmed = [w for w in windows if w["confirmed"]]
    inferred = [w for w in windows if not w["confirmed"]]
    assert len(confirmed) == 1
    assert len(inferred) == 1

    # Jendela inferred (01-20, tidak ada record suspensi yang cocok) tidak
    # boleh ikut membentuk prior_freeze_count -- kalau ikut, angkanya akan 2.
    assert confirmed[0]["end_date"] == "2026-01-11"
    assert inferred[0]["start_date"] == "2026-01-20"
    assert evta["features"]["prior_freeze_count"] == len(confirmed)


def test_insufficient_bucket_reports_sufficient_false(cache):
    build.main()
    baserates_payload = json.loads(
        (cache["web_dir"] / "baserates.json").read_text(encoding="utf-8")
    )

    # Sampel gabungan cuma 2 (1 kejadian + 1 kontrol), jauh di bawah
    # min_sample (10) -- setiap bucket harus melaporkan sufficient=False.
    assert baserates_payload["buckets"]
    assert all(not b["sufficient"] for b in baserates_payload["buckets"])
    assert baserates_payload["n_events"] == 1
    assert baserates_payload["n_controls"] == 1


def test_watchlist_rows_carry_tier_and_tolerate_missing_overview(cache):
    build.main()
    rows = json.loads((cache["web_dir"] / "watchlist.json").read_text(encoding="utf-8"))
    by_symbol = {r["symbol"]: r for r in rows}

    assert set(by_symbol) == {"CAND1", "CAND2"}
    assert all(r["tier"] in ("tinggi", "sedang", "senyap") for r in rows)
    assert by_symbol["CAND1"]["structural"]["available"] is True
    assert by_symbol["CAND2"]["structural"]["available"] is False
    assert client.NETWORK_CALLS == []
