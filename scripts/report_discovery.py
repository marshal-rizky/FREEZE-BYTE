"""Hitung batas tercile dari distribusi yang teramati.

Outputnya disalin sebagai konstanta ke freezebyte/baserates.py. Batas bucket
tidak dikarang di muka; dihitung setelah ETL selesai.
"""
import json
from datetime import date

from freezebyte import client, config
from freezebyte.baserates import terciles
from freezebyte.features import compute_features
from freezebyte.freeze import as_date


def price_rows(symbol: str, window: list[str]) -> list[dict] | None:
    return client.get_prices(symbol, window[0], window[1])


def main():
    manifest = json.loads(
        (config.RAW_DIR / "manifest_prices.json").read_text(encoding="utf-8")
    )

    ret10_values, vol_values, skipped = [], [], []

    for entry in manifest["events"] + manifest["controls"]:
        rows = price_rows(entry["symbol"], entry["window"])
        if not rows:
            skipped.append((entry["symbol"], "tidak ada baris"))
            continue

        ordered = sorted(rows, key=lambda r: as_date(r["date"]))
        trading = [r for r in ordered if r["volume"]]
        if len(trading) < 21:
            skipped.append((entry["symbol"], f"hanya {len(trading)} baris berdagang"))
            continue

        # as_of harus meniru build_events di freezebyte/build.py persis: untuk
        # kejadian (punya suspension_date), as_of adalah hari bursa terakhir
        # SEBELUM suspensi -- bukan baris terakhir di window, yang sekarang
        # jatuh SESUDAH suspensi karena window melewati tanggal itu. Memakai
        # baris terakhir di sini akan mengalibrasi tercile pada harga
        # pasca-beku, persis kegagalan "batas bucket dikarang" yang dilarang
        # spec. Kontrol (tidak punya suspension_date) tetap memakai baris
        # terakhir seperti sebelumnya.
        suspension_date = entry.get("suspension_date")
        if suspension_date is not None:
            before = [r for r in trading if as_date(r["date"]) < as_date(suspension_date)]
            if not before:
                skipped.append((entry["symbol"], "tidak ada hari bursa sebelum suspensi"))
                continue
            as_of = as_date(before[-1]["date"])
        else:
            as_of = as_date(trading[-1]["date"])

        computed = compute_features(ordered, as_of)
        if computed["ret_10d"] is not None:
            ret10_values.append(computed["ret_10d"])
        if computed["vol_ratio"] is not None:
            vol_values.append(computed["vol_ratio"])

    print(f"ret_10d  n={len(ret10_values)}  terciles={terciles(ret10_values)}")
    print(f"vol_ratio n={len(vol_values)}  terciles={terciles(vol_values)}")
    print(f"\ndilewati: {len(skipped)}")
    for symbol, reason in skipped:
        print("  ", symbol, reason)
    print(f"\npanggilan jaringan: {len(client.NETWORK_CALLS)}")


if __name__ == "__main__":
    main()
