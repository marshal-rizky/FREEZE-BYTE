"""Konstanta lingkungan. Satu-satunya tempat yang membaca .env."""
import os
from datetime import date, timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_URL = "https://api.sectors.app/v2"

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
WEB_DIR = ROOT / "data" / "web"
FIXTURE_DIR = ROOT / "tests" / "fixtures"

_loaded = False


def _load_dotenv_once():
    global _loaded
    if not _loaded:
        load_dotenv(ROOT / ".env")
        _loaded = True


def api_key() -> str:
    _load_dotenv_once()
    key = os.environ.get("SECTORS_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "SECTORS_API_KEY tidak ditemukan. Salin .env.example jadi .env "
            "lalu isi dengan key dari portal hackathon Sectors."
        )
    return key


def last_complete_day() -> date:
    """Hari kalender terakhir yang aman diminta ke API: kemarin.

    date.today() memakai jam lokal (WIB, UTC+7). Antara pukul 00.00 dan 07.00
    WIB server Sectors (UTC) masih di tanggal sebelumnya, sehingga "hari ini"
    adalah tanggal masa depan baginya dan permintaan ditolak 400. Bar hari ini
    juga belum lengkap sebelum bursa tutup.
    """
    return date.today() - timedelta(days=1)
