"""Satu-satunya modul yang menyentuh jaringan.

Aturan keras: setiap respons ditulis ke disk sebelum dikembalikan ke pemanggil,
dan endpoint yang sama tidak pernah dipanggil dua kali.
"""
import json
import time
from pathlib import Path
from typing import Any

import requests

from freezebyte import config

TIMEOUT = 30
NETWORK_CALLS: list[str] = []


def _cache_path(cache_key: str) -> Path:
    return config.RAW_DIR / f"{cache_key}.json"


def get_json(path: str, params: dict, cache_key: str) -> Any:
    """Kembalikan payload endpoint. None kalau endpoint mengembalikan 404.

    404 dicatat ke cache sebagai `unavailable` supaya emiten yang datanya memang
    tidak ada tidak ditarik berulang kali dan tetap masuk hitungan coverage.
    """
    cached = _cache_path(cache_key)
    if cached.exists():
        envelope = json.loads(cached.read_text(encoding="utf-8"))
        if envelope.get("unavailable"):
            return None
        return envelope["payload"]

    response = requests.get(
        config.BASE_URL + path,
        headers={"Authorization": config.api_key()},
        params=params,
        timeout=TIMEOUT,
    )
    NETWORK_CALLS.append(path)

    cached.parent.mkdir(parents=True, exist_ok=True)

    if response.status_code == 404:
        cached.write_text(
            json.dumps({"endpoint": path, "params": params, "unavailable": 404}),
            encoding="utf-8",
        )
        return None

    if response.status_code == 429:
        time.sleep(5)
        return get_json(path, params, cache_key)

    response.raise_for_status()
    payload = response.json()
    cached.write_text(
        json.dumps(
            {"endpoint": path, "params": params, "payload": payload},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return payload


def get_suspensions_page(limit: int = 30, offset: int = 0) -> dict:
    return get_json(
        "/suspensions/",
        {"limit": limit, "offset": offset},
        f"suspensions/offset_{offset}_limit_{limit}",
    )


def get_prices(symbol: str, start: str, end: str) -> list[dict] | None:
    symbol = symbol.upper()
    return get_json(
        f"/daily/{symbol}/",
        {"start": start, "end": end},
        f"daily/{symbol}_{start}_{end}",
    )


def get_overview(symbol: str) -> dict | None:
    symbol = symbol.upper()
    return get_json(
        f"/company/report/{symbol}/",
        {"sections": "overview"},
        f"overview/{symbol}",
    )


def screen(where: str | None, limit: int = 200, offset: int = 0) -> dict:
    """Screener terstruktur. Parameter `q` sengaja tidak didukung: 3 kredit versus 1."""
    params = {"limit": limit, "offset": offset}
    slug = "all"
    if where:
        params["where"] = where
        slug = "".join(c if c.isalnum() else "_" for c in where)[:80]
    return get_json("/companies/", params, f"companies/{slug}_offset_{offset}")
