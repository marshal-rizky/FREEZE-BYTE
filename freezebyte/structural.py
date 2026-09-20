"""Ekstraksi fitur struktural dari endpoint overview.

PERINGATAN: seluruh nilai di sini adalah KONDISI SEKARANG. Tidak ada cara
menanyakan tag apa yang dimiliki sebuah emiten pada tanggal lampau. Analisis
forensik memakai nilai sekarang sebagai perkiraan, dan itu dinyatakan di halaman.
"""

TAG_FLAGS = {
    "float_under_25": "public-float-under-25",
    "single_entity_70": "single-entity-holding-70",
    "insider_1m_sell": "insider-1-month-sell",
    "at_52w_high": "52-w-high",
}

EMPTY = {
    **{flag: False for flag in TAG_FLAGS},
    "tags": [],
    "market_cap": None,
    "listing_board": None,
    "available": False,
}


def extract(overview: dict | None) -> dict:
    if not overview:
        return dict(EMPTY)

    section = overview.get("overview", overview)
    tags = section.get("tags") or []

    result = {flag: tag in tags for flag, tag in TAG_FLAGS.items()}
    result["tags"] = list(tags)
    result["market_cap"] = section.get("market_cap")
    result["listing_board"] = section.get("listing_board")
    result["available"] = True
    return result
