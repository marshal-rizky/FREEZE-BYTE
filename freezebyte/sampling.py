"""Pemilihan sampel kejadian dan kelompok kontrol. Fungsi murni dan deterministik."""
import random


def pick_events(records: list[dict], limit: int) -> list[dict]:
    """Kejadian suspensi terbaru, satu per emiten.

    Satu emiten bisa punya banyak record; hanya yang terbaru yang diambil supaya
    sampel tidak didominasi segelintir emiten yang sering disuspensi.
    """
    latest: dict[str, dict] = {}
    for record in records:
        symbol = record["symbol"]
        current = latest.get(symbol)
        if current is None or record["suspension_date"] > current["suspension_date"]:
            latest[symbol] = record

    ordered = sorted(latest.values(), key=lambda r: r["suspension_date"], reverse=True)
    return ordered[:limit]


def pick_controls(
    all_symbols: list[str],
    suspended_symbols: set[str],
    limit: int,
    seed: int = 20260920,
) -> list[str]:
    """Emiten yang tidak pernah muncul di dataset suspensi, disampel dengan seed tetap."""
    eligible = sorted(set(all_symbols) - set(suspended_symbols))
    rng = random.Random(seed)
    if len(eligible) <= limit:
        return eligible
    return sorted(rng.sample(eligible, limit))
