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
    """Ambil fitur struktural dari payload overview.

    `available` False berarti datanya tidak ada, BUKAN bahwa emitennya bersih.
    Payload yang bentuknya tidak dikenali — tidak punya kunci `tags` di mana pun
    yang kita cari — dihitung sebagai pengecualian, bukan diam-diam dianggap
    emiten tanpa tag satu pun. Bedanya menentukan: yang pertama berarti kita
    tidak tahu, yang kedua berarti kita tahu dan jawabannya nol. Menyamakan
    keduanya membuat emiten yang datanya rusak tampil sebagai emiten bersih.
    """
    if not overview:
        return dict(EMPTY)

    section = overview.get("overview")
    if not isinstance(section, dict):
        section = overview
    if "tags" not in section:
        return dict(EMPTY)

    tags = section.get("tags") or []

    result = {flag: tag in tags for flag, tag in TAG_FLAGS.items()}
    result["tags"] = list(tags)
    result["market_cap"] = section.get("market_cap")
    result["listing_board"] = section.get("listing_board")
    result["available"] = True
    return result
