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
