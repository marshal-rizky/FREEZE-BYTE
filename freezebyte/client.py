"""Satu-satunya modul yang menyentuh jaringan.

Aturan keras: setiap respons ditulis ke disk sebelum dikembalikan ke pemanggil,
dan data yang sudah ada di cache tidak pernah ditarik ulang. Satu-satunya
pengecualian adalah percobaan ulang saat kena 429 atau saat koneksi transport
gagal (ConnectionError/Timeout tanpa respons sama sekali), dan itu pun dibatasi.
"""
import hashlib
import json
import time
from pathlib import Path
from typing import Any

import requests

from freezebyte import config

TIMEOUT = 30

# Backoff dinaikkan setelah ETL harga 2026-09-21 kena 429 pada panggilan ke-50.
# Backoff lama (5, 10, 15 detik) total hanya 30 detik, terlalu pendek untuk
# melewati kuota per menit. Sekarang 20, 40, 60, 80, 100 detik, jadi satu
# jendela kuota pasti terlewati sebelum script menyerah. Menyerah tetap lebih
# baik daripada terus memanggil: kredit tidak bisa dikembalikan.
MAX_RETRIES = 5
RETRY_SLEEP = 20
NETWORK_CALLS: list[str] = []


def _cache_path(cache_key: str) -> Path:
    return config.RAW_DIR / f"{cache_key}.json"


def _params_digest(params: dict) -> str:
    """Sidik jari pendek dari seluruh parameter.

    Dipakai untuk endpoint yang parameternya bebas bentuk. Menyusun cache key
    dari potongan parameter yang dipilih tangan pernah membuat dua query berbeda
    menulis ke file yang sama; digest menutup itu.
    """
    blob = json.dumps(params, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


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

    for attempt in range(MAX_RETRIES + 1):
        try:
            response = requests.get(
                config.BASE_URL + path,
                headers={"Authorization": config.api_key()},
                params=params,
                timeout=TIMEOUT,
            )
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as exc:
            # Permintaan sudah benar-benar terkirim (dan mungkin sudah kena
            # tagihan) walau tidak ada respons yang kembali, jadi tetap
            # dihitung di NETWORK_CALLS. Tidak ada respons berarti tidak ada
            # 404 asli untuk dicek, jadi ini TIDAK ditulis ke cache sebagai
            # unavailable -- itu dicadangkan untuk 404 sungguhan.
            NETWORK_CALLS.append(path)
            if attempt == MAX_RETRIES:
                raise RuntimeError(
                    f"Gagal terhubung setelah {MAX_RETRIES} percobaan ulang untuk {path}: "
                    f"{exc}. Berhenti daripada terus mencoba tanpa batas."
                ) from exc
            time.sleep(RETRY_SLEEP * (attempt + 1))
            continue

        NETWORK_CALLS.append(path)

        if response.status_code != 429:
            break

        if attempt == MAX_RETRIES:
            raise RuntimeError(
                f"Masih kena 429 setelah {MAX_RETRIES} percobaan ulang untuk {path}. "
                "Berhenti daripada terus memakan kredit tanpa batas."
            )
        time.sleep(RETRY_SLEEP * (attempt + 1))

    cached.parent.mkdir(parents=True, exist_ok=True)

    if response.status_code == 404:
        cached.write_text(
            json.dumps(
                {"endpoint": path, "params": params, "unavailable": 404},
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return None

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


def price_cache_key(symbol: str, start: str, end: str) -> str:
    return f"daily/{symbol.upper()}_{start}_{end}"


def is_price_cached(symbol: str, start: str, end: str) -> bool:
    """Dipakai script yang dilarang memakan kredit untuk memeriksa lebih dulu."""
    return _cache_path(price_cache_key(symbol, start, end)).exists()


def get_prices(symbol: str, start: str, end: str) -> list[dict] | None:
    symbol = symbol.upper()
    return get_json(
        f"/daily/{symbol}/",
        {"start": start, "end": end},
        price_cache_key(symbol, start, end),
    )


def get_overview(symbol: str) -> dict | None:
    symbol = symbol.upper()
    return get_json(
        f"/company/report/{symbol}/",
        {"sections": "overview"},
        f"overview/{symbol}",
    )


def screen(where: str | None, limit: int = 200, offset: int = 0) -> dict:
    """Screener terstruktur. Parameter `q` sengaja tidak didukung: 3 kredit versus 1.

    Cache key memakai digest seluruh parameter, bukan potongan `where` saja.
    Dua query yang berbeda hanya pada `limit` — atau yang berbeda hanya pada
    tanda baca di dalam `where` — akan menulis ke file yang sama kalau digest
    tidak dipakai, dan pemanggil kedua diam-diam menerima hasil pemanggil pertama.
    """
    params = {"limit": limit, "offset": offset}
    slug = "all"
    if where:
        params["where"] = where
        slug = "".join(c if c.isalnum() else "_" for c in where)[:40]
    return get_json("/companies/", params, f"companies/{slug}_{_params_digest(params)}")
