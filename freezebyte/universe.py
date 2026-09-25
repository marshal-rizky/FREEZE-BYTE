"""Semesta ekstensi: fitur terbaru per emiten dan pilihan overview. Fungsi murni."""
from datetime import date

from freezebyte import scoring
from freezebyte.features import compute_features
from freezebyte.freeze import as_date

MIN_TRADING_ROWS = 21


def latest_features(prices: list[dict], suspension_dates=(),
                    structural: dict | None = None) -> tuple[date, dict] | None:
    """Fitur pada hari bursa terakhir, atau None kalau riwayatnya terlalu pendek."""
    if not prices:
        return None
    ordered = sorted(prices, key=lambda r: as_date(r["date"]))
    trading = [r for r in ordered if r["volume"]]
    if len(trading) < MIN_TRADING_ROWS:
        return None
    as_of = as_date(trading[-1]["date"])
    features = compute_features(ordered, as_of, suspension_dates=suspension_dates,
                                structural=structural)
    return as_of, features


def select_for_overview(rows: list[dict], limit: int) -> list[str]:
    """Overview hanya untuk simbol yang akan dilencanai.

    Flag struktural tampil di kartu TINGGI/SEDANG saja; menarik overview
    untuk simbol SENYAP adalah kredit yang tidak pernah terlihat siapa pun.
    """
    flagged = [r for r in rows if r["tier"] in (scoring.TINGGI, scoring.SEDANG)]
    flagged.sort(key=lambda r: r["features"]["ret_10d"], reverse=True)
    return [r["symbol"] for r in flagged[:limit]]
