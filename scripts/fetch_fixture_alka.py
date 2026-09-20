"""Tarik satu window harga ALKA dan simpan sebagai fixture test yang di-commit.

Biaya: 1 kredit. Window 90 hari supaya cukup untuk dist_from_high.
"""
import json

from freezebyte import client, config

START = "2026-06-22"
END = "2026-09-19"


def main():
    rows = client.get_prices("ALKA", START, END)
    if not rows:
        raise SystemExit("ALKA mengembalikan data kosong — periksa API key dan tanggal.")

    config.FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    out = config.FIXTURE_DIR / "alka_daily.json"
    out.write_text(json.dumps(rows, indent=2), encoding="utf-8")

    print(f"{len(rows)} baris tersimpan ke {out}")
    print(f"panggilan jaringan: {len(client.NETWORK_CALLS)}")
    print("\nbaris ber-volume nol:")
    for row in rows:
        if row["volume"] == 0:
            print(" ", row["date"], row["close"])
    print("\nbaris dengan high kosong atau nol:")
    for row in rows:
        if not row.get("high"):
            print(" ", row["date"], "high =", row.get("high"))


if __name__ == "__main__":
    main()
