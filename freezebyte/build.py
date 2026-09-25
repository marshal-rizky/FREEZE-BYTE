"""Orkestrasi: baca cache, jalankan mesin, tulis data/web/*.json.

Tidak memanggil jaringan untuk data yang sudah ada di cache. Window harga
daftar pantau (lihat `_watchlist_window`) dipinkan ke
`data/raw/watchlist_window.json` supaya build ulang di hari kalender lain
tetap memakai window lama dan cache lama -- tanpa itu, setiap build di hari
baru diam-diam menghasilkan cache key baru dan menghabiskan puluhan kredit
API lagi. Set `FREEZEBYTE_REFRESH_WATCHLIST=1` untuk sengaja menggeser
window itu maju (akan memanggil jaringan dan memakan kredit baru).
"""
import json
import os
from collections import Counter
from dataclasses import asdict
from datetime import date, datetime, timedelta

from freezebyte import baserates, client, config, scoring, universe
from freezebyte.coverage import Coverage
from freezebyte.features import compute_features, ret_n
from freezebyte.freeze import as_date, detect_freeze_windows
from freezebyte.reasons import classify
from freezebyte.structural import EMPTY, extract

ALL_BUCKETS = [f"r{r}v{v}" for r in (1, 2, 3) for v in (1, 2, 3)]
MIN_TRADING_ROWS = 21

# Titik acuan rally pra-beku ALKA: titik terendah lokal pasca-reopen
# sebelumnya, 2026-09-07 (close Rp3.750), enam baris bursa sebelum hari bursa
# terakhir sebelum jendela beku terakhir, 2026-09-15 (close Rp7.400) --
# return 0,9733. build_alka adalah studi kasus satu emiten di atas satu
# fixture yang sudah dikomit dan tidak akan berubah lagi, jadi ini konstanta
# yang sengaja dipatok tangan (bukan rumus umum yang mencari titik rendah).
PRE_FREEZE_RALLY_ROWS = 6

PLACEHOLDER_TERCILES = (0.0, 0.0)
TERCILE_OVERRIDE_ENV = "FREEZEBYTE_ALLOW_PLACEHOLDER_TERCILES"
REFRESH_WATCHLIST_ENV = "FREEZEBYTE_REFRESH_WATCHLIST"


def _base(symbol) -> str:
    """Bandingkan simbol tanpa sufiks bursa: endpoint daily mengembalikan
    'ALKA.JK' sementara endpoint lain memakai 'ALKA'."""
    return str(symbol).split(".")[0].upper()


def frozen_within_30d(symbol: str, as_of: date, suspensions: list[dict]) -> bool:
    """30 hari KALENDER sejak as_of, bukan 30 baris bursa.

    CATATAN (lihat temuan C2 review akhir): di bawah definisi `pick_controls`
    saat ini, kelompok kontrol adalah PERSIS emiten yang tidak pernah muncul
    di dataset suspensi -- jadi fungsi ini secara struktural selalu
    mengembalikan False untuk setiap kontrol yang dipanggilkan padanya di
    `build_events`. Fungsi dan lima test-nya tetap dipertahankan untuk
    definisi kontrol di masa depan yang mungkin menyertakan emiten yang
    pernah disuspensi (mis. kontrol dari emiten yang disuspensi lebih dari
    setahun lalu, di luar window kejadian). Jangan membaca True/False dari
    fungsi ini sebagai perilaku yang benar-benar teramati pada build saat ini.
    """
    deadline = as_date(as_of) + timedelta(days=30)
    for record in suspensions:
        if _base(record["symbol"]) != _base(symbol):
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


def _watchlist_window() -> tuple[str, str]:
    """Pin window harga 90 hari milik semesta ekstensi ke cache.

    Tanpa ini, window baru dibuat setiap hari kalender yang berbeda dan build
    pertama di hari itu memanggil jaringan lagi walau tidak ada yang
    benar-benar berubah. Sekali dipinkan, build berikutnya membaca window yang
    sama dari cache dan tidak memanggil jaringan sama sekali.
    `FREEZEBYTE_REFRESH_WATCHLIST=1` menggeser window itu maju dengan sengaja.
    """
    window_path = config.RAW_DIR / "watchlist_window.json"
    if window_path.exists() and not os.environ.get(REFRESH_WATCHLIST_ENV):
        cached = _read(window_path)
        return cached["start"], cached["end"]

    end_day = config.last_complete_day()
    end = end_day.isoformat()
    start = (end_day - timedelta(days=89)).isoformat()
    window_path.parent.mkdir(parents=True, exist_ok=True)
    window_path.write_text(
        json.dumps({"start": start, "end": end}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return start, end


def _check_terciles_ready() -> None:
    """Gagal keras kalau tercile base rate masih placeholder (0.0, 0.0).

    Dengan placeholder itu, setiap input non-negatif jatuh ke r3/v3 dan
    kesembilan bucket kolaps jadi satu -- lalu build.py akan tetap
    men-serialisasi angka itu ke data/web/baserates.json yang dikomit dan
    ditampilkan ke juri seolah valid. Dicek di awal main(), sebelum build
    menghabiskan kredit API pada langkah-langkah yang toh akan sia-sia.
    """
    placeholder = (
        tuple(baserates.RET10_TERCILES) == PLACEHOLDER_TERCILES
        or tuple(baserates.VOL_TERCILES) == PLACEHOLDER_TERCILES
    )
    if not placeholder:
        return
    if os.environ.get(TERCILE_OVERRIDE_ENV):
        return
    raise SystemExit(
        "RET10_TERCILES/VOL_TERCILES di freezebyte/baserates.py masih "
        "placeholder (0.0, 0.0). Jalankan scripts/report_discovery.py, isi "
        "kedua konstanta itu dengan tercile dari distribusi yang benar-benar "
        "teramati, lalu build ulang. Set "
        f"{TERCILE_OVERRIDE_ENV}=1 untuk memaksa menulis baserates.json apa "
        "adanya (TIDAK disarankan -- seluruh bucket akan kolaps ke r3/v3)."
    )


def build_alka(suspensions: list[dict]) -> dict:
    rows = _read(config.FIXTURE_DIR / "alka_daily.json")
    dates = [r["suspension_date"] for r in suspensions if _base(r["symbol"]) == "ALKA"]
    windows = detect_freeze_windows(rows, dates)
    confirmed = [w for w in windows if w.confirmed]

    # +97,3% pra-beku: lihat PRE_FREEZE_RALLY_ROWS di atas. Hanya dihitung
    # kalau ada jendela confirmed -- tanpa suspension_dates yang benar,
    # seluruh jendela ALKA cuma inferred dan angka ini sengaja ditinggal None
    # daripada mengarang titik acuan.
    rally_return = None
    if confirmed:
        ordered = sorted(rows, key=lambda r: as_date(r["date"]))
        trading = [r for r in ordered if r["volume"]]
        final_start = confirmed[-1].start_date
        before = [r for r in trading if as_date(r["date"]) < final_start]
        if before:
            rally_as_of = as_date(before[-1]["date"])
            rally_return = ret_n(rows, rally_as_of, PRE_FREEZE_RALLY_ROWS)

    return {
        "symbol": "ALKA",
        "rows": rows,
        "windows": [asdict(w) for w in windows],
        "suspension_records": [r for r in suspensions if _base(r["symbol"]) == "ALKA"],
        "pre_freeze_rally_return": rally_return,
        "pre_freeze_rally_rows": PRE_FREEZE_RALLY_ROWS,
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

        # C1: seluruh tanggal suspensi resmi emiten ini, bukan cuma kejadian
        # yang membawanya ke sampel. Memakai satu tanggal saja membuat
        # suspensi lain milik emiten yang sama di dalam window yang sama
        # salah ditandai `inferred`, yang menggugurkannya dari
        # prior_freeze_count dan dari daftar confirmed yang menghasilkan
        # `reopen`.
        symbol_dates = [
            r["suspension_date"] for r in suspensions if _base(r["symbol"]) == _base(symbol)
        ]

        computed = compute_features(
            ordered, as_of, suspension_dates=symbol_dates,
            structural=structural,
        )

        windows = detect_freeze_windows(ordered, symbol_dates)
        confirmed = [w for w in windows if w.confirmed]
        reopen = confirmed[-1].reopen_return if confirmed else None

        events.append(
            baserates.Event(symbol=symbol, as_of=as_of, features=computed,
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
            "bucket": baserates.bucket(computed),
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
            baserates.Event(symbol=symbol, as_of=as_of, features=computed,
                             frozen_within_30d=frozen_within_30d(symbol, as_of, suspensions),
                             reopen_return=None)
        )
        controls_serialised.append({
            "symbol": symbol,
            "as_of": as_of.isoformat(),
            "features": computed,
            "bucket": baserates.bucket(computed),
        })
        # I1: kontrol yang berhasil diproses sekarang juga dihitung sebagai
        # analyzed -- sebelumnya kontrol yang lolos tidak masuk `analyzed`
        # maupun `excluded`, jadi analyzed + excluded != total.
        coverage.analyzed += 1

    return events, serialised, controls_serialised


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


def main():
    # Setiap prasyarat diperiksa lebih dulu dan dilaporkan sebagai satu
    # pesan, bukan dibiarkan meledak jadi stack trace di pembacaan pertama.
    # Urutan ETL-nya juga ikut tercetak, karena "berkas tidak ada" tidak
    # memberi tahu script mana yang harus dijalankan.
    required = [
        (config.RAW_DIR / "suspensions" / "all.json", "scripts/etl_suspensions.py"),
        (config.RAW_DIR / "manifest_prices.json", "scripts/etl_prices.py"),
        (config.RAW_DIR / "tag_vocabulary.json", "scripts/etl_overviews.py"),
        (config.RAW_DIR / "manifest_universe.json", "scripts/etl_universe.py"),
    ]
    missing = [(p, s) for p, s in required if not p.exists()]
    if missing:
        lines = [f"  {p.relative_to(config.RAW_DIR.parent.parent)} -> jalankan {s}"
                 for p, s in missing]
        raise SystemExit(
            "Cache mentah belum lengkap, build dihentikan sebelum menulis apa pun.\n"
            + "\n".join(lines)
            + "\n\ndata/web/*.json yang sudah ada TIDAK diubah."
        )

    suspensions = _read(config.RAW_DIR / "suspensions" / "all.json")
    manifest = _read(config.RAW_DIR / "manifest_prices.json")

    # I3: gerbang kredit diangkat ke sini dari build_watchlist supaya
    # build_events -- yang juga memanggil client.get_overview per kejadian,
    # tanpa gerbang sebelumnya -- tidak diam-diam menghabiskan ~60 kredit
    # sebelum etl_overviews.py pernah dijalankan.
    vocabulary_path = config.RAW_DIR / "tag_vocabulary.json"
    if not vocabulary_path.exists():
        raise SystemExit("Jalankan scripts/etl_overviews.py lebih dulu.")

    _check_terciles_ready()

    # I1: total sampel forensik yang BENAR-BENAR dianalisis (~120), bukan
    # seluruh record suspensi (~592). watchlist_coverage memakai counter
    # terpisah karena kandidat daftar pantau bukan record suspensi dan tidak
    # boleh dicampur ke penyebut yang sama.
    sample_size = len(manifest["events"]) + len(manifest["controls"])
    coverage = Coverage(total=sample_size)
    watchlist_coverage = Coverage(total=0)
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

    # C2: n_events/n_controls (dan pecahannya per bucket) dipakai halaman
    # untuk menjelaskan bahwa n_frozen_within_30d/n adalah pecahan arm
    # kejadian dalam sampel case-control 1:1 -- bukan frekuensi populasi.
    event_bucket_counts = Counter(e["bucket"] for e in serialised)
    control_bucket_counts = Counter(c["bucket"] for c in controls)
    buckets_payload = []
    for b in ALL_BUCKETS:
        rate = asdict(baserates.base_rate(events, b))
        rate["n_events"] = event_bucket_counts.get(b, 0)
        rate["n_controls"] = control_bucket_counts.get(b, 0)
        buckets_payload.append(rate)

    _write("baserates.json", {
        "min_sample": baserates.MIN_SAMPLE,
        "ret10_terciles": list(baserates.RET10_TERCILES),
        "vol_terciles": list(baserates.VOL_TERCILES),
        "n_events": len(serialised),
        "n_controls": len(controls),
        "buckets": buckets_payload,
    })

    _write("watchlist.json", build_watchlist(suspensions, watchlist_coverage))

    reason_counts: dict[str, int] = {}
    for record in suspensions:
        label = classify(record.get("reason"))
        reason_counts[label] = reason_counts.get(label, 0) + 1

    _write("coverage.json", {
        **coverage.as_dict(),
        "total_suspension_records": len(suspensions),
        "sample_events": len(manifest["events"]),
        "sample_controls": len(manifest["controls"]),
        "watchlist": watchlist_coverage.as_dict(),
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
