"""Konstanta lingkungan. Satu-satunya tempat yang membaca .env."""
import os
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
