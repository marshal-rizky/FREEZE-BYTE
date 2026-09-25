"""Semesta ekstensi: screener emiten berisiko, harga 90 hari, overview bertanda.

Dua tahap, supaya biaya diketahui sebelum dibelanjakan:

    python scripts/etl_universe.py --count   # 1 kredit: cetak total_count
    python scripts/etl_universe.py --run     # screener + harga + overview

Biaya --run: 1 kredit halaman screener + <= UNIVERSE_LIMIT kredit harga +
<= MAX_OVERVIEWS kredit overview. Nol pada eksekusi ulang: semuanya dari cache.

Screener API mengurutkan hasil berdasarkan simbol secara standar, sehingga tanpa
filter rally dan pengurutan -market_cap, potongan 150 pertama hanya akan berisi
simbol A hingga F. Tag mencerminkan keadaan pasar saat build, jadi semesta adalah
snapshot pada waktu pembangunan.
"""
import json
import sys

from freezebyte import build, client, config, scoring, universe
from freezebyte.build import _base

UNIVERSE_WHERE = "tags in ['public-float-under-25'] and tags in ['90-d-high', '52-w-high', 'ytd-high', 'top-ten-1m-leaders']"
UNIVERSE_ORDER = "-market_cap"
UNIVERSE_LIMIT = 150
MAX_OVERVIEWS = 50


def count() -> None:
    page = client.screen(where=UNIVERSE_WHERE, limit=1, offset=0, order_by=UNIVERSE_ORDER)
    total = page["pagination"]["total_count"]
    take = min(total, UNIVERSE_LIMIT)
    print(f"total_count screener : {total}")
    print(f"akan diambil         : {take}")
    print(f"perkiraan biaya --run: <= {1 + take + MAX_OVERVIEWS} kredit")


def run() -> None:
    suspensions = json.loads(
        (config.RAW_DIR / "suspensions" / "all.json").read_text(encoding="utf-8")
    )
    page = client.screen(where=UNIVERSE_WHERE, limit=UNIVERSE_LIMIT, offset=0, order_by=UNIVERSE_ORDER)
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
