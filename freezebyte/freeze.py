"""Deteksi jendela beku dari deret harga. Fungsi murni, tidak tahu apa-apa soal API."""
from dataclasses import dataclass
from datetime import date, datetime
from typing import Iterable


@dataclass(frozen=True)
class FreezeWindow:
    start_date: date
    end_date: date
    n_days: int
    price_at_freeze: float
    reopen_close: float | None
    reopen_return: float | None
    confirmed: bool


def as_date(value) -> date:
    if isinstance(value, date):
        return value
    return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()


def detect_freeze_windows(
    rows: list[dict],
    suspension_dates: Iterable = (),
    min_days: int = 1,
) -> list[FreezeWindow]:
    """Deret berurutan maksimal dari baris dengan volume nol.

    Diukur berdasarkan urutan baris, bukan selisih kalender: baris yang tidak ada
    berarti hari non-bursa, bukan hari beku.

    volume == 0 pada saham sangat tidak likuid bisa berarti tidak ada transaksi,
    bukan suspensi. Karena itu setiap jendela di-cross-check terhadap tanggal
    suspensi resmi; `confirmed` False berarti jendela hanya tersimpulkan.
    """
    ordered = sorted(rows, key=lambda r: as_date(r["date"]))
    suspensions = {as_date(d) for d in suspension_dates}

    windows: list[FreezeWindow] = []
    i = 0
    while i < len(ordered):
        if ordered[i]["volume"] != 0:
            i += 1
            continue

        j = i
        while j + 1 < len(ordered) and ordered[j + 1]["volume"] == 0:
            j += 1

        block = ordered[i : j + 1]
        if len(block) >= min_days:
            start = as_date(block[0]["date"])
            end = as_date(block[-1]["date"])
            price_at_freeze = block[-1]["close"]
            after = ordered[j + 1] if j + 1 < len(ordered) else None

            reopen_close = after["close"] if after else None
            reopen_return = None
            if reopen_close is not None and price_at_freeze:
                reopen_return = reopen_close / price_at_freeze - 1

            windows.append(
                FreezeWindow(
                    start_date=start,
                    end_date=end,
                    n_days=len(block),
                    price_at_freeze=price_at_freeze,
                    reopen_close=reopen_close,
                    reopen_return=reopen_return,
                    confirmed=any(start <= d <= end for d in suspensions),
                )
            )
        i = j + 1

    return windows
