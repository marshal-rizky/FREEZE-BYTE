# FREEZE BYTE Extension Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a Manifest V3 browser extension that badges IDX stocks in the historical suspension zone on any page, backed by a lead-time validation, with the existing site turned into the public evidence page.

**Architecture:** The Python engine stays the single source of truth: `scoring.py` decides tiers, `validation.py` produces the proof, `export_extension.py` freezes both into JSON bundled with the extension. The extension makes zero network calls; pure JS modules (`detect.js`, `verdict.js`) are unit-tested in Node, and one DOM module (`overlay.js`) draws badges in a closed Shadow DOM layer without touching the page. The site gains a `?symbol=` deep link and a lead-time pane, and is deployed on GitHub Pages.

**Tech Stack:** Python 3.11+ (stdlib, `requests`, `python-dotenv`, `pytest`), vanilla JS (no build step, no npm dependencies), Node 24 `node --test`, Chrome Manifest V3, GitHub Pages, `gh` CLI.

**Spec:** `docs/superpowers/specs/2026-09-22-freeze-byte-extension-design.md`

## Global Constraints

- Branch: `feat/extension`. Do not merge into `main` without the user's explicit approval.
- Tier boundaries: TINGGI `ret_10d >= RET10_TERCILES[1]`; SEDANG `0.20 <= ret_10d < RET10_TERCILES[1]`; SENYAP otherwise or when `ret_10d` is `None`. The upper bound is never typed anywhere except `freezebyte/baserates.py`.
- Badge copy: TINGGI `"Di zona suspensi"`, SEDANG `"Mendekati zona suspensi"`. The words `"risiko sedang"` never appear. No probability or "chance of freezing" percentage appears anywhere; a stock's own `ret_10d` may be shown as a percentage because it is a return.
- The extension makes no network requests and never asks for an API key.
- Every API response is cached to disk before processing (`freezebyte/client.py` already does this). The `?q=` screener parameter is never used.
- Any command that spends Sectors credits is run only after printing its estimated cost and getting the user's explicit approval in chat. Budget ceiling for this plan: 387 credits. Reserve of 150 credits is never touched.
- `.env` contents are never printed. No API key is committed.
- The repo `Stocklens` is not used as a code source.
- "Bukan saran investasi" disclaimer appears in the extension description, the badge card, the popup, the site, and the README.
- Comments and user-facing strings are in Indonesian, matching the existing code. Commit messages in English, Conventional Commits, ending with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Python tests: `python -m pytest`. JS tests: `node --test "extension/test/*.test.js"`. Both must pass at the end of every task.
- Run all commands from the repo root `C:\Users\User\FREEZE-BYTE`.

## File Structure

```
freezebyte/
  scoring.py              NEW  features -> tier. Pure.
  validation.py           NEW  samples, lead-time curve, holdout, markdown report. Pure.
  universe.py             NEW  latest-features + overview selection for the universe. Pure.
  export_extension.py     NEW  data/web -> extension/data/*.json
  package_extension.py    NEW  extension/ -> dist/*.zip
  client.py               MOD  add is_price_cached()
  build.py                MOD  build_watchlist reads the universe manifest, adds tier
scripts/
  etl_overviews.py        MOD  drop the 80-candidate screener; events only
  etl_universe.py         NEW  screener + 90-day prices + flagged overviews
  report_validation.py    NEW  writes data/web/validation.json + docs/validation/lead-time.md
extension/
  manifest.json           NEW
  data/universe.json      GENERATED
  data/thresholds.json    GENERATED
  src/detect.js           NEW  URL rules + text scan. Pure.
  src/verdict.js          NEW  tier -> badge copy. Pure.
  src/anchors.js          NEW  per-site anchor selector lookup
  src/overlay.js          NEW  closed Shadow DOM layer, badges, detail card
  src/content.js          NEW  wires the above on a page
  src/popup.html, popup.js, popup.css   NEW
  test/*.test.js          NEW  node --test
  test/harness.html       NEW  fixture page for browser check
  test/fixtures/*.json    NEW
site/
  index.html, app.js, shell.js, style.css   MOD
  privacy.html            NEW
tests/
  test_scoring.py, test_validation.py, test_universe.py,
  test_export_extension.py, test_package_extension.py    NEW
  test_client.py, test_build_integration.py              MOD
docs/validation/lead-time.md   GENERATED
docs/user-testing.md           NEW
.nojekyll                      NEW
```

---

### Task 1: Tier scoring

**Files:**
- Create: `freezebyte/scoring.py`
- Test: `tests/test_scoring.py`

**Interfaces:**
- Consumes: `freezebyte.baserates.RET10_TERCILES: tuple[float, float]`, `freezebyte.baserates.bucket(features: dict) -> str`
- Produces:
  - constants `TINGGI = "tinggi"`, `SEDANG = "sedang"`, `SENYAP = "senyap"`, `NEAR_ZONE_LOWER = 0.20`
  - `upper_bound() -> float`
  - `tier(ret_10d: float | None, upper: float | None = None, near: float = NEAR_ZONE_LOWER) -> str`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_scoring.py`:

```python
import pytest

from freezebyte import baserates, scoring


def test_exact_upper_bound_is_tinggi():
    assert scoring.tier(0.315874, upper=0.315874) == scoring.TINGGI


def test_just_below_upper_bound_is_sedang():
    assert scoring.tier(0.315873, upper=0.315874) == scoring.SEDANG


def test_exact_near_lower_is_sedang():
    assert scoring.tier(0.20, upper=0.315874) == scoring.SEDANG


def test_just_below_near_lower_is_senyap():
    assert scoring.tier(0.1999, upper=0.315874) == scoring.SENYAP


def test_missing_return_is_senyap():
    assert scoring.tier(None, upper=0.315874) == scoring.SENYAP


def test_default_upper_is_read_from_baserates_at_call_time(monkeypatch):
    monkeypatch.setattr(baserates, "RET10_TERCILES", (-0.1, 0.5))
    assert scoring.upper_bound() == 0.5
    assert scoring.tier(0.4) == scoring.SEDANG
    assert scoring.tier(0.5) == scoring.TINGGI


def test_upper_below_near_leaves_no_sedang_band():
    # Kalau tercile hasil hitung ulang jatuh di bawah 0,20, SEDANG kosong --
    # bukan terbalik.
    assert scoring.tier(0.15, upper=0.1) == scoring.TINGGI
    assert scoring.tier(0.05, upper=0.1) == scoring.SENYAP


@pytest.mark.parametrize("value", [-0.5, 0.0, 0.2, 0.315873, 0.315874, 0.9])
def test_tinggi_agrees_with_r3_bucket(value):
    in_r3 = baserates.bucket({"ret_10d": value, "vol_ratio": 1.0}).startswith("r3")
    assert (scoring.tier(value) == scoring.TINGGI) == in_r3
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_scoring.py -v`
Expected: FAIL with `ImportError: cannot import name 'scoring'`

- [ ] **Step 3: Write the implementation**

Create `freezebyte/scoring.py`:

```python
"""Tingkat peringatan dari fitur. Fungsi murni.

Satu-satunya tempat tingkat diputuskan. Ekstensi dan halaman bukti membaca
hasilnya dari JSON, tidak menghitung ulang.
"""
from freezebyte import baserates

TINGGI = "tinggi"
SEDANG = "sedang"
SENYAP = "senyap"

# Batas bawah SEDANG. Pilihan tetap proyek ini, bukan hasil estimasi: data
# tidak mendukung tingkat risiko tengah (r1 dan r2 praktis identik), jadi
# SEDANG berarti "mendekati ambang", bukan kelas risiko tersendiri.
NEAR_ZONE_LOWER = 0.20


def upper_bound() -> float:
    """Batas atas tercile ret_10d. Dibaca saat dipanggil, bukan saat impor,
    supaya nilai baru dari report_discovery.py langsung berlaku."""
    return baserates.RET10_TERCILES[1]


def tier(ret_10d: float | None, upper: float | None = None,
         near: float = NEAR_ZONE_LOWER) -> str:
    """TINGGI memakai >= supaya sama persis dengan bucket r3."""
    if ret_10d is None:
        return SENYAP
    if upper is None:
        upper = upper_bound()
    if ret_10d >= upper:
        return TINGGI
    if ret_10d >= near:
        return SEDANG
    return SENYAP
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_scoring.py -v`
Expected: 13 passed

- [ ] **Step 5: Run the full suite**

Run: `python -m pytest`
Expected: all passed, 0 failed

- [ ] **Step 6: Commit**

```bash
git add freezebyte/scoring.py tests/test_scoring.py
git commit -m "feat(scoring): decide the warning tier from ret_10d in one place

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Lead-time curve and temporal holdout

**Files:**
- Create: `freezebyte/validation.py`
- Test: `tests/test_validation.py`

**Interfaces:**
- Consumes: `scoring.tier`, `scoring.TINGGI/SEDANG/SENYAP`, `scoring.NEAR_ZONE_LOWER` (Task 1); `baserates.terciles(values) -> tuple[float, float]`; `features.ret_n(rows, as_of, n) -> float | None`; `freeze.as_date(value) -> date`
- Produces:
  - `Sample` frozen dataclass: `symbol: str, role: str ("event"|"control"), anchor_date: date, as_of: date, rows: tuple[dict, ...]`
  - `build_samples(manifest: dict, load_rows: Callable[[str, list[str]], list[dict] | None]) -> tuple[list[Sample], list[tuple[str, str]]]`
  - `ret10_at_lag(sample: Sample, lag: int) -> float | None`
  - `lead_time_curve(samples, lags=LAGS, upper=None, near=NEAR_ZONE_LOWER) -> list[dict]` — each item `{"lag": int, "events": {"tinggi","sedang","senyap","tidak_terukur"}, "controls": {...}}`
  - `temporal_holdout(samples, train_fraction=TRAIN_FRACTION, near=NEAR_ZONE_LOWER) -> dict` — keys `boundary_date: str, upper: float, train: {"events": int, "controls": int}, test_events: {"n": int, "tinggi": int}, test_controls: {"n": int, "tinggi": int}`
  - `render_markdown(curve: list[dict], holdout: dict, upper: float, near: float, skipped: list[tuple[str, str]]) -> str`
  - constants `LAGS = (1, 3, 5, 10)`, `TRAIN_FRACTION = 2 / 3`, `MIN_TRADING_ROWS = 21`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_validation.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_validation.py -v`
Expected: FAIL with `ImportError: cannot import name 'validation'`

- [ ] **Step 3: Write the implementation**

Create `freezebyte/validation.py`:

```python
"""Kurva tenggang dan holdout temporal. Fungsi murni tanpa I/O.

Definisinya mengikuti scripts/report_discovery.py persis: tercile dihitung
dari gabungan kejadian dan kontrol; as_of kejadian adalah hari bursa
terakhir sebelum tanggal suspensi; as_of kontrol adalah baris berdagang
terakhir di window-nya. T-1 adalah as_of itu sendiri; T-k adalah baris
berdagang ke-(k-1) sebelum as_of.
"""
from dataclasses import dataclass
from datetime import date
from typing import Callable

from freezebyte import scoring
from freezebyte.baserates import terciles
from freezebyte.features import ret_n
from freezebyte.freeze import as_date

MIN_TRADING_ROWS = 21
LAGS = (1, 3, 5, 10)
TRAIN_FRACTION = 2 / 3
MISSING = "tidak_terukur"


@dataclass(frozen=True)
class Sample:
    symbol: str
    role: str          # "event" atau "control"
    anchor_date: date  # tanggal suspensi kejadian, atau milik pasangannya
    as_of: date
    rows: tuple


def build_samples(
    manifest: dict,
    load_rows: Callable[[str, list[str]], list[dict] | None],
) -> tuple[list[Sample], list[tuple[str, str]]]:
    entries = (
        [("event", e, e["suspension_date"]) for e in manifest["events"]]
        + [("control", c, c["paired_suspension_date"]) for c in manifest["controls"]]
    )
    samples, skipped = [], []

    for role, entry, anchor in entries:
        symbol = entry["symbol"]
        rows = load_rows(symbol, entry["window"])
        if not rows:
            skipped.append((symbol, "tidak ada baris"))
            continue

        ordered = sorted(rows, key=lambda r: as_date(r["date"]))
        trading = [r for r in ordered if r["volume"]]
        if len(trading) < MIN_TRADING_ROWS:
            skipped.append((symbol, f"hanya {len(trading)} baris berdagang"))
            continue

        if role == "event":
            before = [r for r in trading if as_date(r["date"]) < as_date(anchor)]
            if not before:
                skipped.append((symbol, "tidak ada hari bursa sebelum suspensi"))
                continue
            as_of = as_date(before[-1]["date"])
        else:
            as_of = as_date(trading[-1]["date"])

        samples.append(Sample(symbol, role, as_date(anchor), as_of, tuple(ordered)))

    return samples, skipped


def ret10_at_lag(sample: Sample, lag: int) -> float | None:
    """ret_10d dengan titik akhir mundur lag-1 hari bursa dari as_of.

    Langkah mundurnya melewati baris ber-volume nol (hari beku bukan hari
    bursa), lalu ret_n dihitung persis seperti di produksi.
    """
    trading = [r for r in sample.rows
               if r["volume"] and as_date(r["date"]) <= sample.as_of]
    index = len(trading) - lag
    if index < 0:
        return None
    return ret_n(list(sample.rows), as_date(trading[index]["date"]), 10)


def _empty_counts() -> dict:
    return {scoring.TINGGI: 0, scoring.SEDANG: 0, scoring.SENYAP: 0, MISSING: 0}


def lead_time_curve(samples: list[Sample], lags=LAGS, upper: float | None = None,
                    near: float = scoring.NEAR_ZONE_LOWER) -> list[dict]:
    """Ambang tetap untuk semua jarak -- ekstensi juga memakai ambang tetap."""
    curve = []
    for lag in lags:
        counts = {"event": _empty_counts(), "control": _empty_counts()}
        for sample in samples:
            value = ret10_at_lag(sample, lag)
            key = MISSING if value is None else scoring.tier(value, upper=upper, near=near)
            counts[sample.role][key] += 1
        curve.append({"lag": lag, "events": counts["event"], "controls": counts["control"]})
    return curve


def temporal_holdout(samples: list[Sample], train_fraction: float = TRAIN_FRACTION,
                     near: float = scoring.NEAR_ZONE_LOWER) -> dict:
    """Tercile dari kejadian tertua, diuji pada kejadian terbaru.

    Pemisahnya tanggal, bukan indeks, supaya kontrol ikut sisi kejadian
    pasangannya (anchor_date kontrol = tanggal suspensi pasangannya).
    """
    events = sorted((s for s in samples if s.role == "event"),
                    key=lambda s: (s.anchor_date, s.symbol))
    # round() dulu: 6 * (2/3) di float adalah 3.9999999999999996, dan int()
    # langsung akan memotongnya jadi 3.
    cut = int(round(len(events) * train_fraction, 9))
    if cut < 3 or cut >= len(events):
        raise ValueError("kejadian terlalu sedikit untuk holdout temporal")
    boundary = events[cut].anchor_date

    train = [s for s in samples if s.anchor_date < boundary]
    test = [s for s in samples if s.anchor_date >= boundary]
    values = [v for v in (ret10_at_lag(s, 1) for s in train) if v is not None]
    _, upper = terciles(values)

    def caught(role: str) -> dict:
        group = [s for s in test if s.role == role]
        hits = 0
        for s in group:
            value = ret10_at_lag(s, 1)
            if value is not None and scoring.tier(value, upper=upper, near=near) == scoring.TINGGI:
                hits += 1
        return {"n": len(group), "tinggi": hits}

    return {
        "boundary_date": boundary.isoformat(),
        "upper": upper,
        "train": {"events": sum(1 for s in train if s.role == "event"),
                  "controls": sum(1 for s in train if s.role == "control")},
        "test_events": caught("event"),
        "test_controls": caught("control"),
    }


def _measured(counts: dict) -> int:
    return counts[scoring.TINGGI] + counts[scoring.SEDANG] + counts[scoring.SENYAP]


def render_markdown(curve: list[dict], holdout: dict, upper: float, near: float,
                    skipped: list[tuple[str, str]]) -> str:
    """Laporan untuk docs/validation/lead-time.md. Hitungan, bukan persentase."""
    lines = [
        "# Kurva tenggang dan holdout temporal",
        "",
        "Digenerate oleh `scripts/report_validation.py`. Jangan disunting tangan.",
        "",
        f"Ambang TINGGI: `ret_10d` ≥ {upper:.6f}. Ambang SEDANG: "
        f"{near:.2f} ≤ `ret_10d` < {upper:.6f} (batas bawah dipilih tetap, "
        "bukan diestimasi). Ambang yang sama dipakai di semua jarak.",
        "",
        "## Kurva tenggang",
        "",
        "| Jarak | Kejadian TINGGI | Kejadian SEDANG | Kejadian terukur "
        "| Kontrol TINGGI | Kontrol SEDANG | Kontrol terukur |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in curve:
        e, c = row["events"], row["controls"]
        lines.append(
            f"| T−{row['lag']} | {e['tinggi']} | {e['sedang']} | {_measured(e)} "
            f"| {c['tinggi']} | {c['sedang']} | {_measured(c)} |"
        )
    missing = [(row["lag"], row["events"][MISSING] + row["controls"][MISSING])
               for row in curve if row["events"][MISSING] + row["controls"][MISSING]]
    if missing:
        lines += ["", "Tidak terukur (riwayat terlalu pendek untuk jarak itu): "
                  + ", ".join(f"T−{lag}: {n}" for lag, n in missing) + "."]

    te, tc = holdout["test_events"], holdout["test_controls"]
    lines += [
        "",
        "## Holdout temporal",
        "",
        f"Tercile dihitung dari {holdout['train']['events']} kejadian dan "
        f"{holdout['train']['controls']} kontrol dengan tanggal suspensi sebelum "
        f"{holdout['boundary_date']}. Ambang TINGGI hasilnya: {holdout['upper']:.6f}.",
        "",
        f"- Kejadian uji yang tertangkap TINGGI: {te['tinggi']} dari {te['n']}.",
        f"- Kontrol uji yang salah tertangkap TINGGI: {tc['tinggi']} dari {tc['n']}.",
        "",
        "Sampel ini case-control 1:1. Hitungan di atas bukan peluang sebuah "
        "saham dibekukan.",
    ]
    if skipped:
        lines += ["", "## Gugur", ""]
        lines += [f"- {symbol}: {reason}" for symbol, reason in skipped]
    return "\n".join(lines) + "\n"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_validation.py -v`
Expected: 11 passed

- [ ] **Step 5: Run the full suite**

Run: `python -m pytest`
Expected: all passed

- [ ] **Step 6: Commit**

```bash
git add freezebyte/validation.py tests/test_validation.py
git commit -m "feat(validation): measure how early the zone shows and test it out of time

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Universe pipeline

Replaces the 80-candidate watchlist screener with the extension universe, so the site's "Pantau" pane and the extension recognise the same symbols.

**Files:**
- Create: `freezebyte/universe.py`, `scripts/etl_universe.py`
- Modify: `freezebyte/client.py` (add `price_cache_key`, `is_price_cached`; `get_prices` uses the key function)
- Modify: `freezebyte/build.py` (`build_watchlist`, `main` prerequisites, new `_cached_structural`)
- Modify: `scripts/etl_overviews.py` (drop `candidate_symbols`)
- Test: `tests/test_universe.py`, `tests/test_client.py`, `tests/test_build_integration.py`

**Interfaces:**
- Consumes: `scoring.tier`, `scoring.TINGGI/SEDANG` (Task 1); `features.compute_features(rows, as_of, suspension_dates=(), structural=None) -> dict`; `structural.extract(overview) -> dict`; `structural.EMPTY: dict`; `build._watchlist_window() -> tuple[str, str]`
- Produces:
  - `universe.latest_features(prices: list[dict], suspension_dates=(), structural: dict | None = None) -> tuple[date, dict] | None`
  - `universe.select_for_overview(rows: list[dict], limit: int) -> list[str]` — rows have keys `symbol`, `tier`, `features`
  - `client.price_cache_key(symbol: str, start: str, end: str) -> str`
  - `client.is_price_cached(symbol: str, start: str, end: str) -> bool`
  - `data/raw/manifest_universe.json`: `{"where": str, "window": [start, end], "total_count": int, "symbols": [str], "overview_symbols": [str]}`
  - `data/web/watchlist.json` rows gain `"tier": str`; `structural` may have `available: false`

- [ ] **Step 1: Write the failing universe tests**

Create `tests/test_universe.py`:

```python
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
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_universe.py -v`
Expected: FAIL with `ImportError: cannot import name 'universe'`

- [ ] **Step 3: Implement `freezebyte/universe.py`**

```python
"""Semesta ekstensi: fitur terbaru per emiten dan pilihan overview. Fungsi murni."""
from datetime import date

from freezebyte import scoring
from freezebyte.features import compute_features
from freezebyte.freeze import as_date

MIN_TRADING_ROWS = 21


def latest_features(prices: list[dict], suspension_dates=(),
                    structural: dict | None = None) -> tuple[date, dict] | None:
    """Fitur pada hari bursa terakhir, atau None kalau riwayatnya terlalu pendek."""
    if not prices:
        return None
    ordered = sorted(prices, key=lambda r: as_date(r["date"]))
    trading = [r for r in ordered if r["volume"]]
    if len(trading) < MIN_TRADING_ROWS:
        return None
    as_of = as_date(trading[-1]["date"])
    features = compute_features(ordered, as_of, suspension_dates=suspension_dates,
                                structural=structural)
    return as_of, features


def select_for_overview(rows: list[dict], limit: int) -> list[str]:
    """Overview hanya untuk simbol yang akan dilencanai.

    Flag struktural tampil di kartu TINGGI/SEDANG saja; menarik overview
    untuk simbol SENYAP adalah kredit yang tidak pernah terlihat siapa pun.
    """
    flagged = [r for r in rows if r["tier"] in (scoring.TINGGI, scoring.SEDANG)]
    flagged.sort(key=lambda r: r["features"]["ret_10d"], reverse=True)
    return [r["symbol"] for r in flagged[:limit]]
```

- [ ] **Step 4: Run universe tests**

Run: `python -m pytest tests/test_universe.py -v`
Expected: 4 passed

- [ ] **Step 5: Write the failing client test**

Append to `tests/test_client.py`:

```python
def test_is_price_cached_matches_get_prices_cache_path(tmp_path, monkeypatch):
    from freezebyte import client, config
    monkeypatch.setattr(config, "RAW_DIR", tmp_path)
    assert client.price_cache_key("ccsi.jk", "2026-01-01", "2026-03-31") == \
        "daily/CCSI.JK_2026-01-01_2026-03-31"
    assert not client.is_price_cached("CCSI.JK", "2026-01-01", "2026-03-31")
    path = tmp_path / "daily" / "CCSI.JK_2026-01-01_2026-03-31.json"
    path.parent.mkdir(parents=True)
    path.write_text("{}", encoding="utf-8")
    assert client.is_price_cached("ccsi.jk", "2026-01-01", "2026-03-31")
```

Run: `python -m pytest tests/test_client.py -v -k is_price_cached`
Expected: FAIL with `AttributeError: module 'freezebyte.client' has no attribute 'price_cache_key'`

- [ ] **Step 6: Implement in `freezebyte/client.py`**

Replace the existing `get_prices` function with:

```python
def price_cache_key(symbol: str, start: str, end: str) -> str:
    return f"daily/{symbol.upper()}_{start}_{end}"


def is_price_cached(symbol: str, start: str, end: str) -> bool:
    """Dipakai script yang dilarang memakan kredit untuk memeriksa lebih dulu."""
    return _cache_path(price_cache_key(symbol, start, end)).exists()


def get_prices(symbol: str, start: str, end: str) -> list[dict] | None:
    symbol = symbol.upper()
    return get_json(
        f"/daily/{symbol}/",
        {"start": start, "end": end},
        price_cache_key(symbol, start, end),
    )
```

Run: `python -m pytest tests/test_client.py -v`
Expected: all passed

- [ ] **Step 7: Update the integration test fixture (failing first)**

In `tests/test_build_integration.py`, inside the `cache` fixture, directly after the `watchlist_window.json` write, add:

```python
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
```

After the `cand_rows` envelope seed, add:

```python
    _seed_envelope(
        raw_dir / "daily" / "CAND2_2026-01-01_2026-01-30.json",
        "/daily/CAND2/", {"start": "2026-01-01", "end": "2026-01-30"},
        _rows("CAND2", seed_close=300),
    )
```

In `test_coverage_analyzed_plus_excluded_equals_total`, replace the line
`assert coverage["watchlist"]["total"] == 1  # CAND1 saja; EVTA sudah "seen"` with:

```python
    assert coverage["watchlist"]["total"] == 2  # CAND1 + CAND2 dari semesta
```

Append a new test at the end of the file:

```python
def test_watchlist_rows_carry_tier_and_tolerate_missing_overview(cache):
    build.main()
    rows = json.loads((cache["web_dir"] / "watchlist.json").read_text(encoding="utf-8"))
    by_symbol = {r["symbol"]: r for r in rows}

    assert set(by_symbol) == {"CAND1", "CAND2"}
    assert all(r["tier"] in ("tinggi", "sedang", "senyap") for r in rows)
    assert by_symbol["CAND1"]["structural"]["available"] is True
    assert by_symbol["CAND2"]["structural"]["available"] is False
    assert client.NETWORK_CALLS == []
```

Run: `python -m pytest tests/test_build_integration.py -v`
Expected: FAIL — `watchlist.total` is 1 and `KeyError: 'tier'`

- [ ] **Step 8: Implement in `freezebyte/build.py`**

Add to the imports:

```python
from freezebyte import baserates, client, config, scoring, universe
from freezebyte.structural import EMPTY, extract
```

(replacing the existing `from freezebyte import baserates, client, config` and `from freezebyte.structural import extract` lines).

Replace the whole `build_watchlist` function with:

```python
def _cached_structural(symbol: str) -> dict:
    """Overview hanya dibaca kalau sudah ada di cache.

    etl_universe.py sengaja tidak menarik overview untuk simbol SENYAP.
    Memanggil client.get_overview di sini untuk simbol tanpa cache akan
    diam-diam menghabiskan satu kredit per simbol itu.
    """
    if not (config.RAW_DIR / "overview" / f"{symbol.upper()}.json").exists():
        return dict(EMPTY)
    return extract(client.get_overview(symbol))


def build_watchlist(suspensions: list[dict], coverage: Coverage) -> list[dict]:
    """Semesta ekstensi. Panel Pantau dan ekstensi mengenali simbol yang sama."""
    manifest = _read(config.RAW_DIR / "manifest_universe.json")
    symbols = manifest["symbols"]
    start, end = manifest["window"]
    coverage.total = len(symbols)
    rows = []

    for symbol in symbols:
        prices = client.get_prices(symbol, start, end)
        if not prices:
            coverage.exclude(symbol, "harga kandidat tidak tersedia")
            continue

        # C1: tanggal suspensi milik simbol ini sendiri, supaya
        # prior_freeze_count tidak selalu nol.
        symbol_dates = [
            r["suspension_date"] for r in suspensions if _base(r["symbol"]) == _base(symbol)
        ]
        structural = _cached_structural(symbol)
        latest = universe.latest_features(prices, symbol_dates, structural)
        if latest is None:
            coverage.exclude(symbol, "riwayat kandidat terlalu pendek")
            continue

        as_of, computed = latest
        rows.append({
            "symbol": symbol,
            "as_of": as_of.isoformat(),
            "features": computed,
            "bucket": baserates.bucket(computed),
            "tier": scoring.tier(computed["ret_10d"]),
            "structural": structural,
        })
        coverage.analyzed += 1

    rows.sort(
        key=lambda r: (-99 if r["features"]["ret_10d"] is None else r["features"]["ret_10d"]),
        reverse=True,
    )
    return rows
```

In `main()`, add a fourth entry to the `required` list:

```python
        (config.RAW_DIR / "manifest_universe.json", "scripts/etl_universe.py"),
```

Run: `python -m pytest tests/test_build_integration.py -v`
Expected: all passed

- [ ] **Step 9: Trim `scripts/etl_overviews.py`**

Replace the module docstring, delete `CANDIDATE_WHERE`, `CANDIDATE_LIMIT`, and `candidate_symbols()`, and change the first line of `main()`:

```python
"""Tarik overview untuk kejadian sampel, lalu petakan kosakata tag.

Biaya: 1 kredit per emiten karena hanya section overview yang diminta.
Memanggil tanpa parameter sections akan menarik 8 section dan menghabiskan 8 kredit.
Kandidat daftar pantau tidak lagi ditarik di sini; semesta ekstensi
(scripts/etl_universe.py) yang menggantikannya.
"""
```

```python
def main():
    symbols = list(dict.fromkeys(sampled_symbols()))
```

- [ ] **Step 10: Write `scripts/etl_universe.py`**

```python
"""Semesta ekstensi: screener emiten berisiko, harga 90 hari, overview bertanda.

Dua tahap, supaya biaya diketahui sebelum dibelanjakan:

    python scripts/etl_universe.py --count   # 1 kredit: cetak total_count
    python scripts/etl_universe.py --run     # screener + harga + overview

Biaya --run: 1 kredit halaman screener + <= UNIVERSE_LIMIT kredit harga +
<= MAX_OVERVIEWS kredit overview. Nol pada eksekusi ulang: semuanya dari cache.
"""
import json
import sys

from freezebyte import build, client, config, scoring, universe
from freezebyte.build import _base

UNIVERSE_WHERE = "tags in ['public-float-under-25']"
UNIVERSE_LIMIT = 150
MAX_OVERVIEWS = 50


def count() -> None:
    page = client.screen(where=UNIVERSE_WHERE, limit=1, offset=0)
    total = page["pagination"]["total_count"]
    take = min(total, UNIVERSE_LIMIT)
    print(f"total_count screener : {total}")
    print(f"akan diambil         : {take}")
    print(f"perkiraan biaya --run: <= {1 + take + MAX_OVERVIEWS} kredit")


def run() -> None:
    suspensions = json.loads(
        (config.RAW_DIR / "suspensions" / "all.json").read_text(encoding="utf-8")
    )
    page = client.screen(where=UNIVERSE_WHERE, limit=UNIVERSE_LIMIT, offset=0)
    symbols = [r["symbol"] for r in page.get("results") or []]
    start, end = build._watchlist_window()

    rows = []
    for symbol in symbols:
        prices = client.get_prices(symbol, start, end)
        dates = [r["suspension_date"] for r in suspensions
                 if _base(r["symbol"]) == _base(symbol)]
        latest = universe.latest_features(prices or [], dates)
        if latest is None:
            continue
        _, features = latest
        rows.append({"symbol": symbol, "tier": scoring.tier(features["ret_10d"]),
                     "features": features})

    overview_symbols = universe.select_for_overview(rows, MAX_OVERVIEWS)
    for symbol in overview_symbols:
        client.get_overview(symbol)

    manifest = {
        "where": UNIVERSE_WHERE,
        "window": [start, end],
        "total_count": page["pagination"]["total_count"],
        "symbols": symbols,
        "overview_symbols": overview_symbols,
    }
    path = config.RAW_DIR / "manifest_universe.json"
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    tiers = {t: sum(1 for r in rows if r["tier"] == t)
             for t in (scoring.TINGGI, scoring.SEDANG, scoring.SENYAP)}
    print(f"simbol semesta : {len(symbols)} (terukur {len(rows)})")
    print(f"per tingkat    : {tiers}")
    print(f"overview       : {len(overview_symbols)}")
    print(f"panggilan jaringan (kredit terpakai): {len(client.NETWORK_CALLS)}")


if __name__ == "__main__":
    if "--count" in sys.argv:
        count()
    elif "--run" in sys.argv:
        run()
    else:
        raise SystemExit(__doc__)
```

Check that it imports cleanly without spending anything:

Run: `python scripts/etl_universe.py`
Expected: prints the module docstring and exits with code 1; no network call.

- [ ] **Step 11: Run the full suite**

Run: `python -m pytest`
Expected: all passed

- [ ] **Step 12: Commit**

```bash
git add freezebyte/universe.py freezebyte/client.py freezebyte/build.py scripts/etl_overviews.py scripts/etl_universe.py tests/test_universe.py tests/test_client.py tests/test_build_integration.py
git commit -m "feat(universe): make the watchlist the extension's universe

The 80-candidate overview screener is replaced by a price-first
universe; overviews are pulled only for symbols that will be badged,
and the build never fetches an uncached overview.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Validation report script

**Files:**
- Create: `scripts/report_validation.py`

**Interfaces:**
- Consumes: `validation.build_samples`, `validation.lead_time_curve`, `validation.temporal_holdout`, `validation.render_markdown`, `validation.LAGS` (Task 2); `client.is_price_cached`, `client.get_prices` (Task 3); `scoring.upper_bound`, `scoring.NEAR_ZONE_LOWER`
- Produces:
  - `data/web/validation.json`: `{"lags": [...lead_time_curve...], "holdout": {...}, "n_samples": {"events": int, "controls": int}, "skipped": [[symbol, reason]], "upper": float, "near_lower": float}`
  - `docs/validation/lead-time.md`

- [ ] **Step 1: Write the script**

Create `scripts/report_validation.py`:

```python
"""Kurva tenggang dan holdout temporal dari cache harga sampel forensik.

Nol kredit, dan dijamin begitu: setiap deret harga diperiksa ada di cache
SEBELUM dibaca. Kalau satu saja belum ada, script berhenti sebelum
memanggil jaringan -- jalankan scripts/etl_prices.py lebih dulu.

Menulis data/web/validation.json dan docs/validation/lead-time.md.
"""
import json

from freezebyte import client, config, scoring, validation


def cached_rows(symbol: str, window: list[str]) -> list[dict] | None:
    if not client.is_price_cached(symbol, window[0], window[1]):
        raise SystemExit(
            f"Cache harga {symbol} {window[0]}..{window[1]} tidak ada. "
            "Jalankan scripts/etl_prices.py lebih dulu. Tidak ada kredit terpakai."
        )
    return client.get_prices(symbol, window[0], window[1])


def main() -> None:
    manifest = json.loads(
        (config.RAW_DIR / "manifest_prices.json").read_text(encoding="utf-8")
    )
    samples, skipped = validation.build_samples(manifest, cached_rows)
    upper = scoring.upper_bound()
    near = scoring.NEAR_ZONE_LOWER

    curve = validation.lead_time_curve(samples, validation.LAGS, upper=upper, near=near)
    holdout = validation.temporal_holdout(samples, near=near)

    payload = {
        "lags": curve,
        "holdout": holdout,
        "n_samples": {"events": sum(1 for s in samples if s.role == "event"),
                      "controls": sum(1 for s in samples if s.role == "control")},
        "skipped": [list(item) for item in skipped],
        "upper": upper,
        "near_lower": near,
    }
    config.WEB_DIR.mkdir(parents=True, exist_ok=True)
    (config.WEB_DIR / "validation.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    doc = config.ROOT / "docs" / "validation" / "lead-time.md"
    doc.parent.mkdir(parents=True, exist_ok=True)
    doc.write_text(validation.render_markdown(curve, holdout, upper, near, skipped),
                   encoding="utf-8")

    print(doc.read_text(encoding="utf-8"))
    print(f"panggilan jaringan: {len(client.NETWORK_CALLS)}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify it refuses to spend credits with an empty cache**

The local cache currently has no `manifest_prices.json`, so:

Run: `python scripts/report_validation.py`
Expected: fails with `FileNotFoundError` for `manifest_prices.json`, and no network call. (It runs for real in Task 6.)

- [ ] **Step 3: Commit**

```bash
git add scripts/report_validation.py
git commit -m "feat(validation): write the lead-time report from cache only

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Extension data export

**Files:**
- Create: `freezebyte/export_extension.py`
- Test: `tests/test_export_extension.py`

**Interfaces:**
- Consumes: `data/web/watchlist.json` rows (Task 3), `data/web/validation.json` (Task 4), `scoring.upper_bound`, `scoring.NEAR_ZONE_LOWER`
- Produces:
  - `EVIDENCE_URL = "https://marshal-rizky.github.io/FREEZE-BYTE/site/"`
  - `STALE_AFTER_DAYS = 7`
  - `universe_payload(watchlist: list[dict]) -> dict` → `{"symbols": [{"symbol": "CCSI", "tier": str, "ret_10d": float | None, "vol_ratio": float | None, "as_of": "YYYY-MM-DD", "flags": dict | None}]}`
  - `thresholds_payload(validation: dict, evidence_url: str, built_at: str) -> dict` → `{"upper", "near_lower", "counts": {"tinggi": {"events", "controls"}, "sedang": {...}}, "n": {"events", "controls"}, "lags", "holdout", "evidence_url", "built_at", "stale_after_days"}`
  - `extension/data/universe.json`, `extension/data/thresholds.json`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_export_extension.py`:

```python
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
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_export_extension.py -v`
Expected: FAIL with `ImportError: cannot import name 'export_extension'`

- [ ] **Step 3: Implement `freezebyte/export_extension.py`**

```python
"""data/web -> extension/data. Satu-satunya jalan ambang masuk ke ekstensi.

    python -m freezebyte.export_extension

verdict.js tidak menyimpan angka ambang; ia membaca thresholds.json yang
ditulis di sini dari baserates.py, dan tingkat per simbol sudah dihitung
scoring.py di build.
"""
import json
from datetime import datetime

from freezebyte import config, scoring

EVIDENCE_URL = "https://marshal-rizky.github.io/FREEZE-BYTE/site/"
STALE_AFTER_DAYS = 7
FLAG_KEYS = ("float_under_25", "single_entity_70", "insider_1m_sell", "at_52w_high")
EXTENSION_DATA = config.ROOT / "extension" / "data"


def _flags(structural: dict) -> dict | None:
    if not structural or not structural.get("available"):
        return None
    return {key: bool(structural.get(key)) for key in FLAG_KEYS}


def universe_payload(watchlist: list[dict]) -> dict:
    return {"symbols": [
        {
            "symbol": row["symbol"].split(".")[0].upper(),
            "tier": row["tier"],
            "ret_10d": row["features"]["ret_10d"],
            "vol_ratio": row["features"]["vol_ratio"],
            "as_of": row["as_of"],
            "flags": _flags(row.get("structural")),
        }
        for row in watchlist
    ]}


def thresholds_payload(validation: dict, evidence_url: str, built_at: str) -> dict:
    lag1 = next(row for row in validation["lags"] if row["lag"] == 1)
    return {
        "upper": scoring.upper_bound(),
        "near_lower": scoring.NEAR_ZONE_LOWER,
        "counts": {
            tier: {"events": lag1["events"][tier], "controls": lag1["controls"][tier]}
            for tier in (scoring.TINGGI, scoring.SEDANG)
        },
        "n": dict(validation["n_samples"]),
        "lags": validation["lags"],
        "holdout": validation["holdout"],
        "evidence_url": evidence_url,
        "built_at": built_at,
        "stale_after_days": STALE_AFTER_DAYS,
    }


def main() -> None:
    watchlist = json.loads((config.WEB_DIR / "watchlist.json").read_text(encoding="utf-8"))
    validation = json.loads((config.WEB_DIR / "validation.json").read_text(encoding="utf-8"))
    built_at = datetime.now().isoformat(timespec="seconds")

    EXTENSION_DATA.mkdir(parents=True, exist_ok=True)
    for name, payload in (
        ("universe.json", universe_payload(watchlist)),
        ("thresholds.json", thresholds_payload(validation, EVIDENCE_URL, built_at)),
    ):
        (EXTENSION_DATA / name).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"  ditulis: extension/data/{name}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_export_extension.py -v`
Expected: 4 passed

- [ ] **Step 5: Run the full suite and commit**

Run: `python -m pytest`
Expected: all passed

```bash
git add freezebyte/export_extension.py tests/test_export_extension.py
git commit -m "feat(export): freeze tiers and thresholds into the extension's data

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Refresh the data (spends credits)

Every credit-spending step below requires the user's explicit "ya" in chat after the estimate is shown. If a step's actual call count exceeds its estimate, stop and report before continuing.

**Files:**
- Modify: `freezebyte/baserates.py` (constants and their comment)
- Modify: `README.md` (Coverage numbers), `docs/SUBMISSION.md` (coverage line)
- Generated and committed: `data/web/*.json`, `extension/data/*.json`, `docs/validation/lead-time.md`

**Interfaces:**
- Consumes: every script from Tasks 3–5
- Produces: the real data every later task reads

- [ ] **Step 1: Confirm the remaining credit balance**

Ask the user to read the remaining credits from the Sectors hackathon dashboard and paste the number. Proceed only if it is at least 537 (387 budget + 150 reserve). If lower, lower `UNIVERSE_LIMIT` in `scripts/etl_universe.py` so that `balance - 150 >= 237 + UNIVERSE_LIMIT`, and tell the user the new limit.

- [ ] **Step 2: Forensic sample prices — ~125 credits**

Tell the user: "`etl_prices.py` akan memakan sekitar 125 kredit (120 harga + ≤5 halaman screener). Lanjut?" After "ya":

Run: `python scripts/etl_prices.py`
Expected: `kejadian berhasil` near 60, `kontrol berhasil` near 60, `panggilan jaringan` ≤ 130.

- [ ] **Step 3: Event overviews — ~60 credits**

Tell the user: "`etl_overviews.py` akan memakan sekitar 60 kredit. Lanjut?" After "ya":

Run: `python scripts/etl_overviews.py`
Expected: writes `data/raw/tag_vocabulary.json`, network calls ≤ 60.

- [ ] **Step 4: Recompute terciles — 0 credits**

Run: `python scripts/report_discovery.py`
Expected: lines `ret_10d  n=...  terciles=(a, b)` and `vol_ratio n=...  terciles=(c, d)`, network calls 0.

Copy the two tuples into `freezebyte/baserates.py`, rounded to 6 decimals, and rewrite the comment above them to state the new date (2026-09-23), the new sample size `n`, the source record count (595), and the symbols that were skipped as printed by the script.

Run: `python -m pytest`
Expected: all passed

- [ ] **Step 5: Universe count — 1 credit**

Tell the user: "Cek jumlah semesta, 1 kredit. Lanjut?" After "ya":

Run: `python scripts/etl_universe.py --count`
Expected: prints `total_count`, `akan diambil`, and `perkiraan biaya --run`.

- [ ] **Step 6: Universe prices and overviews — ≤ 201 credits**

Show the user the `perkiraan biaya --run` number from Step 5 and ask to proceed. After "ya":

Run: `python scripts/etl_universe.py --run`
Expected: writes `data/raw/manifest_universe.json`; prints counts per tier; network calls ≤ the estimate.

- [ ] **Step 7: Build, validate, export — 0 credits**

Run each and confirm `panggilan jaringan`/`network_calls_this_build` is 0:

```bash
python -m freezebyte.build
python scripts/report_validation.py
python -m freezebyte.export_extension
```

Expected: `data/web/*.json` rewritten (including `validation.json`), `docs/validation/lead-time.md` created, `extension/data/universe.json` and `thresholds.json` created.

- [ ] **Step 8: Read the result before anything else**

Open `docs/validation/lead-time.md` and report to the user, in plain words: how many events and controls are TINGGI at T−1, T−3, T−5, T−10, and the holdout result. Do not interpret beyond the counts. If controls in TINGGI at T−1 are not near zero, stop and discuss with the user before continuing — the spec's claim in §2 depends on it.

- [ ] **Step 9: Update the numbers in docs**

In `README.md` section `## Coverage` and in `docs/SUBMISSION.md` (the coverage checklist line), replace the old numbers (592 records, 120 sample, 113 analyzed, 7 dropped) with the values from the new `data/web/coverage.json` (`total_suspension_records`, `total`, `analyzed`, `excluded`). Also replace the tercile tuple quoted in `docs/SUBMISSION.md` with the new one.

- [ ] **Step 10: Full suite and commit**

Run: `python -m pytest`
Expected: all passed

```bash
git add freezebyte/baserates.py data/web extension/data docs/validation README.md docs/SUBMISSION.md
git commit -m "data: rebuild from 595 records with the extension universe and validation

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Pure extension logic — verdict and detection

**Files:**
- Create: `extension/src/verdict.js`, `extension/src/detect.js`
- Test: `extension/test/verdict.test.js`, `extension/test/detect.test.js`

**Interfaces:**
- Consumes: `thresholds.json` shape from Task 5; `universe.json` entry shape from Task 5
- Produces (attached to `globalThis.FreezeByte` in the browser, `module.exports` in Node):
  - `verdict(entry, thresholds, now: number) -> null | { tier, label, symbol, move, evidence, caveat, stale: boolean, asOf, evidenceUrl, flags }`
  - `isStale(asOf: string, now: number, days: number) -> boolean`
  - `LABELS: {tinggi: string, sedang: string}`
  - `symbolFromUrl(url: string) -> null | { site: string, symbol: string }`
  - `findSymbols(text: string, whitelist: Set<string>) -> Array<{ symbol: string, index: number }>`
  - `URL_RULES: Array<{ site: string, pattern: RegExp }>`

- [ ] **Step 1: Write the failing verdict tests**

Create `extension/test/verdict.test.js`:

```js
const test = require("node:test");
const assert = require("node:assert/strict");
const { verdict, isStale, LABELS } = require("../src/verdict.js");

const thresholds = {
  upper: 0.315874,
  near_lower: 0.2,
  counts: { tinggi: { events: 38, controls: 0 }, sedang: { events: 3, controls: 2 } },
  n: { events: 55, controls: 58 },
  evidence_url: "https://x.test/site/",
  stale_after_days: 7,
};
const NOW = Date.parse("2026-09-20T00:00:00Z");
const entry = (tier, extra = {}) => ({
  symbol: "CCSI", tier, ret_10d: 0.4966, vol_ratio: 0.99, as_of: "2026-09-18",
  flags: null, ...extra,
});

test("senyap and unknown tiers give no verdict", () => {
  assert.equal(verdict(entry("senyap"), thresholds, NOW), null);
  assert.equal(verdict(entry("lainnya"), thresholds, NOW), null);
  assert.equal(verdict(null, thresholds, NOW), null);
});

test("tinggi carries the label and the raw counts", () => {
  const v = verdict(entry("tinggi"), thresholds, NOW);
  assert.equal(v.label, "Di zona suspensi");
  assert.match(v.evidence, /38 dari 55 kejadian/);
  assert.match(v.evidence, /0 dari 58 emiten pembanding/);
  assert.match(v.move, /49,7%/);
});

test("sedang says approaching, never medium risk", () => {
  const v = verdict(entry("sedang", { ret_10d: 0.25 }), thresholds, NOW);
  assert.equal(v.label, LABELS.sedang);
  assert.equal(v.label, "Mendekati zona suspensi");
  assert.ok(!JSON.stringify(v).toLowerCase().includes("risiko sedang"));
  assert.match(v.evidence, /31,6%/);
});

test("caveat states counts are not chances and carries the disclaimer", () => {
  const v = verdict(entry("tinggi"), thresholds, NOW);
  assert.match(v.caveat, /bukan peluang/);
  assert.match(v.caveat, /Bukan saran investasi/);
});

test("evidence url deep-links the symbol", () => {
  const v = verdict(entry("tinggi"), thresholds, NOW);
  assert.equal(v.evidenceUrl, "https://x.test/site/#pantau?symbol=CCSI");
});

test("staleness flips after the configured days", () => {
  assert.equal(isStale("2026-09-18", NOW, 7), false);
  assert.equal(isStale("2026-09-10", NOW, 7), true);
  assert.equal(isStale("bukan-tanggal", NOW, 7), true);
  assert.equal(verdict(entry("tinggi", { as_of: "2026-09-01" }), thresholds, NOW).stale, true);
});
```

- [ ] **Step 2: Run to verify failure**

Run: `node --test "extension/test/*.test.js"`
Expected: FAIL with `Cannot find module '../src/verdict.js'`

- [ ] **Step 3: Implement `extension/src/verdict.js`**

```js
// Tingkat -> bunyi lencana. Murni: tidak menyentuh DOM dan tidak menyimpan
// angka ambang. Ambang dan hitungan dibaca dari thresholds.json, yang
// digenerate dari freezebyte/baserates.py -- satu sumber kebenaran.
(function (root) {
  const LABELS = {
    tinggi: "Di zona suspensi",
    sedang: "Mendekati zona suspensi",
  };
  const DAY_MS = 86400000;

  const pct = (v) =>
    (v * 100).toLocaleString("id-ID", { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + "%";

  function isStale(asOf, now, days) {
    const then = Date.parse(asOf + "T00:00:00Z");
    if (Number.isNaN(then)) return true;
    return now - then > days * DAY_MS;
  }

  function verdict(entry, thresholds, now) {
    if (!entry || !Object.prototype.hasOwnProperty.call(LABELS, entry.tier)) return null;
    const counts = thresholds.counts[entry.tier];
    const n = thresholds.n;

    const evidence = entry.tier === "tinggi"
      ? `Sehari sebelum suspensi, profil ini muncul pada ${counts.events} dari ` +
        `${n.events} kejadian suspensi, dan pada ${counts.controls} dari ` +
        `${n.controls} emiten pembanding.`
      : `Belum di zona. Batas zona: naik ${pct(thresholds.upper)} dalam 10 hari ` +
        `bursa. Sehari sebelum suspensi, ${counts.events} dari ${n.events} ` +
        `kejadian suspensi berada di rentang ini.`;

    return {
      tier: entry.tier,
      label: LABELS[entry.tier],
      symbol: entry.symbol,
      move: `Naik ${pct(entry.ret_10d)} dalam 10 hari bursa`,
      evidence,
      caveat: "Hitungan sampel kejadian dan pembanding, bukan peluang. " +
              "Bukan saran investasi.",
      stale: isStale(entry.as_of, now, thresholds.stale_after_days),
      asOf: entry.as_of,
      evidenceUrl: `${thresholds.evidence_url}#pantau?symbol=${entry.symbol}`,
      flags: entry.flags,
    };
  }

  const api = { verdict, isStale, LABELS };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.FreezeByte = Object.assign(root.FreezeByte || {}, api);
})(typeof globalThis !== "undefined" ? globalThis : this);
```

- [ ] **Step 4: Run verdict tests**

Run: `node --test "extension/test/*.test.js"`
Expected: 6 passed

- [ ] **Step 5: Write the failing detection tests**

Create `extension/test/detect.test.js`:

```js
const test = require("node:test");
const assert = require("node:assert/strict");
const { symbolFromUrl, findSymbols } = require("../src/detect.js");

const list = new Set(["CCSI", "ALKA", "BUMI"]);

test("stockbit symbol page", () => {
  assert.deepEqual(symbolFromUrl("https://stockbit.com/symbol/CCSI"),
    { site: "stockbit", symbol: "CCSI" });
  assert.deepEqual(symbolFromUrl("https://stockbit.com/symbol/ccsi/chartbit?x=1"),
    { site: "stockbit", symbol: "CCSI" });
  assert.equal(symbolFromUrl("https://stockbit.com/stream"), null);
  assert.equal(symbolFromUrl("https://stockbit.com/symbol/CCSIX"), null);
});

test("tradingview idx symbol page", () => {
  assert.deepEqual(symbolFromUrl("https://www.tradingview.com/symbols/IDX-ALKA/"),
    { site: "tradingview", symbol: "ALKA" });
  assert.deepEqual(symbolFromUrl("https://id.tradingview.com/symbols/IDX-ALKA/"),
    { site: "tradingview", symbol: "ALKA" });
  assert.equal(symbolFromUrl("https://www.tradingview.com/symbols/NASDAQ-AAPL/"), null);
});

test("google finance idx quote", () => {
  assert.deepEqual(symbolFromUrl("https://www.google.com/finance/quote/BUMI:IDX?hl=id"),
    { site: "google-finance", symbol: "BUMI" });
  assert.equal(symbolFromUrl("https://www.google.com/finance/quote/AAPL:NASDAQ"), null);
});

test("unknown sites give nothing", () => {
  assert.equal(symbolFromUrl("https://example.com/symbol/CCSI"), null);
  assert.equal(symbolFromUrl("bukan url"), null);
});

test("finds whitelisted tickers in running text with their index", () => {
  assert.deepEqual(findSymbols("Saham CCSI naik, BBCA turun.", list),
    [{ symbol: "CCSI", index: 6 }]);
});

test("finds tickers written with the exchange suffix", () => {
  assert.deepEqual(findSymbols("lihat CCSI.JK hari ini", list),
    [{ symbol: "CCSI", index: 6 }]);
});

test("ignores common four-letter caps words not in the whitelist", () => {
  assert.deepEqual(findSymbols("BUMN dan RUPS dan IHSG", list), []);
});

test("rejects a ticker inside a run of more than three caps words", () => {
  assert.deepEqual(findSymbols("BEI SUSPENSI SAHAM ALKA HARI INI", list), []);
});

test("accepts a ticker next to at most two other caps words", () => {
  assert.deepEqual(findSymbols("BEI suspensi ALKA hari ini", list),
    [{ symbol: "ALKA", index: 13 }]);
  assert.deepEqual(findSymbols("BEI ALKA IDX naik", list),
    [{ symbol: "ALKA", index: 4 }]);
});

test("does not match inside longer words", () => {
  assert.deepEqual(findSymbols("CCSIX dan XCCSI", list), []);
});
```

- [ ] **Step 6: Run to verify failure**

Run: `node --test "extension/test/*.test.js"`
Expected: detect tests FAIL with `Cannot find module '../src/detect.js'`

- [ ] **Step 7: Implement `extension/src/detect.js`**

```js
// Deteksi simbol. Murni: menjawab "simbol apa, di mana", tidak tahu apa pun
// soal risiko maupun DOM.
//
// Lapis 0 membaca simbol yang sedang DILIHAT dari URL. Lapis 1 menyapu teks
// dan hanya menerima kode yang ada di daftar putih -- daftar putih itulah
// yang membuat pola empat huruf kapital aman dipakai di situs mana pun.
(function (root) {
  // Setiap pola diverifikasi terhadap situs aslinya (Task 9) sebelum rilis.
  const URL_RULES = [
    { site: "stockbit",
      pattern: /^https:\/\/(?:www\.)?stockbit\.com\/symbol\/([A-Za-z]{4})(?:[\/?#]|$)/ },
    { site: "tradingview",
      pattern: /^https:\/\/(?:[a-z]{2,3}\.)?tradingview\.com\/symbols\/IDX-([A-Za-z]{4})(?:[\/?#]|$)/ },
    { site: "google-finance",
      pattern: /^https:\/\/www\.google\.com\/finance\/quote\/([A-Za-z]{4}):IDX(?:[\/?#]|$)/ },
  ];

  function symbolFromUrl(url) {
    for (const rule of URL_RULES) {
      const match = rule.pattern.exec(String(url));
      if (match) return { site: rule.site, symbol: match[1].toUpperCase() };
    }
    return null;
  }

  const TICKER = /\b[A-Z]{4}\b/g;
  // Kata "kapital" untuk keperluan deteksi judul: huruf besar, angka, dan
  // tanda baca, minimal dua karakter, minimal satu huruf.
  const CAPS_WORD = /^[A-Z0-9&.,:;!?()'"\-]{2,}$/;
  const MAX_CAPS_RUN = 3;

  const isCapsWord = (word) => CAPS_WORD.test(word) && /[A-Z]/.test(word);

  function capsRunLength(tokens, i) {
    let n = 1;
    for (let j = i - 1; j >= 0 && isCapsWord(tokens[j].word); j -= 1) n += 1;
    for (let j = i + 1; j < tokens.length && isCapsWord(tokens[j].word); j += 1) n += 1;
    return n;
  }

  function findSymbols(text, whitelist) {
    const found = [];
    let tokens = null;
    for (const match of text.matchAll(TICKER)) {
      const symbol = match[0];
      if (!whitelist.has(symbol)) continue;
      if (!tokens) {
        tokens = Array.from(text.matchAll(/\S+/g),
          (m) => ({ start: m.index, end: m.index + m[0].length, word: m[0] }));
      }
      const i = tokens.findIndex((t) => t.start <= match.index && match.index < t.end);
      // Judul ALL CAPS ("BEI SUSPENSI SAHAM ALKA") membuat kata biasa terlihat
      // seperti kode; kode di tengah rentetan kapital panjang ditolak.
      if (i >= 0 && capsRunLength(tokens, i) > MAX_CAPS_RUN) continue;
      found.push({ symbol, index: match.index });
    }
    return found;
  }

  const api = { symbolFromUrl, findSymbols, URL_RULES };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.FreezeByte = Object.assign(root.FreezeByte || {}, api);
})(typeof globalThis !== "undefined" ? globalThis : this);
```

- [ ] **Step 8: Run all JS tests**

Run: `node --test "extension/test/*.test.js"`
Expected: 16 passed

- [ ] **Step 9: Commit**

```bash
git add extension/src/verdict.js extension/src/detect.js extension/test/verdict.test.js extension/test/detect.test.js
git commit -m "feat(extension): pure verdict copy and ticker detection with node tests

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: Overlay, content script, manifest, popup

**Files:**
- Create: `extension/manifest.json`, `extension/src/anchors.js`, `extension/src/overlay.js`, `extension/src/content.js`, `extension/src/popup.html`, `extension/src/popup.js`, `extension/src/popup.css`
- Create: `extension/test/anchors.test.js`, `extension/test/harness.html`, `extension/test/fixtures/universe.json`, `extension/test/fixtures/thresholds.json`

**Interfaces:**
- Consumes: `verdict`, `symbolFromUrl`, `findSymbols` (Task 7) via `globalThis.FreezeByte`
- Produces:
  - `anchorFor(site: string, doc: Document) -> Element | null`, `ANCHORS: {[site]: string | null}`
  - `createOverlay(doc: Document) -> { setItems(items), schedule(), host }` where each item is `{ verdict, range?: Range, anchor?: Element | null, pinned?: boolean }`
  - `host.dataset.badges` — number of badges currently visible (test hook; the shadow root is closed)
  - Content scripts list, in load order: `src/detect.js`, `src/verdict.js`, `src/anchors.js`, `src/overlay.js`, `src/content.js`

- [ ] **Step 1: Write the failing anchors test**

Create `extension/test/anchors.test.js`:

```js
const test = require("node:test");
const assert = require("node:assert/strict");
const { anchorFor, ANCHORS } = require("../src/anchors.js");

const fakeDoc = (map) => ({
  querySelector(sel) {
    if (sel === "!!invalid") throw new Error("SyntaxError");
    return map[sel] || null;
  },
});

test("sites without a selector give no anchor", () => {
  assert.equal(anchorFor("tradingview", fakeDoc({})), null);
  assert.equal(anchorFor("tidak-dikenal", fakeDoc({})), null);
});

test("a configured selector returns the element it finds", () => {
  ANCHORS.testsite = ".harga";
  const el = { tag: "span" };
  assert.equal(anchorFor("testsite", fakeDoc({ ".harga": el })), el);
  delete ANCHORS.testsite;
});

test("a missing or invalid selector degrades to null, never throws", () => {
  ANCHORS.testsite = "!!invalid";
  assert.equal(anchorFor("testsite", fakeDoc({})), null);
  ANCHORS.testsite = ".tidak-ada";
  assert.equal(anchorFor("testsite", fakeDoc({})), null);
  delete ANCHORS.testsite;
});
```

Run: `node --test "extension/test/*.test.js"`
Expected: anchors tests FAIL with `Cannot find module '../src/anchors.js'`

- [ ] **Step 2: Implement `extension/src/anchors.js`**

```js
// Jangkar penempatan per situs. Selector di sini HANYA memutuskan di mana
// lencana dipaku -- tidak pernah dipakai untuk deteksi. Kalau selector
// meleset (markup situs berubah), lencana jatuh ke pojok: bergeser, tidak
// hilang.
(function (root) {
  const ANCHORS = {
    stockbit: null, // diisi di Task 9 dari halaman Stockbit asli
  };

  function anchorFor(site, doc) {
    const selector = ANCHORS[site];
    if (!selector) return null;
    try {
      return doc.querySelector(selector);
    } catch (err) {
      return null;
    }
  }

  const api = { anchorFor, ANCHORS };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.FreezeByte = Object.assign(root.FreezeByte || {}, api);
})(typeof globalThis !== "undefined" ? globalThis : this);
```

Run: `node --test "extension/test/*.test.js"`
Expected: 19 passed

- [ ] **Step 3: Write `extension/src/overlay.js`**

```js
// Lapisan overlay: satu-satunya modul yang menyentuh halaman, dan itu pun
// hanya menambah SATU elemen host di <html>. DOM halaman tidak pernah
// diubah -- situs SPA seperti Stockbit memiliki DOM-nya sendiri, dan span
// yang disisipkan ke text node akan ditimpa atau membuat render-nya error.
//
// Posisi lencana diukur dari Range di teks halaman dan diukur ulang saat
// scroll, resize, dan scan ulang, paling banyak sekali per frame.
(function (root) {
  const MAX_BADGES = 60;
  const MARGIN = 16;

  const CSS = `
    :host { all: initial; }
    .badge {
      position: fixed; left: 0; top: 0; pointer-events: auto; cursor: pointer;
      font: 600 11px/1 system-ui, sans-serif; letter-spacing: .01em;
      padding: 4px 7px; border-radius: 999px; border: 1px solid transparent;
      white-space: nowrap; box-shadow: 0 2px 8px rgba(0,0,0,.35);
    }
    .badge.tinggi { background: #3a0d10; color: #ffd9da; border-color: #f2555a; }
    .badge.sedang { background: #33250a; color: #ffe7b8; border-color: #e0a43a; }
    .badge::before { content: "\\25B2  "; }
    .badge.sedang::before { content: "\\25B3  "; }
    .badge[hidden] { display: none; }
    .card {
      position: fixed; right: ${MARGIN}px; top: ${MARGIN}px; width: 320px;
      pointer-events: auto; background: #0e131d; color: #eaf0f9;
      border: 1px solid rgba(255,255,255,.14); border-radius: 14px;
      box-shadow: inset 0 1px 0 rgba(255,255,255,.12), 0 18px 40px rgba(0,0,0,.5);
      padding: 16px; font: 400 13px/1.45 system-ui, sans-serif;
    }
    .card[hidden] { display: none; }
    .card h2 { font-size: 15px; margin: 0 0 4px; }
    .card .label.tinggi { color: #ff8a8e; }
    .card .label.sedang { color: #f2c46d; }
    .card p { margin: 8px 0; }
    .card .caveat, .card .stale { color: #9aa7bb; font-size: 12px; }
    .card .stale { color: #f2c46d; }
    .card a { color: #8ab8ff; }
    .card ul { margin: 6px 0; padding-left: 18px; color: #c5cfdd; }
    .card .close {
      position: absolute; right: 10px; top: 8px; background: none; border: 0;
      color: #9aa7bb; font-size: 18px; cursor: pointer;
    }
  `;

  const FLAG_LABELS = {
    float_under_25: "Free float di bawah 25%",
    single_entity_70: "Satu pihak memegang lebih dari 70%",
    insider_1m_sell: "Orang dalam menjual dalam sebulan terakhir",
    at_52w_high: "Di puncak 52 minggu",
  };

  const esc = (s) => String(s).replace(/[&<>"']/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  function cardHtml(v) {
    const flags = v.flags
      ? Object.keys(FLAG_LABELS).filter((k) => v.flags[k]).map((k) => `<li>${FLAG_LABELS[k]}</li>`)
      : [];
    return `
      <button class="close" type="button" aria-label="Tutup">&times;</button>
      <h2>${esc(v.symbol)}</h2>
      <div class="label ${esc(v.tier)}">${esc(v.label)}</div>
      <p><strong>${esc(v.move)}</strong></p>
      <p>${esc(v.evidence)}</p>
      ${flags.length ? `<p>Kondisi sekarang:</p><ul>${flags.join("")}</ul>` : ""}
      ${v.stale ? `<p class="stale">Data per ${esc(v.asOf)} &mdash; sudah lebih dari seminggu.</p>`
                : `<p class="caveat">Data per ${esc(v.asOf)}.</p>`}
      <p class="caveat">${esc(v.caveat)}</p>
      <p><a href="${esc(v.evidenceUrl)}" target="_blank" rel="noopener">Lihat buktinya</a></p>`;
  }

  function createOverlay(doc) {
    const win = doc.defaultView;
    const host = doc.createElement("freeze-byte-overlay");
    host.style.cssText =
      "position:fixed;inset:0;pointer-events:none;z-index:2147483647;display:block;";
    host.dataset.badges = "0";
    const shadow = host.attachShadow({ mode: "closed" });
    shadow.innerHTML = `<style>${CSS}</style><div class="layer"></div><div class="card" hidden></div>`;
    doc.documentElement.appendChild(host);

    const layer = shadow.querySelector(".layer");
    const card = shadow.querySelector(".card");
    let items = [];
    let frame = 0;

    function openCard(v) {
      card.innerHTML = cardHtml(v);
      card.hidden = false;
      card.querySelector(".close").addEventListener("click", () => { card.hidden = true; });
    }

    function makeBadge(v) {
      const badge = doc.createElement("button");
      badge.type = "button";
      badge.className = `badge ${v.tier}`;
      badge.textContent = `${v.symbol} · ${v.label}`;
      badge.addEventListener("click", (event) => {
        event.stopPropagation();
        openCard(v);
      });
      layer.appendChild(badge);
      return badge;
    }

    function rectOf(item) {
      if (item.range) {
        const rects = item.range.getClientRects();
        return rects.length ? rects[0] : null;
      }
      if (item.anchor && item.anchor.isConnected) return item.anchor.getBoundingClientRect();
      return null;
    }

    function place() {
      frame = 0;
      const vw = win.innerWidth;
      const vh = win.innerHeight;
      let visible = 0;
      for (const item of items) {
        const rect = rectOf(item);
        if (item.pinned && !rect) {
          // Lapis 0 tanpa jangkar: pojok kanan atas.
          item.el.hidden = false;
          item.el.style.transform =
            `translate(${vw - item.el.offsetWidth - MARGIN}px, ${MARGIN}px)`;
          visible += 1;
          continue;
        }
        const off = !rect || rect.width === 0 ||
          rect.bottom < 0 || rect.top > vh || rect.right < 0 || rect.left > vw;
        item.el.hidden = off;
        if (off) continue;
        item.el.style.transform =
          `translate(${Math.round(rect.right + 4)}px, ${Math.round(rect.top - 3)}px)`;
        visible += 1;
      }
      host.dataset.badges = String(visible);
    }

    function schedule() {
      if (!frame) frame = win.requestAnimationFrame(place);
    }

    function setItems(next) {
      layer.textContent = "";
      items = next.slice(0, MAX_BADGES).map((item) => ({ ...item, el: makeBadge(item.verdict) }));
      schedule();
    }

    win.addEventListener("scroll", schedule, { passive: true, capture: true });
    win.addEventListener("resize", schedule, { passive: true });
    return { setItems, schedule, host };
  }

  root.FreezeByte = Object.assign(root.FreezeByte || {}, { createOverlay });
})(globalThis);
```

- [ ] **Step 4: Write `extension/src/content.js`**

```js
// Merangkai deteksi, vonis, dan overlay di satu halaman. Tidak memanggil
// jaringan apa pun selain membaca dua berkas JSON milik ekstensi sendiri.
(async function () {
  const FB = globalThis.FreezeByte;
  if (!FB || globalThis.__freezeByteLoaded) return;
  globalThis.__freezeByteLoaded = true;

  const readJson = async (path) => {
    const response = await fetch(chrome.runtime.getURL(path));
    if (!response.ok) throw new Error(`${path}: HTTP ${response.status}`);
    return response.json();
  };

  let universe, thresholds;
  try {
    [universe, thresholds] = await Promise.all([
      readJson("data/universe.json"), readJson("data/thresholds.json"),
    ]);
  } catch (err) {
    console.error("FREEZE BYTE: data ekstensi gagal dimuat; ekstensi diam.", err);
    return;
  }

  const now = Date.now();
  const verdicts = new Map();
  for (const entry of universe.symbols) {
    const v = FB.verdict(entry, thresholds, now);
    if (v) verdicts.set(entry.symbol, v);
  }
  if (!verdicts.size) return;

  const whitelist = new Set(verdicts.keys());
  const overlay = FB.createOverlay(document);
  const SKIP = new Set(["SCRIPT", "STYLE", "NOSCRIPT", "TEXTAREA", "INPUT", "SELECT", "OPTION"]);
  const MAYBE_TICKER = /[A-Z]{4}/;

  function scan() {
    const items = [];

    const focused = FB.symbolFromUrl(location.href);
    if (focused && verdicts.has(focused.symbol)) {
      items.push({
        pinned: true,
        anchor: FB.anchorFor(focused.site, document),
        verdict: verdicts.get(focused.symbol),
      });
    }

    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, {
      acceptNode(node) {
        const parent = node.parentElement;
        if (!parent || SKIP.has(parent.tagName) || parent.isContentEditable) {
          return NodeFilter.FILTER_REJECT;
        }
        return MAYBE_TICKER.test(node.nodeValue)
          ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
      },
    });
    for (let node = walker.nextNode(); node; node = walker.nextNode()) {
      for (const hit of FB.findSymbols(node.nodeValue, whitelist)) {
        const range = document.createRange();
        range.setStart(node, hit.index);
        range.setEnd(node, hit.index + hit.symbol.length);
        items.push({ range, verdict: verdicts.get(hit.symbol) });
      }
    }

    overlay.setItems(items);
  }

  let timer = 0;
  const rescan = () => {
    clearTimeout(timer);
    timer = setTimeout(scan, 400);
  };
  new MutationObserver(rescan).observe(document.body, {
    childList: true, subtree: true, characterData: true,
  });
  scan();
})();
```

- [ ] **Step 5: Write `extension/manifest.json`**

```json
{
  "manifest_version": 3,
  "name": "FREEZE BYTE",
  "version": "0.1.0",
  "description": "Menandai saham IDX yang berada di zona tempat bursa secara historis membekukan perdagangan. Tanpa API key, tanpa jaringan. Bukan saran investasi.",
  "action": {
    "default_popup": "src/popup.html",
    "default_title": "FREEZE BYTE"
  },
  "permissions": ["activeTab", "scripting"],
  "host_permissions": [
    "https://stockbit.com/*",
    "https://*.stockbit.com/*",
    "https://www.tradingview.com/*",
    "https://*.tradingview.com/*",
    "https://www.google.com/finance/*",
    "https://sectors.app/*",
    "https://*.sectors.app/*",
    "https://www.idx.co.id/*",
    "https://*.rti.co.id/*",
    "https://www.investing.com/*",
    "https://id.investing.com/*"
  ],
  "optional_host_permissions": ["https://*/*"],
  "content_scripts": [
    {
      "matches": [
        "https://stockbit.com/*",
        "https://*.stockbit.com/*",
        "https://www.tradingview.com/*",
        "https://*.tradingview.com/*",
        "https://www.google.com/finance/*",
        "https://sectors.app/*",
        "https://*.sectors.app/*",
        "https://www.idx.co.id/*",
        "https://*.rti.co.id/*",
        "https://www.investing.com/*",
        "https://id.investing.com/*"
      ],
      "js": ["src/detect.js", "src/verdict.js", "src/anchors.js", "src/overlay.js", "src/content.js"],
      "run_at": "document_idle"
    }
  ],
  "web_accessible_resources": [
    {
      "resources": ["data/universe.json", "data/thresholds.json"],
      "matches": ["https://*/*"]
    }
  ]
}
```

- [ ] **Step 6: Write the popup**

`extension/src/popup.html`:

```html
<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="utf-8">
  <link rel="stylesheet" href="popup.css">
</head>
<body>
  <h1>FREEZE BYTE</h1>
  <p>Menandai saham IDX yang berada di zona tempat bursa secara historis
     membekukan perdagangan. Saham tanpa lencana <strong>tidak dikenali</strong>,
     bukan berarti aman.</p>
  <p id="status">Memeriksa halaman ini&hellip;</p>
  <button id="enable" type="button" hidden>Aktifkan di situs ini</button>
  <p class="disclaimer"><strong>Bukan saran investasi.</strong> Hitungan
     historis, bukan peluang. Tidak mengeksekusi order. Data dari Sectors API.</p>
  <script src="popup.js"></script>
</body>
</html>
```

`extension/src/popup.css`:

```css
body { width: 300px; margin: 0; padding: 16px; background: #080b12; color: #eaf0f9;
       font: 400 13px/1.45 system-ui, sans-serif; }
h1 { font-size: 15px; letter-spacing: .06em; margin: 0 0 8px; }
p { margin: 8px 0; }
#status { color: #9aa7bb; }
button { width: 100%; padding: 8px; border-radius: 10px; border: 1px solid #5b9dff;
         background: #10213d; color: #eaf0f9; font: inherit; cursor: pointer; }
.disclaimer { color: #9aa7bb; font-size: 12px; border-top: 1px solid rgba(255,255,255,.1);
              padding-top: 8px; }
```

`extension/src/popup.js`:

```js
// Popup: status situs yang sedang dibuka dan izin opt-in untuk situs di luar
// daftar bawaan. Izin diminta untuk satu origin saja, lalu content script
// didaftarkan untuk origin itu dan bertahan antar sesi.
const SCRIPTS = ["src/detect.js", "src/verdict.js", "src/anchors.js", "src/overlay.js", "src/content.js"];

document.addEventListener("DOMContentLoaded", async () => {
  const status = document.getElementById("status");
  const button = document.getElementById("enable");
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

  let url;
  try { url = new URL(tab.url); } catch (err) { url = null; }
  if (!url || url.protocol !== "https:") {
    status.textContent = "Halaman ini tidak didukung.";
    return;
  }

  const pattern = `${url.origin}/*`;
  if (await chrome.permissions.contains({ origins: [pattern] })) {
    status.textContent = `Aktif di ${url.hostname}.`;
    return;
  }

  status.textContent = `Belum aktif di ${url.hostname}.`;
  button.hidden = false;
  button.addEventListener("click", async () => {
    const granted = await chrome.permissions.request({ origins: [pattern] });
    if (!granted) return;
    const id = `fb-${url.hostname}`;
    const existing = await chrome.scripting.getRegisteredContentScripts({ ids: [id] });
    if (!existing.length) {
      await chrome.scripting.registerContentScripts([{
        id, matches: [pattern], js: SCRIPTS, runAt: "document_idle", persistAcrossSessions: true,
      }]);
    }
    await chrome.scripting.executeScript({ target: { tabId: tab.id }, files: SCRIPTS });
    status.textContent = `Aktif di ${url.hostname}.`;
    button.hidden = true;
  });
});
```

- [ ] **Step 7: Write the browser harness and its fixtures**

`extension/test/fixtures/universe.json`:

```json
{"symbols": [
  {"symbol": "AAAA", "tier": "tinggi", "ret_10d": 0.52, "vol_ratio": 1.2, "as_of": "2026-09-18",
   "flags": {"float_under_25": true, "single_entity_70": false, "insider_1m_sell": false, "at_52w_high": true}},
  {"symbol": "BBBB", "tier": "sedang", "ret_10d": 0.24, "vol_ratio": 0.9, "as_of": "2026-09-18", "flags": null},
  {"symbol": "CCCC", "tier": "senyap", "ret_10d": 0.01, "vol_ratio": 1.0, "as_of": "2026-09-18", "flags": null}
]}
```

`extension/test/fixtures/thresholds.json`:

```json
{"upper": 0.315874, "near_lower": 0.2,
 "counts": {"tinggi": {"events": 38, "controls": 0}, "sedang": {"events": 3, "controls": 2}},
 "n": {"events": 55, "controls": 58}, "lags": [], "holdout": {},
 "evidence_url": "https://marshal-rizky.github.io/FREEZE-BYTE/site/",
 "built_at": "2026-09-23T00:00:00", "stale_after_days": 7}
```

`extension/test/harness.html`:

```html
<!DOCTYPE html>
<html lang="id">
<head><meta charset="utf-8"><title>FREEZE BYTE harness</title>
<style>body{font:16px/1.6 Georgia,serif;max-width:640px;margin:40px auto;padding:0 16px}
.spacer{height:1400px}</style></head>
<body>
  <h1>Berita pasar</h1>
  <p id="p1">Saham AAAA naik tajam pekan ini. BBBB juga menguat, sementara CCCC tenang.</p>
  <p id="p2">BEI SUSPENSI SAHAM AAAA HARI INI</p>
  <p id="p3">BUMN dan RUPS tidak boleh terdeteksi.</p>
  <textarea>AAAA di dalam textarea tidak boleh terdeteksi</textarea>
  <div class="spacer"></div>
  <p id="p4">Di bawah lipatan: AAAA sekali lagi.</p>
  <script>
    // Pengganti chrome.runtime untuk halaman uji: data dibaca dari fixtures.
    globalThis.chrome = { runtime: { getURL: (p) => p.replace(/^data\//, "fixtures/") } };
    document.addEventListener("DOMContentLoaded", () => {
      window.__bodyBefore = document.body.innerHTML;
    });
  </script>
  <script src="../src/detect.js"></script>
  <script src="../src/verdict.js"></script>
  <script src="../src/anchors.js"></script>
  <script src="../src/overlay.js"></script>
  <script src="../src/content.js"></script>
</body>
</html>
```

Note: `__bodyBefore` is captured at `DOMContentLoaded`, after the parser has added every `<script>` to `body` and before `content.js` finishes its data fetch. The overlay host is attached to `<html>`, not `<body>`, so a correct extension leaves `body.innerHTML` identical.

- [ ] **Step 8: Check the harness in a browser**

Start a server from `extension/`:

Run (background): `python -m http.server 8731 --directory extension`

With the Playwright MCP browser, navigate to `http://localhost:8731/test/harness.html`, wait 1 second, then evaluate:

```js
() => ({
  badges: document.querySelector("freeze-byte-overlay")?.dataset.badges,
  bodyUnchanged: document.body.innerHTML === window.__bodyBefore,
})
```

Expected: `{ badges: "2", bodyUnchanged: true }` — AAAA and BBBB in `#p1` visible; the all-caps headline, BUMN/RUPS, CCCC (senyap), the textarea, and the below-the-fold AAAA are not visible badges.

Then scroll to the bottom (`window.scrollTo(0, document.body.scrollHeight)`), wait 200 ms, evaluate the same expression.
Expected: `badges` is `"1"` (only `#p4`).

Take a screenshot at the top of the page and look at it: badges sit just right of each ticker and do not cover the text.

Stop the server.

- [ ] **Step 9: Load the real extension once**

Ask the user to open `chrome://extensions`, turn on Developer mode, click "Load unpacked", and pick the `extension/` folder. Expected: no errors on the extension card. Ask the user to open any Stockbit or TradingView page of a symbol that is `tinggi` in `extension/data/universe.json` (read one out to them) and confirm a badge appears. Record the answer; if it fails, open the page's DevTools console and report the `FREEZE BYTE:` message.

- [ ] **Step 10: Run all tests and commit**

Run: `node --test "extension/test/*.test.js"` — Expected: 19 passed
Run: `python -m pytest` — Expected: all passed

```bash
git add extension/manifest.json extension/src extension/test
git commit -m "feat(extension): shadow-DOM overlay, content script, manifest, and popup

The page DOM is never modified; badges live in one closed shadow host
and are positioned from text ranges.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: Verify URL rules against real sites and set the Stockbit anchor

**Files:**
- Modify: `extension/src/detect.js` (`URL_RULES`), `extension/src/anchors.js` (`ANCHORS.stockbit`)
- Modify: `extension/test/detect.test.js`, `extension/test/anchors.test.js`

**Interfaces:**
- Consumes: Task 7 and Task 8 modules
- Produces: `URL_RULES` containing only verified rules; `ANCHORS.stockbit` set to a verified selector or left `null`

- [ ] **Step 1: Verify the three existing rules**

With the Playwright MCP browser, navigate to each URL and record the final URL after redirects:
- `https://stockbit.com/symbol/BBCA`
- `https://www.tradingview.com/symbols/IDX-BBCA/`
- `https://www.google.com/finance/quote/BBCA:IDX`

For each, run in Node: `node -e "console.log(require('./extension/src/detect.js').symbolFromUrl(process.argv[1]))" "<final URL>"`
Expected: `{ site: ..., symbol: 'BBCA' }`. If a final URL no longer matches, change that rule's regex so it matches the real final URL, and add that exact URL as a new assertion in `extension/test/detect.test.js` under the matching site's test.

- [ ] **Step 2: Try to add Sectors, IDX, and RTI**

For each of `sectors.app`, `www.idx.co.id`, and `rti.co.id`: open the site's home page in the Playwright MCP browser, search for `BBCA`, open its company page, and record the URL.

Decision rule, applied to each site independently:
- If the URL path contains `BBCA` as its own segment, add a rule `{ site: "<name>", pattern: <regex anchored on that host and path shape, capturing [A-Za-z]{4}> }` to `URL_RULES`, and add a test asserting that recorded URL returns `BBCA`, plus one negative test for the site's home page returning `null`.
- If the URL has no ticker in its path, or the page cannot be reached, add no rule; that site stays covered by Lapis 1 only. Write one line in the commit message saying which.

- [ ] **Step 3: Find the Stockbit anchor**

Ask the user to open `https://stockbit.com/symbol/BBCA` logged in, right-click the large last-price number, choose Inspect, and paste the element's outer HTML plus its two parent elements' outer HTML into chat.

From that markup, pick a selector that uses a stable attribute (`data-*`, `aria-*`, or a semantic tag) rather than a generated class name (random-looking classes such as `css-1x2y3z` or `sc-abc123`). Set `ANCHORS.stockbit` in `extension/src/anchors.js` to it.

If no stable attribute exists, leave `ANCHORS.stockbit = null` (corner badge) and add a comment above it recording why: generated class names change on every Stockbit deploy.

- [ ] **Step 4: Test the anchor choice**

If a selector was set, add to `extension/test/anchors.test.js`:

```js
test("stockbit anchor selector is configured and non-empty", () => {
  assert.equal(typeof ANCHORS.stockbit, "string");
  assert.ok(ANCHORS.stockbit.length > 0);
});
```

Ask the user to reload the extension in `chrome://extensions`, reload the Stockbit page for a `tinggi` symbol, and confirm the badge sits next to the price. Then ask them to temporarily break it: in DevTools console run `document.querySelector(<the selector>).remove()` and scroll slightly. Expected: the badge moves to the top-right corner and stays visible.

- [ ] **Step 5: Run tests and commit**

Run: `node --test "extension/test/*.test.js"`
Expected: all passed

```bash
git add extension/src/detect.js extension/src/anchors.js extension/test/detect.test.js extension/test/anchors.test.js
git commit -m "feat(extension): lock URL rules and the Stockbit anchor to the real sites

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 10: Evidence page — deep link, tiers, lead-time pane

**Files:**
- Modify: `site/shell.js`, `site/app.js`, `site/index.html`, `site/style.css`

**Interfaces:**
- Consumes: `data/web/watchlist.json` rows with `tier` (Task 3), `data/web/validation.json` (Task 4)
- Produces:
  - `window.freezebyteRoute = { name: string, params: URLSearchParams }` and a `freezebyte:route` document event on every route change
  - `#pantau?symbol=CCSI` filters the Pantau pane to that symbol, or explains "tidak dikenali ≠ aman"
  - New pane `#tenggang`

- [ ] **Step 1: Route with parameters in `site/shell.js`**

Replace the `parse` function with:

```js
  const parse = () => {
    const raw = location.hash.replace(/^#/, "");
    const [name, query = ""] = raw.split("?");
    return {
      name: names.has(name) ? name : DEFAULT,
      params: new URLSearchParams(query),
    };
  };
```

In `apply`, replace `const name = parse();` with:

```js
    const route = parse();
    const name = route.name;
    window.freezebyteRoute = route;
```

and at the end of `apply` (after the `links.forEach(...)` block) add:

```js
    document.dispatchEvent(new CustomEvent("freezebyte:route", { detail: route }));
```

- [ ] **Step 2: Escape the search echo and allow a custom empty state in `site/app.js`**

Add near the other helpers at the top of `site/app.js`:

```js
const esc = (s) => String(s).replace(/[&<>"']/g,
  (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
```

Change the `wireToolbar` signature to:

```js
function wireToolbar(root, items, { match, getValue, render, noun, empty }) {
```

and replace the empty-state branch inside `apply()`:

```js
    slot.innerHTML = filtered.length
      ? render(filtered)
      : empty
        ? empty(state.q.trim())
        : `<div class="empty">Tidak ada ${noun} yang cocok dengan
           "<strong>${esc(state.q.trim())}</strong>".</div>`;
```

- [ ] **Step 3: Tier chip, empty state, and deep link in `renderWatchlist`**

Add above `renderWatchlist`:

```js
// Bunyinya sama dengan lencana ekstensi. SENYAP tidak diberi chip.
const TIER_LABELS = { tinggi: "Di zona suspensi", sedang: "Mendekati zona suspensi" };
const tierChip = (tier) =>
  TIER_LABELS[tier] ? `<span class="tier ${tier}">${TIER_LABELS[tier]}</span>` : "";

function focusFromRoute(container) {
  const apply = () => {
    const route = window.freezebyteRoute;
    if (!route || route.name !== "pantau") return;
    const symbol = (route.params.get("symbol") || "").toUpperCase().replace(/[^A-Z]/g, "").slice(0, 4);
    if (!symbol) return;
    const input = container.querySelector(".search input");
    if (!input || input.value === symbol) return;
    input.value = symbol;
    input.dispatchEvent(new Event("input"));
  };
  document.addEventListener("freezebyte:route", apply);
  apply();
}
```

In the `card` template inside `renderWatchlist`, change the `.sym` block to:

```js
      <div class="sym">
        <strong>${row.symbol}</strong>
        <span class="ret${sign(row.features.ret_10d)}">${fmtPct(row.features.ret_10d)}</span>
      </div>
      ${tierChip(row.tier)}
```

In the `wireToolbar(container, watchlist, {...})` call inside `renderWatchlist`, add:

```js
    empty: (q) => `<div class="empty"><strong>${esc(q)}</strong> tidak ada di semesta
      yang dipantau. Tidak dikenali bukan berarti aman.</div>`,
```

and directly after that `wireToolbar(...)` call add:

```js
  focusFromRoute(container);
```

Also in `renderWatchlist`, change the opening empty-list message to:

```js
    container.innerHTML = `<p class="insufficient">Tidak ada emiten di semesta
      pada build terakhir.</p>`;
```

- [ ] **Step 4: Lead-time renderer in `site/app.js`**

Add above `renderSection`:

```js
function renderLeadTime(container, validation) {
  const rows = validation.lags.map((row) => {
    const e = row.events, c = row.controls;
    const measured = (x) => x.tinggi + x.sedang + x.senyap;
    return `<tr><td>T−${row.lag}</td>
      <td class="num">${e.tinggi}</td><td class="num">${e.sedang}</td><td class="num">${measured(e)}</td>
      <td class="num">${c.tinggi}</td><td class="num">${c.sedang}</td><td class="num">${measured(c)}</td></tr>`;
  }).join("");
  const h = validation.holdout;
  const fmt = (v) => v.toLocaleString("id-ID", { maximumFractionDigits: 4 });

  container.innerHTML = `
    <p>Kalau ambang zona terlihat hanya sehari sebelum suspensi, peringatannya
       sempit. Tabel ini menghitung ulang posisi setiap emiten 1, 3, 5, dan 10
       hari bursa sebelumnya, dengan ambang yang sama.</p>
    ${wrapTable(
      `<tr><th>Jarak</th><th class="num">Kejadian TINGGI</th><th class="num">Kejadian SEDANG</th>
       <th class="num">Kejadian terukur</th><th class="num">Kontrol TINGGI</th>
       <th class="num">Kontrol SEDANG</th><th class="num">Kontrol terukur</th></tr>`, rows)}
    <h3>Diuji pada kejadian yang belum pernah dilihat</h3>
    <p>Ambang dihitung ulang hanya dari kejadian sebelum ${h.boundary_date}
       (ambang hasilnya ${fmt(h.upper)}), lalu diterapkan ke kejadian sesudahnya:
       <strong>${h.test_events.tinggi} dari ${h.test_events.n}</strong> kejadian uji
       tertangkap TINGGI, dan <strong>${h.test_controls.tinggi} dari
       ${h.test_controls.n}</strong> kontrol uji salah tertangkap.</p>
    <p class="caveat">TINGGI: return 10 hari bursa ≥ ${fmt(validation.upper)}.
       SEDANG: ${fmt(validation.near_lower)} sampai di bawahnya &mdash; batas bawah ini
       dipilih tetap, bukan diestimasi. Sampel case-control 1:1; hitungan ini
       bukan peluang sebuah saham dibekukan.</p>`;
}
```

In `main()`, add `"validation"` to the parallel loads and render the pane:

```js
  const [alka, events, baserates, watchlist, coverage, meta, distribution, validation] =
    await Promise.all([
      load("alka"), load("events"), load("baserates"), load("watchlist"),
      load("coverage"), load("meta"), load("distribution"), load("validation"),
    ]);
```

```js
  renderSection("lead-time", (c) => renderLeadTime(c, validation));
```

(place the `renderSection` line next to the existing `renderSection("watchlist-table", ...)` line).

- [ ] **Step 5: Markup in `site/index.html`**

In the rail `<nav>`, after the `#pantau` link, add:

```html
        <a href="#tenggang" data-pane="tenggang"><i class="dot"></i>Tenggang</a>
```

After the `pane-pantau` section, add:

```html
      <section class="pane" id="pane-tenggang" data-pane="tenggang" tabindex="-1">
        <div class="pane-head">
          <a class="back" href="#ikhtisar">&larr; Ikhtisar</a>
          <div class="row"><h2>Seberapa awal zonanya terlihat</h2></div>
        </div>
        <div class="panel"><div id="lead-time"></div></div>
      </section>
```

Replace the ikhtisar `pane-note` paragraph with:

```html
          <p class="pane-note">
            Ekstensi FREEZE BYTE menandai saham di zona ini saat Anda sedang
            melihatnya. Halaman ini buktinya.
          </p>
```

In the `pane-pantau` head, change the note to `Semesta yang dikenali ekstensi. Deskriptif, bukan prediksi.`

- [ ] **Step 6: Styles in `site/style.css`**

Add `--warn: #e0a43a;` inside the existing `:root` token block, next to `--danger`. Append:

```css
.tier {
  display: inline-block; margin-top: .4rem; padding: .15rem .55rem;
  border-radius: 999px; font-size: .75rem; font-weight: 600;
  border: 1px solid currentColor;
}
.tier.tinggi { color: var(--danger); }
.tier.sedang { color: var(--warn); }
.tier::before { content: "\25B2\00a0"; }
.tier.sedang::before { content: "\25B3\00a0"; }
```

- [ ] **Step 7: Check in the browser**

Run (background): `python -m http.server 8741`

With the Playwright MCP browser:
1. Open `http://localhost:8741/site/?v=1#tenggang`. Expected: the table has 4 rows (T−1, T−3, T−5, T−10) and the numbers match `docs/validation/lead-time.md`.
2. Pick one `tinggi` symbol from `data/web/watchlist.json` (strip `.JK`), open `http://localhost:8741/site/?v=2#pantau?symbol=<SYM>`. Expected: exactly one card, showing the "Di zona suspensi" chip.
3. Open `http://localhost:8741/site/?v=3#pantau?symbol=ZZZZ`. Expected: the empty state reads "ZZZZ tidak ada di semesta yang dipantau. Tidak dikenali bukan berarti aman."
4. Check the browser console has no errors.
5. Screenshot the Pantau and Tenggang panes and look at them for overlap or overflow at 1440px and 390px widths.

Stop the server.

- [ ] **Step 8: Commit**

```bash
git add site/shell.js site/app.js site/index.html site/style.css
git commit -m "feat(site): turn the site into the evidence page for the extension

Adds the ?symbol= deep link the extension and mobile share point to,
tier chips matching the badge copy, and the lead-time pane.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 11: Packaging and deployment

**Files:**
- Create: `freezebyte/package_extension.py`, `tests/test_package_extension.py`, `site/privacy.html`, `.nojekyll`
- Modify: `.gitignore` (add `dist/`), `README.md`

**Interfaces:**
- Consumes: `extension/` from Tasks 7–9
- Produces: `package(src: Path, out_dir: Path) -> Path` and `dist/freeze-byte-extension-<version>.zip`; public URLs `https://marshal-rizky.github.io/FREEZE-BYTE/site/` and `.../site/privacy.html`

- [ ] **Step 1: Write the failing packaging test**

Create `tests/test_package_extension.py`:

```python
import json
import zipfile

from freezebyte import package_extension


def test_package_includes_runtime_files_and_excludes_tests(tmp_path):
    src = tmp_path / "extension"
    (src / "src").mkdir(parents=True)
    (src / "data").mkdir()
    (src / "test").mkdir()
    (src / "manifest.json").write_text(json.dumps({"version": "0.1.0"}), encoding="utf-8")
    (src / "src" / "content.js").write_text("//", encoding="utf-8")
    (src / "data" / "universe.json").write_text("{}", encoding="utf-8")
    (src / "test" / "harness.html").write_text("x", encoding="utf-8")

    out = package_extension.package(src, tmp_path / "dist")

    assert out.name == "freeze-byte-extension-0.1.0.zip"
    names = set(zipfile.ZipFile(out).namelist())
    assert names == {"manifest.json", "src/content.js", "data/universe.json"}
```

Run: `python -m pytest tests/test_package_extension.py -v`
Expected: FAIL with `ImportError`

- [ ] **Step 2: Implement `freezebyte/package_extension.py`**

```python
"""extension/ -> dist/freeze-byte-extension-<versi>.zip untuk GitHub Release
dan Chrome Web Store. Folder test/ tidak ikut.

    python -m freezebyte.package_extension
"""
import json
import zipfile
from pathlib import Path

from freezebyte import config

EXCLUDED_DIRS = {"test"}


def package(src: Path, out_dir: Path) -> Path:
    version = json.loads((src / "manifest.json").read_text(encoding="utf-8"))["version"]
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"freeze-byte-extension-{version}.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(src.rglob("*")):
            relative = path.relative_to(src)
            if path.is_dir() or relative.parts[0] in EXCLUDED_DIRS:
                continue
            archive.write(path, relative.as_posix())
    return out


if __name__ == "__main__":
    print(package(config.ROOT / "extension", config.ROOT / "dist"))
```

Run: `python -m pytest tests/test_package_extension.py -v`
Expected: 1 passed

- [ ] **Step 3: Pages prerequisites and privacy page**

Create an empty `.nojekyll` at the repo root (GitHub Pages otherwise runs Jekyll and skips some paths).

Append `dist/` to `.gitignore`.

Create `site/privacy.html`:

```html
<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>FREEZE BYTE — privasi</title>
  <style>
    :root { --bg: #080b12; --ink: #eaf0f9; --muted: #9aa7bb; }
    body { background: var(--bg); color: var(--ink); max-width: 680px; margin: 48px auto;
           padding: 0 16px; font: 16px/1.6 system-ui, sans-serif; }
    p, li { color: var(--ink); } .muted { color: var(--muted); }
  </style>
</head>
<body>
  <h1>Kebijakan privasi ekstensi FREEZE BYTE</h1>
  <ul>
    <li>Ekstensi membaca teks dan alamat halaman yang sedang Anda buka, di perangkat
        Anda, untuk mencari kode saham IDX.</li>
    <li>Tidak ada data yang dikirim ke mana pun. Ekstensi tidak melakukan permintaan
        jaringan selain membaca dua berkas data yang dibawanya sendiri.</li>
    <li>Tidak ada yang disimpan: tidak ada riwayat, tidak ada akun, tidak ada analitik.</li>
    <li>Izin untuk situs tambahan hanya diberikan kalau Anda menekan "Aktifkan di situs
        ini", dan bisa dicabut dari pengaturan ekstensi browser.</li>
  </ul>
  <p class="muted">Bukan saran investasi. Kontak: melalui issue di
     github.com/marshal-rizky/FREEZE-BYTE.</p>
</body>
</html>
```

- [ ] **Step 4: README**

Add a section `## Ekstensi browser` to `README.md` directly after the project introduction, containing:

```markdown
## Ekstensi browser

FREEZE BYTE menandai saham IDX yang berada di zona tempat bursa secara historis
membekukan perdagangan, di Stockbit, TradingView, Google Finance, IDX, Sectors,
RTI, Investing.com, dan situs lain yang Anda aktifkan sendiri.

Tanpa API key, tanpa jaringan: seluruh data dibawa ekstensi.

**Pasang (Load unpacked):**
1. Unduh `freeze-byte-extension-<versi>.zip` dari halaman Releases, lalu ekstrak.
2. Buka `chrome://extensions` dan nyalakan Developer mode.
3. Klik "Load unpacked" dan pilih folder hasil ekstrak.
4. Buka halaman saham di Stockbit atau TradingView.

Lencana merah: di zona suspensi. Lencana kuning: mendekati zona. Tanpa lencana:
tidak dikenali, bukan berarti aman. Klik lencana untuk hitungan dan tautan bukti.

Halaman bukti: https://marshal-rizky.github.io/FREEZE-BYTE/site/

**Bangun ulang data** (butuh `SECTORS_API_KEY` di `.env`, memakan kredit):
`etl_suspensions.py` → `etl_prices.py` → `etl_overviews.py` →
`report_discovery.py` (salin tercile ke `baserates.py`) →
`etl_universe.py --count` lalu `--run` → `python -m freezebyte.build` →
`report_validation.py` → `python -m freezebyte.export_extension`.

**Bukan saran investasi.** Hitungan historis, bukan peluang. Tidak mengeksekusi order.
```

Also add `node --test "extension/test/*.test.js"` next to the existing `python -m pytest` line in the README's testing section.

- [ ] **Step 5: Run tests and commit**

Run: `python -m pytest` and `node --test "extension/test/*.test.js"`
Expected: all passed

```bash
git add freezebyte/package_extension.py tests/test_package_extension.py site/privacy.html .nojekyll .gitignore README.md
git commit -m "feat(release): package the extension and prepare Pages and the privacy page

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 6: Merge, publish Pages, and release — outward-facing, confirm each**

Each item below needs its own explicit "ya" from the user:

1. Push the branch: `git push -u origin feat/extension`.
2. Merge into `main` (the user decides between a PR and a direct merge; if PR: `gh pr create --base main --head feat/extension --title "feat: freeze-warning browser extension" --body-file <scratchpad file>` with the body ending in `🤖 Generated with [Claude Code](https://claude.com/claude-code)`).
3. Enable Pages from `main`, root folder:
   `gh api -X POST repos/marshal-rizky/FREEZE-BYTE/pages -f "source[branch]=main" -f "source[path]=/"`
   Then open `https://marshal-rizky.github.io/FREEZE-BYTE/site/` and `.../site/privacy.html` with the Playwright MCP browser once the deployment finishes. Expected: both load, the site shows data (HTTP 200 for every `data/web/*.json` in the network log).
4. Build the zip: `python -m freezebyte.package_extension`, then release:
   `gh release create v0.1.0 dist/freeze-byte-extension-0.1.0.zip --title "FREEZE BYTE 0.1.0" --notes "Ekstensi peringatan zona suspensi IDX. Pasang lewat Load unpacked; lihat README. Bukan saran investasi."`

- [ ] **Step 7: Chrome Web Store submission — done by the user**

Give the user these steps and the texts to paste:
1. Register at the Chrome Web Store Developer Dashboard (one-time US$5).
2. New item → upload `dist/freeze-byte-extension-0.1.0.zip`.
3. Privacy policy URL: `https://marshal-rizky.github.io/FREEZE-BYTE/site/privacy.html`.
4. Single purpose: "Menandai kode saham IDX di halaman web yang berada di zona tempat bursa secara historis membekukan perdagangan."
5. Permission justifications — `activeTab`: "Membaca alamat tab aktif saat pengguna membuka popup, untuk menawarkan aktivasi di situs itu." `scripting`: "Mendaftarkan pemindai di situs yang pengguna aktifkan sendiri." Host permissions: "Membaca teks halaman situs keuangan untuk menemukan kode saham; tidak ada data yang dikirim."
6. Data usage: tick none; certify no data is collected.

Record the submission date in `docs/SUBMISSION.md` (Task 12).

---

### Task 12: User-testing record, submission checklist, final verification

**Files:**
- Create: `docs/user-testing.md`
- Modify: `docs/SUBMISSION.md`, `docs/video-script.md`

**Interfaces:**
- Consumes: everything above

- [ ] **Step 1: Write `docs/user-testing.md`**

```markdown
# Pengujian pengguna

## Batasan

Tidak ada penguji yang aktif berinvestasi saham. Pengujinya perancang produk
sendiri, yang tahu arti setiap kata di lencana. Karena itu pengujian ini
**tidak bisa** menangkap salah baca kata-kata lencana. Yang diuji di bawah
adalah perilaku teknis dan kegunaan di situs asli.

## Uji teknis di situs asli

Dijalankan sekali sebelum merekam video, dengan ekstensi terpasang lewat
Load unpacked dan data build terakhir.

| Situs | Lencana muncul untuk simbol TINGGI/SEDANG | Tidak muncul untuk simbol di luar semesta | Ikut scroll dan resize | Halaman utuh dan tidak melambat | Kartu dan tautan bukti benar | Catatan |
|---|---|---|---|---|---|---|
| Stockbit (halaman simbol) | | | | | | |
| TradingView | | | | | | |
| Google Finance | | | | | | |
| IDX | | | | | | |
| Sectors | | | | | | |
| RTI | | | | | | |
| Investing.com (Lapis 1) | | | | | | |
| Satu artikel berita | | | | | | |

Jangkar Stockbit: selector dihapus sengaja lewat DevTools → lencana pindah ke
pojok: [ya/tidak].

## Pertanyaan uji pemahaman

Siap dipakai kalau penguji tersedia. Tidak ada data pribadi yang disimpan.

1. "Apa arti lencana ini menurutmu?"
2. "Kalau kamu mau beli saham ini, apa yang kamu lakukan sekarang?"
3. "Berapa persen kemungkinan saham ini dibekukan?" — jawaban benar: tidak disebutkan.
4. Pada saham tanpa lencana: "Artinya saham ini aman?" — jawaban benar: tidak dikenali, bukan aman.

| Penguji | Q1 | Q2 | Q3 | Q4 | Perubahan kata yang dihasilkan |
|---|---|---|---|---|---|

Belum ada penguji.
```

- [ ] **Step 2: Run the real-site checklist with the user**

Walk the user through each row of the table, filling cells with "ya", "tidak", or a short note from what they report. Where a row fails, open a fix in the relevant task's files before continuing, and note the fix in the "Catatan" cell.

- [ ] **Step 3: Update `docs/SUBMISSION.md`**

Add these rows to the requirements table and checks to "Pemeriksaan akhir sebelum submit", each checked only after actually verifying it:

```markdown
| Ekstensi terpasang lewat Load unpacked dari zip Release | Siap/Belum |
| Halaman bukti publik di GitHub Pages | Siap/Belum |
| Chrome Web Store | Disubmit <tanggal> / belum disubmit / lolos <tanggal> |
```

```markdown
- [ ] `node --test "extension/test/*.test.js"` lulus.
- [ ] `python -m pytest` lulus dari clone bersih tanpa `.env`.
- [ ] Zip Release terpasang tanpa error di `chrome://extensions`.
- [ ] `extension/` tidak berisi string API key: `git grep -nE "SECTORS_API_KEY=[\"']?[A-Za-z0-9_-]{8,}"` kosong.
- [ ] "Bukan saran investasi" ada di deskripsi manifest, kartu lencana, popup, situs, README.
- [ ] Frasa "risiko sedang" tidak ada di mana pun: `git grep -ni "risiko sedang" -- extension site` kosong.
- [ ] `docs/validation/lead-time.md` sesuai `data/web/validation.json` build terakhir.
- [ ] `docs/user-testing.md` terisi untuk seluruh baris uji teknis.
```

Update the "Sisa pekerjaan" sentence to list what actually remains after this plan.

- [ ] **Step 4: Reorder the video script**

In `docs/video-script.md`, move the product demo to the opening: first 20 seconds show a Stockbit page with a badge appearing and the card opening; then the evidence page's lead-time pane; then the ALKA case study and coverage. Keep the existing wording where it still applies, and keep the one-sentence problem statement as the voice-over opener. The final line of the script stays the disclaimer.

- [ ] **Step 5: Final verification**

Run each and paste the tail of the output into the task report:

```bash
python -m pytest
node --test "extension/test/*.test.js"
git grep -nE "SECTORS_API_KEY=[\"']?[A-Za-z0-9_-]{8,}"
git grep -ni "risiko sedang" -- extension site
git ls-files .env
```

Expected: pytest all passed; node tests all passed; the three greps and `ls-files` print nothing.

- [ ] **Step 6: Commit**

```bash
git add docs/user-testing.md docs/SUBMISSION.md docs/video-script.md
git commit -m "docs: record user testing limits and the extension submission checks

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
