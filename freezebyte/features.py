"""Mesin fitur. Fungsi murni tanpa I/O.

Inti proyek: forensik memanggil compute_features dengan as_of sehari sebelum
suspensi, pantau-hari-ini memanggilnya dengan as_of hari bursa terakhir.
Kode yang sama.
"""
from datetime import date

from freezebyte.freeze import as_date, detect_freeze_windows


def _ordered(rows: list[dict]) -> list[dict]:
    return sorted(rows, key=lambda r: as_date(r["date"]))


def _index_of(ordered: list[dict], as_of: date) -> int:
    target = as_date(as_of)
    for i, row in enumerate(ordered):
        if as_date(row["date"]) == target:
            return i
    raise ValueError(f"as_of {target} tidak ada di deret harga")


def ret_n(rows: list[dict], as_of: date, n: int) -> float | None:
    """Return selama n baris bursa ke belakang, bukan n hari kalender."""
    ordered = _ordered(rows)
    i = _index_of(ordered, as_of)
    if i - n < 0:
        return None
    previous = ordered[i - n]["close"]
    if not previous:
        return None
    return ordered[i]["close"] / previous - 1


def vol_ratio(rows: list[dict], as_of: date, window: int = 20) -> float | None:
    """Volume hari ini dibagi rata-rata volume window baris sebelumnya.

    Baris ber-volume nol dikeluarkan dari rata-rata: hari beku bukan hari sepi.
    """
    ordered = _ordered(rows)
    i = _index_of(ordered, as_of)
    prior = [r["volume"] for r in ordered[max(0, i - window) : i] if r["volume"]]
    if not prior:
        return None
    return ordered[i]["volume"] / (sum(prior) / len(prior))


def dist_from_high(rows: list[dict], as_of: date, window: int = 90) -> float | None:
    """Rasio close terhadap high tertinggi window baris terakhir. 1,0 = di puncak.

    Baris dengan high nol atau null dibuang: nilai itu muncul di data nyata
    (ALKA 2026-09-18) dan akan merusak hasilnya kalau ikut dihitung.
    """
    ordered = _ordered(rows)
    i = _index_of(ordered, as_of)
    highs = [r.get("high") for r in ordered[max(0, i - window + 1) : i + 1]]
    usable = [h for h in highs if h]
    if not usable:
        return None
    return ordered[i]["close"] / max(usable)


def consecutive_up_days(rows: list[dict], as_of: date) -> int:
    ordered = _ordered(rows)
    i = _index_of(ordered, as_of)
    count = 0
    while i > 0 and ordered[i]["close"] > ordered[i - 1]["close"]:
        count += 1
        i -= 1
    return count


def compute_features(
    rows: list[dict],
    as_of: date,
    suspension_dates=(),
    structural: dict | None = None,
) -> dict:
    """Satu dict fitur untuk satu emiten pada satu tanggal.

    `structural` berisi kondisi dari endpoint overview dan bersifat KONDISI
    SEKARANG, bukan historis. Tidak ada cara menanyakan tag apa yang dimiliki
    sebuah emiten pada tanggal lampau. UI wajib menandainya.

    `prior_freeze_count` hanya menghitung jendela `confirmed`. Deret volume nol
    tanpa record suspensi resmi bisa berarti saham itu cuma tidak ditransaksikan
    hari itu — ALKA punya dua deret seperti itu di fixture. Menghitungnya akan
    menggelembungkan fitur ini dan melanggar aturan bahwa angka forensik hanya
    berasal dari jendela confirmed. Konsekuensinya: tanpa `suspension_dates`,
    nilainya selalu 0. Itu disengaja.
    """
    ordered = _ordered(rows)
    target = as_date(as_of)
    _index_of(ordered, target)

    prior_windows = [
        w
        for w in detect_freeze_windows(ordered, suspension_dates)
        if w.confirmed and w.end_date < target
    ]

    return {
        "ret_5d": ret_n(ordered, target, 5),
        "ret_10d": ret_n(ordered, target, 10),
        "ret_20d": ret_n(ordered, target, 20),
        "vol_ratio": vol_ratio(ordered, target),
        "dist_from_high": dist_from_high(ordered, target),
        "prior_freeze_count": len(prior_windows),
        "consecutive_up_days": consecutive_up_days(ordered, target),
        "structural": structural or {},
    }
