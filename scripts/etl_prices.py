"""Tarik harga 90 hari untuk sampel kejadian suspensi dan kelompok kontrol.

Biaya: sekitar 125 kredit pada eksekusi pertama. Nol pada eksekusi ulang.
Window kontrol disamakan dengan kejadian pasangannya agar kondisi pasar sebanding.
"""
import json
from datetime import timedelta

from freezebyte import client, config
from freezebyte.freeze import as_date
from freezebyte.sampling import pick_controls, pick_events

N_EVENTS = 60
N_CONTROLS = 60
WINDOW_DAYS = 90
MAX_SCREENER_PAGES = 20  # 200 emiten per halaman; IDX punya sekitar 960


def load_suspensions() -> list[dict]:
    path = config.RAW_DIR / "suspensions" / "all.json"
    if not path.exists():
        raise SystemExit("Jalankan scripts/etl_suspensions.py lebih dulu.")
    return json.loads(path.read_text(encoding="utf-8"))


def all_listed_symbols() -> list[str]:
    """Daftar seluruh emiten lewat screener terstruktur.

    Dibatasi jumlah halaman dan menolak `next_offset` yang tidak maju. Loop
    paginasi tanpa batas di script berbayar adalah cara termahal untuk salah.
    """
    symbols, offset, pages = [], 0, 0
    while pages < MAX_SCREENER_PAGES:
        page = client.screen(where=None, limit=200, offset=offset)
        symbols.extend(r["symbol"] for r in page.get("results") or [])
        pages += 1

        pagination = page.get("pagination") or {}
        next_offset = pagination.get("next_offset")
        if not pagination.get("has_next") or next_offset is None:
            break
        if next_offset <= offset:
            raise SystemExit(
                f"Paginasi screener tidak maju: next_offset {next_offset} <= offset {offset}."
            )
        offset = next_offset
    else:
        print(
            f"PERINGATAN: berhenti di batas {MAX_SCREENER_PAGES} halaman screener. "
            "Daftar emiten TIDAK lengkap."
        )
    return symbols


def window_for(end_date) -> tuple[str, str]:
    end = as_date(end_date)
    start = end - timedelta(days=WINDOW_DAYS - 1)
    return start.isoformat(), end.isoformat()


def main():
    records = load_suspensions()
    events = pick_events(records, N_EVENTS)

    manifest = {"events": [], "controls": [], "failures": []}

    for event in events:
        start, end = window_for(event["suspension_date"])
        rows = client.get_prices(event["symbol"], start, end)
        if not rows:
            manifest["failures"].append(
                {"symbol": event["symbol"], "role": "event",
                 "reason": "harga tidak tersedia", "window": [start, end]}
            )
            continue
        manifest["events"].append(
            {"symbol": event["symbol"], "suspension_date": event["suspension_date"],
             "reason": event.get("reason"), "pdf_url": event.get("pdf_url"),
             "window": [start, end], "n_rows": len(rows)}
        )

    suspended = {r["symbol"] for r in records}
    controls = pick_controls(all_listed_symbols(), suspended, N_CONTROLS)

    if not events:
        raise SystemExit(
            "Tidak ada kejadian suspensi, jadi kontrol tidak punya window pembanding."
        )

    # Setiap kontrol dipasangkan ke satu kejadian dan memakai window kejadian itu.
    # Memakai satu window global untuk semua kontrol akan menghadapkan kontrol
    # milik suspensi Januari pada kondisi pasar September, dan perbandingannya
    # kehilangan artinya. Pasangannya dicatat di manifest supaya bisa diaudit.
    for i, symbol in enumerate(controls):
        paired = events[i % len(events)]
        start, end = window_for(paired["suspension_date"])
        rows = client.get_prices(symbol, start, end)
        if not rows:
            manifest["failures"].append(
                {"symbol": symbol, "role": "control",
                 "reason": "harga tidak tersedia", "window": [start, end],
                 "paired_event": paired["symbol"]}
            )
            continue
        manifest["controls"].append(
            {"symbol": symbol, "window": [start, end], "n_rows": len(rows),
             "paired_event": paired["symbol"],
             "paired_suspension_date": paired["suspension_date"]}
        )

    path = config.RAW_DIR / "manifest_prices.json"
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"kejadian berhasil : {len(manifest['events'])} dari {len(events)}")
    print(f"kontrol berhasil  : {len(manifest['controls'])} dari {len(controls)}")
    print(f"gagal             : {len(manifest['failures'])}")
    print(f"panggilan jaringan (kredit terpakai): {len(client.NETWORK_CALLS)}")

    for failure in manifest["failures"]:
        print("  gagal:", failure["symbol"], failure["role"], failure["reason"])


if __name__ == "__main__":
    main()
