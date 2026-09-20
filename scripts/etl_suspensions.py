"""Tarik seluruh record suspensi lewat paginasi dan cetak distribusi alasannya.

Biaya: satu kredit per halaman, 30 record per halaman.
Aman dijalankan ulang: halaman yang sudah ada di cache tidak memanggil jaringan.
"""
import json
from collections import Counter

from freezebyte import client, config
from freezebyte.reasons import UNKNOWN, classify

PAGE_SIZE = 30
MAX_PAGES = 40  # pengaman terhadap loop paginasi yang tidak berhenti


def fetch_all() -> list[dict]:
    records, offset, pages = [], 0, 0

    while pages < MAX_PAGES:
        page = client.get_suspensions_page(limit=PAGE_SIZE, offset=offset)
        records.extend(page["results"])
        pages += 1

        pagination = page["pagination"]
        if not pagination.get("has_next"):
            break
        offset = pagination["next_offset"]

    return records


def main():
    records = fetch_all()

    combined = config.RAW_DIR / "suspensions" / "all.json"
    combined.parent.mkdir(parents=True, exist_ok=True)
    combined.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"total record: {len(records)}")
    print(f"panggilan jaringan (kredit terpakai): {len(client.NETWORK_CALLS)}")

    print("\ndistribusi alasan:")
    counts = Counter(classify(r.get("reason")) for r in records)
    for label, count in counts.most_common():
        print(f"  {label:26} {count:4}  {count / len(records):6.1%}")

    unclassified = [r for r in records if classify(r.get("reason")) == UNKNOWN]
    print(f"\ncontoh teks yang belum terklasifikasi ({len(unclassified)} record):")
    for record in unclassified[:15]:
        print("  -", (record.get("reason") or "")[:140])

    with_pdf = sum(1 for r in records if r.get("pdf_url"))
    print(f"\nrecord dengan pdf_url: {with_pdf} dari {len(records)}")

    symbols = Counter(r["symbol"] for r in records)
    print(f"emiten unik: {len(symbols)}")
    print("emiten paling sering disuspensi:", symbols.most_common(10))


if __name__ == "__main__":
    main()
