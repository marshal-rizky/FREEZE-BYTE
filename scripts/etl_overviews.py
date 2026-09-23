"""Tarik overview untuk kejadian sampel, lalu petakan kosakata tag.

Biaya: 1 kredit per emiten karena hanya section overview yang diminta.
Memanggil tanpa parameter sections akan menarik 8 section dan menghabiskan 8 kredit.
Kandidat daftar pantau tidak lagi ditarik di sini; semesta ekstensi
(scripts/etl_universe.py) yang menggantikannya.
"""
import json
from collections import Counter

from freezebyte import client, config
from freezebyte.structural import extract


def sampled_symbols() -> list[str]:
    manifest = json.loads(
        (config.RAW_DIR / "manifest_prices.json").read_text(encoding="utf-8")
    )
    return [e["symbol"] for e in manifest["events"]]


def main():
    symbols = list(dict.fromkeys(sampled_symbols()))

    vocabulary = Counter()
    unavailable = []

    for symbol in symbols:
        data = extract(client.get_overview(symbol))
        if not data["available"]:
            unavailable.append(symbol)
            continue
        vocabulary.update(data["tags"])

    path = config.RAW_DIR / "tag_vocabulary.json"
    path.write_text(
        json.dumps(dict(vocabulary.most_common()), indent=2), encoding="utf-8"
    )

    print(f"emiten diproses: {len(symbols)}")
    print(f"overview tidak tersedia: {len(unavailable)} {unavailable}")
    print(f"panggilan jaringan (kredit terpakai): {len(client.NETWORK_CALLS)}")
    print(f"\nkosakata tag ({len(vocabulary)} tag unik):")
    for tag, count in vocabulary.most_common():
        print(f"  {tag:34} {count:4}")


if __name__ == "__main__":
    main()
