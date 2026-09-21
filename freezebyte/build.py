"""Orkestrasi: baca cache, jalankan mesin, tulis data/web/*.json.

Tidak memanggil jaringan untuk data yang sudah ada di cache, jadi build ulang gratis.
"""
import json
from dataclasses import asdict
from datetime import date, datetime, timedelta

from freezebyte import client, config
from freezebyte.baserates import (
    MIN_SAMPLE,
    RET10_TERCILES,
    VOL_TERCILES,
    Event,
    base_rate,
    bucket,
)
from freezebyte.coverage import Coverage
from freezebyte.features import compute_features
from freezebyte.freeze import as_date, detect_freeze_windows
from freezebyte.reasons import classify
from freezebyte.structural import extract

ALL_BUCKETS = [f"r{r}v{v}" for r in (1, 2, 3) for v in (1, 2, 3)]
MIN_TRADING_ROWS = 21


def frozen_within_30d(symbol: str, as_of: date, suspensions: list[dict]) -> bool:
    """30 hari KALENDER sejak as_of, bukan 30 baris bursa."""
    deadline = as_date(as_of) + timedelta(days=30)
    for record in suspensions:
        if record["symbol"] != symbol:
            continue
        when = as_date(record["suspension_date"])
        if as_date(as_of) < when <= deadline:
            return True
    return False


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _write(name: str, payload) -> None:
    config.WEB_DIR.mkdir(parents=True, exist_ok=True)
    (config.WEB_DIR / name).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    print(f"  ditulis: data/web/{name}")


def build_alka(suspensions: list[dict]) -> dict:
    rows = _read(config.FIXTURE_DIR / "alka_daily.json")
    dates = [r["suspension_date"] for r in suspensions if r["symbol"] == "ALKA"]
    windows = detect_freeze_windows(rows, dates)
    return {
        "symbol": "ALKA",
        "rows": rows,
        "windows": [asdict(w) for w in windows],
        "suspension_records": [r for r in suspensions if r["symbol"] == "ALKA"],
    }


def build_events(manifest: dict, suspensions: list[dict], coverage: Coverage):
    """Kembalikan (events, serialised_events, serialised_controls).

    `events` menggabungkan kejadian dan kontrol karena base rate dihitung dari
    keduanya. Dua daftar serialised dipisah supaya halaman bisa membandingkan
    sebaran kenaikan harga kejadian terhadap kelompok kontrol.
    """
    events, serialised, controls_serialised = [], [], []

    for entry in manifest["events"]:
        symbol = entry["symbol"]
        rows = client.get_prices(symbol, entry["window"][0], entry["window"][1])
        if not rows:
            coverage.exclude(symbol, "harga tidak tersedia")
            continue

        ordered = sorted(rows, key=lambda r: as_date(r["date"]))
        trading = [r for r in ordered if r["volume"]]
        if len(trading) < MIN_TRADING_ROWS:
            coverage.exclude(symbol, "riwayat perdagangan terlalu pendek")
            continue

        # as_of adalah hari bursa terakhir SEBELUM saham dibekukan.
        suspension_date = as_date(entry["suspension_date"])
        before = [r for r in trading if as_date(r["date"]) < suspension_date]
        if not before:
            coverage.exclude(symbol, "tidak ada hari bursa sebelum suspensi")
            continue

        as_of = as_date(before[-1]["date"])
        structural = extract(client.get_overview(symbol))
        computed = compute_features(
            ordered, as_of, suspension_dates=[entry["suspension_date"]],
            structural=structural,
        )

        windows = detect_freeze_windows(ordered, [entry["suspension_date"]])
        confirmed = [w for w in windows if w.confirmed]
        reopen = confirmed[-1].reopen_return if confirmed else None

        events.append(
            Event(symbol=symbol, as_of=as_of, features=computed,
                  frozen_within_30d=True, reopen_return=reopen)
        )
        serialised.append({
            "symbol": symbol,
            "as_of": as_of.isoformat(),
            "suspension_date": entry["suspension_date"],
            "reason": entry.get("reason"),
            "reason_category": classify(entry.get("reason")),
            "pdf_url": entry.get("pdf_url"),
            "features": computed,
            "bucket": bucket(computed),
            "reopen_return": reopen,
            "windows": [asdict(w) for w in windows],
        })
        coverage.analyzed += 1

    for entry in manifest["controls"]:
        symbol = entry["symbol"]
        rows = client.get_prices(symbol, entry["window"][0], entry["window"][1])
        if not rows:
            coverage.exclude(symbol, "harga kontrol tidak tersedia")
            continue
        ordered = sorted(rows, key=lambda r: as_date(r["date"]))
        trading = [r for r in ordered if r["volume"]]
        if len(trading) < MIN_TRADING_ROWS:
            coverage.exclude(symbol, "riwayat kontrol terlalu pendek")
            continue

        as_of = as_date(trading[-1]["date"])
        computed = compute_features(ordered, as_of)
        events.append(
            Event(symbol=symbol, as_of=as_of, features=computed,
                  frozen_within_30d=frozen_within_30d(symbol, as_of, suspensions),
                  reopen_return=None)
        )
        controls_serialised.append({
            "symbol": symbol,
            "as_of": as_of.isoformat(),
            "features": computed,
            "bucket": bucket(computed),
        })

    return events, serialised, controls_serialised


def build_watchlist(suspensions: list[dict], coverage: Coverage) -> list[dict]:
    # Gerbang: file ini hanya ada setelah etl_overviews.py selesai berjalan.
    # Isinya sendiri tidak dipakai di sini -- kehadirannya saja yang dicek.
    vocabulary_path = config.RAW_DIR / "tag_vocabulary.json"
    if not vocabulary_path.exists():
        return []

    manifest = _read(config.RAW_DIR / "manifest_prices.json")
    seen = {e["symbol"] for e in manifest["events"]}
    rows = []

    for cache_file in sorted((config.RAW_DIR / "overview").glob("*.json")):
        symbol = cache_file.stem
        if symbol in seen:
            continue
        structural = extract(client.get_overview(symbol))
        if not structural["available"]:
            coverage.exclude(symbol, "overview tidak tersedia")
            continue

        end = date.today().isoformat()
        start = (date.today() - timedelta(days=89)).isoformat()
        prices = client.get_prices(symbol, start, end)
        if not prices:
            coverage.exclude(symbol, "harga kandidat tidak tersedia")
            continue

        ordered = sorted(prices, key=lambda r: as_date(r["date"]))
        trading = [r for r in ordered if r["volume"]]
        if len(trading) < MIN_TRADING_ROWS:
            coverage.exclude(symbol, "riwayat kandidat terlalu pendek")
            continue

        as_of = as_date(trading[-1]["date"])
        computed = compute_features(ordered, as_of, structural=structural)
        rows.append({
            "symbol": symbol,
            "as_of": as_of.isoformat(),
            "features": computed,
            "bucket": bucket(computed),
            "structural": structural,
        })

    rows.sort(key=lambda r: (r["features"]["ret_10d"] or -99), reverse=True)
    return rows


def main():
    suspensions = _read(config.RAW_DIR / "suspensions" / "all.json")
    manifest = _read(config.RAW_DIR / "manifest_prices.json")

    coverage = Coverage(total=len(suspensions))
    print("membangun output...")

    _write("alka.json", build_alka(suspensions))

    events, serialised, controls = build_events(manifest, suspensions, coverage)
    _write("events.json", serialised)

    # Sebaran ret_10d kejadian dibanding kontrol. Dipakai bagian 2 halaman.
    _write("distribution.json", {
        "events": [
            {"symbol": e["symbol"], "ret_10d": e["features"]["ret_10d"],
             "vol_ratio": e["features"]["vol_ratio"]}
            for e in serialised
        ],
        "controls": [
            {"symbol": c["symbol"], "ret_10d": c["features"]["ret_10d"],
             "vol_ratio": c["features"]["vol_ratio"]}
            for c in controls
        ],
        "control_definition": (
            "Emiten yang tidak pernah muncul di dataset suspensi, disampel acak "
            "dengan seed tetap, diukur pada hari bursa terakhir di window yang sama."
        ),
    })

    _write("baserates.json", {
        "min_sample": MIN_SAMPLE,
        "ret10_terciles": list(RET10_TERCILES),
        "vol_terciles": list(VOL_TERCILES),
        "buckets": [asdict(base_rate(events, b)) for b in ALL_BUCKETS],
    })

    _write("watchlist.json", build_watchlist(suspensions, coverage))

    reason_counts: dict[str, int] = {}
    for record in suspensions:
        label = classify(record.get("reason"))
        reason_counts[label] = reason_counts.get(label, 0) + 1

    _write("coverage.json", {
        **coverage.as_dict(),
        "reason_distribution": reason_counts,
        "sample_note": (
            "Sampel forensik dibatasi kejadian terbaru dari total record karena "
            "anggaran kredit API. Kelompok kontrol adalah emiten yang tidak pernah "
            "muncul di dataset suspensi, disampel acak dengan seed tetap."
        ),
    })

    _write("meta.json", {
        "built_at": datetime.now().isoformat(timespec="seconds"),
        "total_suspension_records": len(suspensions),
        "network_calls_this_build": len(client.NETWORK_CALLS),
    })

    print(f"\npanggilan jaringan selama build: {len(client.NETWORK_CALLS)}")


if __name__ == "__main__":
    main()
