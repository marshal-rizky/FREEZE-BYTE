"""Kurva tenggang dan holdout temporal dari cache harga sampel forensik.

Nol kredit, dan dijamin begitu: setiap deret harga diperiksa ada di cache
SEBELUM dibaca. Kalau satu saja belum ada, script berhenti sebelum
memanggil jaringan -- jalankan scripts/etl_prices.py lebih dulu.

Menulis data/web/validation.json dan docs/validation/lead-time.md.
"""
import json
import sys

from freezebyte import client, config, scoring, validation


def cached_rows(symbol: str, window: list[str]) -> list[dict] | None:
    if not client.is_price_cached(symbol, window[0], window[1]):
        raise SystemExit(
            f"Cache harga {symbol} {window[0]}..{window[1]} tidak ada. "
            "Jalankan scripts/etl_prices.py lebih dulu. Tidak ada kredit terpakai."
        )
    return client.get_prices(symbol, window[0], window[1])


def main() -> None:
    # Konsol Windows memakai cp1252 dan tidak punya karakter seperti "≥";
    # tanpa ini print laporan gagal setelah berkasnya sudah ditulis.
    sys.stdout.reconfigure(encoding="utf-8")
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
