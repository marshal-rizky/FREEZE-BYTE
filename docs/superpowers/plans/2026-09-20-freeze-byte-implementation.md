# FREEZE BYTE — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Membangun situs statis yang menganalisis suspensi perdagangan IDX — anatomi forensik pembekuan yang tercatat dan daftar pantau emiten hari ini — dari satu mesin fitur yang sama.

**Architecture:** Pipeline satu arah tanpa loop. `client.py` satu-satunya modul yang menyentuh jaringan dan selalu menulis cache ke disk sebelum data diolah. `freeze.py`, `features.py`, dan `baserates.py` adalah fungsi murni tanpa I/O sehingga bisa dites offline. `build.py` membaca cache, menjalankan mesin, dan menulis `data/web/*.json` yang di-commit. Situs statis di `site/` hanya membaca JSON tersebut, jadi juri bisa clone dan membuka tanpa API key dan tanpa mengeluarkan kredit.

**Tech Stack:** Python 3.11, `requests`, `python-dotenv`, `pytest`. Frontend HTML/CSS/JavaScript vanilla tanpa dependensi eksternal dan tanpa CDN; grafik digambar sebagai SVG buatan sendiri. Tanpa LLM.

**Dokumen acuan:** `docs/superpowers/specs/2026-09-20-freeze-byte-design.md`. Spec adalah otoritas untuk keputusan desain; plan ini adalah urutan eksekusinya.

---

## Global Constraints

Setiap task secara implisit mewarisi seluruh butir di bawah ini.

**API**

- Base URL adalah `https://api.sectors.app/v2`. **v1 sudah dihentikan dan mengembalikan HTTP 410 Gone sejak 2026-05-11.** Jangan pernah menulis `/v1/` di kode mana pun.
- Header autentikasi: `Authorization: <raw key>`. **Tanpa prefiks `Bearer`.**
- API key dibaca dari environment variable `SECTORS_API_KEY` lewat file `.env` yang tidak pernah di-commit.
- Dilarang memakai parameter `q=` (natural language) pada endpoint screener — biayanya 3 kredit versus 1 kredit untuk query terstruktur.
- Setiap respons HTTP 2xx **wajib ditulis ke `data/raw/` sebelum diolah**. Tidak ada pemanggilan jaringan untuk data yang sudah ada di cache.
- Anggaran kredit total 1.000. Rencana pemakaian 455, sisanya cadangan. Setiap script ETL mencetak jumlah panggilan jaringan yang benar-benar terjadi di akhir eksekusi.

**Kepatuhan aturan hackathon**

- Produk bersifat deskriptif. Dilarang memberi saran investasi. Kalimat aman: *"dari N kejadian dengan profil serupa, M berakhir dibekukan dalam 30 hari"*. Kalimat terlarang: *"hindari saham ini"*, *"jual sekarang"*.
- Dilarang mengeksekusi atau mengotomatiskan order beli/jual.
- Disclaimer "Bukan saran investasi" wajib muncul di halaman situs dan di README.
- Repo `Stocklens` milik penulis **tidak boleh** jadi sumber kode. Seluruh kode ditulis dalam build period.
- Temuan n=2 (INPS dan MGLV) **tidak boleh** ditampilkan sebagai angka akurasi di README, situs, maupun video. Sebut sebagai pengamatan awal yang memicu investigasi.
- Setelah submit, repo freeze total: tidak ada commit, push, atau edit, termasuk bugfix.

**Kejujuran data**

- Jendela beku `confirmed` (ada record suspensi resmi di dalam rentangnya) dan `inferred` (hanya disimpulkan dari `volume == 0`) **wajib dibedakan di UI**. Seluruh angka forensik dan base rate dihitung hanya dari jendela `confirmed`.
- Bucket dengan `n < 10` menampilkan "sampel tidak cukup", bukan angka.
- Fitur struktural dari `overview` (float, insider, single-entity) adalah **kondisi sekarang**, bukan historis, dan wajib ditandai begitu di UI.
- Setiap pengecualian dihitung dan ditampilkan di bagian coverage. Tidak ada yang dibuang diam-diam.

**Verifikasi endpoint (sudah dikonfirmasi dari docs.sectors.app, 2026-09-20)**

| Endpoint | Path | Parameter | Kredit | Bentuk respons |
|---|---|---|---|---|
| Suspensi | `GET /v2/suspensions/` | `symbol`, `start`, `end`, `limit` (maks 30), `offset` | 1 | `{"results": [{symbol, suspension_date, reason, pdf_url}], "pagination": {total_count, showing, limit, offset, has_next, has_previous, next_offset, previous_offset}}` |
| Harga harian | `GET /v2/daily/{symbol}/` | `start`, `end` (rentang maks 90 hari) | 1 | array of `{symbol, date, close, open, high, low, volume, market_cap}` — **`open`, `high`, `low` nullable** |
| Company report | `GET /v2/company/report/{symbol}/` | `sections=overview` | 1 per section | `{"overview": {listing_board, sector, sub_sector, market_cap, market_cap_rank, listing_date, last_close_price, all_time_price, tags, indices, ...}}` |
| Screener | `GET /v2/companies/` | `where`, `order_by`, `limit` (maks 200), `offset` | 1 | `{"results": [{symbol, company_name}], "pagination": {...}}` |

Sintaks tag: `where=tags in ['a','b']` berlaku **OR** dalam satu klausa. Untuk AND, rangkai klausa terpisah dengan `and`.

Catatan: endpoint `/v2/tags/` adalah kosakata tag **berita**, bukan tag screener perusahaan seperti `52-w-high` atau `insider-1-month-sell`. Jangan pakai untuk memetakan kosakata tag emiten.

---

## Struktur File

| File | Tanggung jawab |
|---|---|
| `freezebyte/__init__.py` | Penanda package, kosong. |
| `freezebyte/config.py` | Baca `.env`, sediakan `API_KEY`, `BASE_URL`, path direktori. Satu-satunya tempat konstanta lingkungan. |
| `freezebyte/client.py` | Ambil data dari API, cache ke disk, hitung panggilan jaringan. Satu-satunya modul yang import `requests`. |
| `freezebyte/freeze.py` | Deteksi jendela beku dari deret harga. Fungsi murni. |
| `freezebyte/features.py` | Mesin fitur. `(rows, as_of) -> dict`. Fungsi murni. |
| `freezebyte/reasons.py` | Klasifikasi teks `reason` resmi IDX ke kategori. Fungsi murni. |
| `freezebyte/baserates.py` | Bucketing dan perhitungan base rate. Fungsi murni. |
| `freezebyte/coverage.py` | Akumulator pengecualian: apa yang gugur dan kenapa. Fungsi murni. |
| `freezebyte/build.py` | Orkestrasi. Baca cache, jalankan mesin, tulis `data/web/*.json`. |
| `scripts/etl_suspensions.py` | Tarik seluruh halaman suspensi. |
| `scripts/etl_prices.py` | Tarik harga untuk sampel kejadian dan kontrol. |
| `scripts/etl_overviews.py` | Tarik `overview` untuk sampel emiten. |
| `scripts/report_discovery.py` | Cetak distribusi alasan, kosakata tag, dan tercile bucket. Outputnya jadi input konstanta di `baserates.py`. |
| `site/index.html` | Halaman tunggal, tiga bagian. |
| `site/style.css` | Styling. |
| `site/app.js` | Fetch JSON, render tabel dan chip. |
| `site/chart.js` | Gambar SVG grafik harga dengan shading jendela beku. |
| `data/raw/` | Cache mentah. **Tidak di-commit.** |
| `data/web/` | Output build. **Di-commit.** |
| `tests/fixtures/` | Fixture JSON yang di-commit supaya test jalan offline. |

---

## Urutan dan Jadwal

Hari ini 2026-09-20. Deadline submit 2026-09-30 23:59 WIB.

| Tanggal | Task |
|---|---|
| 20 Sep | Task 1–4 |
| 21–22 Sep | Task 5–7 (ETL, keluar kredit) |
| 23–24 Sep | Task 8–9 |
| 25–26 Sep | Task 10–11 |
| 27 Sep | Task 12, refresh data final |
| 28–29 Sep | Task 13 (video dan sosial media, dua hari penuh) |
| 30 Sep | Submit, sisa hari jadi buffer |

Task 1–4 dan 8–9 bisa dikerjakan offline setelah fixture ALKA turun. Hanya Task 5–7 dan 12 yang mengeluarkan kredit.

---

### Task 1: Scaffold proyek dan push commit pertama

**Files:**
- Create: `requirements.txt`
- Create: `pyproject.toml`
- Create: `.env.example`
- Create: `freezebyte/__init__.py`
- Create: `freezebyte/config.py`
- Create: `tests/__init__.py`
- Create: `tests/test_config.py`
- Create: `README.md`

**Interfaces:**
- Consumes: tidak ada.
- Produces: `freezebyte.config.BASE_URL: str`, `config.api_key() -> str`, `config.RAW_DIR: Path`, `config.WEB_DIR: Path`, `config.FIXTURE_DIR: Path`.

- [ ] **Step 1: Buat `requirements.txt`**

```
requests==2.32.3
python-dotenv==1.0.1
pytest==8.3.3
```

- [ ] **Step 2: Buat `pyproject.toml`**

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-q"

[tool.setuptools.packages.find]
include = ["freezebyte*"]
```

- [ ] **Step 3: Buat `.env.example`**

```
# Salin file ini jadi .env lalu isi dengan key dari portal hackathon Sectors.
# .env tidak pernah di-commit.
SECTORS_API_KEY=
```

- [ ] **Step 4: Tulis test yang gagal**

File `tests/test_config.py`:

```python
from pathlib import Path

from freezebyte import config


def test_base_url_is_v2():
    assert config.BASE_URL == "https://api.sectors.app/v2"


def test_directories_are_absolute_paths():
    for path in (config.RAW_DIR, config.WEB_DIR, config.FIXTURE_DIR):
        assert isinstance(path, Path)
        assert path.is_absolute()


def test_api_key_raises_clear_error_when_missing(monkeypatch):
    monkeypatch.delenv("SECTORS_API_KEY", raising=False)
    monkeypatch.setattr(config, "_load_dotenv_once", lambda: None)
    try:
        config.api_key()
    except RuntimeError as exc:
        assert "SECTORS_API_KEY" in str(exc)
    else:
        raise AssertionError("api_key() harus melempar RuntimeError kalau key tidak ada")
```

- [ ] **Step 5: Jalankan test untuk memastikan gagal**

Run: `python -m pytest tests/test_config.py -v`
Expected: FAIL dengan `ModuleNotFoundError: No module named 'freezebyte'`

- [ ] **Step 6: Tulis implementasi minimal**

File `freezebyte/__init__.py`: kosong.

File `freezebyte/config.py`:

```python
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
```

File `tests/__init__.py`: kosong.

- [ ] **Step 7: Jalankan test untuk memastikan lulus**

Run: `python -m pip install -r requirements.txt && python -m pytest tests/test_config.py -v`
Expected: 3 passed

- [ ] **Step 8: Tulis `README.md`**

```markdown
# FREEZE BYTE

Analisis suspensi perdagangan IDX. Entri Sectors Hackathon 2026, Track 03 Market Intelligence.

Dua pilar di atas satu mesin fitur yang sama: anatomi forensik seluruh pembekuan yang
tercatat, dan daftar pantau emiten hari ini yang kondisinya menyerupai kejadian-kejadian itu.

## Menjalankan situs tanpa API key

Seluruh data hasil build sudah di-commit di `data/web/`. Situs statis membacanya langsung.

```bash
python -m http.server 8000
# buka http://localhost:8000/site/
```

## Menjalankan ulang pipeline (butuh API key)

```bash
cp .env.example .env    # isi SECTORS_API_KEY
pip install -r requirements.txt
python scripts/etl_suspensions.py
python scripts/etl_prices.py
python scripts/etl_overviews.py
python -m freezebyte.build
```

## Test

```bash
python -m pytest
```

Test berjalan offline memakai fixture di `tests/fixtures/`. Tidak butuh API key.

## Disclaimer

Bukan saran investasi. Produk ini bersifat deskriptif dan menyajikan statistik historis
serta frekuensi kondisional. Produk ini tidak merekomendasikan pembelian atau penjualan
efek apa pun, dan tidak mengeksekusi order.
```

- [ ] **Step 9: Commit dan push**

```bash
git add requirements.txt pyproject.toml .env.example freezebyte/ tests/ README.md docs/superpowers/plans/
git commit -m "feat: scaffold project, config module, and README"
git push -u origin main
```

Push ini penting: juri memeriksa commit history dan commit pertama harus tercatat jelas di dalam build period.

---

### Task 2: `client.py` dengan cache disk dan fixture ALKA

**Files:**
- Create: `freezebyte/client.py`
- Create: `tests/test_client.py`
- Create: `scripts/fetch_fixture_alka.py`
- Create: `tests/fixtures/alka_daily.json` (hasil satu panggilan jaringan)

**Interfaces:**
- Consumes: `config.BASE_URL`, `config.api_key()`, `config.RAW_DIR`.
- Produces:
  - `client.get_json(path: str, params: dict, cache_key: str) -> Any`
  - `client.get_suspensions_page(limit: int, offset: int) -> dict`
  - `client.get_prices(symbol: str, start: str, end: str) -> list[dict]`
  - `client.get_overview(symbol: str) -> dict`
  - `client.screen(where: str | None, limit: int, offset: int) -> dict`
  - `client.NETWORK_CALLS: list[str]` — setiap cache miss menambahkan satu entri.

- [ ] **Step 1: Tulis test yang gagal**

File `tests/test_client.py`:

```python
import json

import pytest

from freezebyte import client


class FakeResponse:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status
        self.text = json.dumps(payload)

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def test_cache_miss_calls_network_and_writes_file(tmp_path, monkeypatch):
    monkeypatch.setattr(client.config, "RAW_DIR", tmp_path)
    monkeypatch.setattr(client.config, "api_key", lambda: "dummy")
    client.NETWORK_CALLS.clear()

    calls = []

    def fake_get(url, headers, params, timeout):
        calls.append(url)
        return FakeResponse({"ok": True})

    monkeypatch.setattr(client.requests, "get", fake_get)

    result = client.get_json("/daily/ALKA/", {"start": "2026-09-01"}, "daily/ALKA_2026-09-01")

    assert result == {"ok": True}
    assert len(calls) == 1
    assert (tmp_path / "daily" / "ALKA_2026-09-01.json").exists()
    assert len(client.NETWORK_CALLS) == 1


def test_cache_hit_does_not_call_network(tmp_path, monkeypatch):
    monkeypatch.setattr(client.config, "RAW_DIR", tmp_path)
    monkeypatch.setattr(client.config, "api_key", lambda: "dummy")
    client.NETWORK_CALLS.clear()

    target = tmp_path / "daily" / "ALKA_2026-09-01.json"
    target.parent.mkdir(parents=True)
    target.write_text(json.dumps({"payload": {"cached": True}}), encoding="utf-8")

    def explode(*args, **kwargs):
        raise AssertionError("jaringan tidak boleh dipanggil saat cache hit")

    monkeypatch.setattr(client.requests, "get", explode)

    assert client.get_json("/daily/ALKA/", {}, "daily/ALKA_2026-09-01") == {"cached": True}
    assert client.NETWORK_CALLS == []


def test_auth_header_has_no_bearer_prefix(tmp_path, monkeypatch):
    monkeypatch.setattr(client.config, "RAW_DIR", tmp_path)
    monkeypatch.setattr(client.config, "api_key", lambda: "secret-key")
    captured = {}

    def fake_get(url, headers, params, timeout):
        captured.update(headers)
        return FakeResponse([])

    monkeypatch.setattr(client.requests, "get", fake_get)
    client.get_json("/suspensions/", {}, "suspensions/probe")

    assert captured["Authorization"] == "secret-key"


def test_404_returns_none_and_is_cached_as_unavailable(tmp_path, monkeypatch):
    monkeypatch.setattr(client.config, "RAW_DIR", tmp_path)
    monkeypatch.setattr(client.config, "api_key", lambda: "dummy")

    monkeypatch.setattr(
        client.requests, "get", lambda url, headers, params, timeout: FakeResponse({}, status=404)
    )

    assert client.get_json("/daily/NOPE/", {}, "daily/NOPE") is None
    saved = json.loads((tmp_path / "daily" / "NOPE.json").read_text(encoding="utf-8"))
    assert saved["unavailable"] == 404


def test_429_gives_up_after_max_retries_instead_of_looping_forever(tmp_path, monkeypatch):
    """Rate limit yang bertahan harus berhenti, bukan terus memakan kredit."""
    monkeypatch.setattr(client.config, "RAW_DIR", tmp_path)
    monkeypatch.setattr(client.config, "api_key", lambda: "dummy")
    monkeypatch.setattr(client.time, "sleep", lambda _: None)
    client.NETWORK_CALLS.clear()

    monkeypatch.setattr(
        client.requests, "get", lambda url, headers, params, timeout: FakeResponse({}, status=429)
    )

    with pytest.raises(RuntimeError, match="429"):
        client.get_json("/suspensions/", {}, "suspensions/ratelimited")

    assert len(client.NETWORK_CALLS) == client.MAX_RETRIES + 1
    assert not (tmp_path / "suspensions" / "ratelimited.json").exists()


def test_429_then_success_returns_the_payload(tmp_path, monkeypatch):
    monkeypatch.setattr(client.config, "RAW_DIR", tmp_path)
    monkeypatch.setattr(client.config, "api_key", lambda: "dummy")
    monkeypatch.setattr(client.time, "sleep", lambda _: None)

    responses = [FakeResponse({}, status=429), FakeResponse({"ok": True})]
    monkeypatch.setattr(
        client.requests, "get", lambda url, headers, params, timeout: responses.pop(0)
    )

    assert client.get_json("/suspensions/", {}, "suspensions/recovered") == {"ok": True}


def _record_calls(monkeypatch, tmp_path):
    """Tangkap url dan params yang dikirim wrapper, tanpa menyentuh jaringan."""
    monkeypatch.setattr(client.config, "RAW_DIR", tmp_path)
    monkeypatch.setattr(client.config, "api_key", lambda: "dummy")
    seen = []

    def fake_get(url, headers, params, timeout):
        seen.append((url, dict(params)))
        return FakeResponse({"ok": True})

    monkeypatch.setattr(client.requests, "get", fake_get)
    return seen


def test_get_prices_uppercases_symbol_and_sends_the_date_range(tmp_path, monkeypatch):
    seen = _record_calls(monkeypatch, tmp_path)
    client.get_prices("alka", "2026-06-22", "2026-09-19")

    url, params = seen[0]
    assert url.endswith("/v2/daily/ALKA/")
    assert params == {"start": "2026-06-22", "end": "2026-09-19"}


def test_get_overview_requests_only_the_overview_section(tmp_path, monkeypatch):
    """Menghilangkan `sections` membuat endpoint ini berharga 8 kredit, bukan 1."""
    seen = _record_calls(monkeypatch, tmp_path)
    client.get_overview("inps")

    url, params = seen[0]
    assert url.endswith("/v2/company/report/INPS/")
    assert params == {"sections": "overview"}


def test_get_suspensions_page_passes_limit_and_offset(tmp_path, monkeypatch):
    seen = _record_calls(monkeypatch, tmp_path)
    client.get_suspensions_page(limit=30, offset=60)

    url, params = seen[0]
    assert url.endswith("/v2/suspensions/")
    assert params == {"limit": 30, "offset": 60}


def test_screen_never_sends_a_natural_language_query(tmp_path, monkeypatch):
    """Parameter `q` berharga 3 kredit; query terstruktur 1."""
    seen = _record_calls(monkeypatch, tmp_path)
    client.screen("tags in ['52-w-high']")

    url, params = seen[0]
    assert url.endswith("/v2/companies/")
    assert "q" not in params
    assert params["where"] == "tags in ['52-w-high']"


def test_screen_does_not_reuse_one_cache_file_for_different_limits(tmp_path, monkeypatch):
    """Dua query yang beda `limit` harus jadi dua file, bukan satu.

    Kalau jadi satu, pemanggil kedua diam-diam menerima hasil pemanggil pertama
    dengan jumlah baris yang salah.
    """
    seen = _record_calls(monkeypatch, tmp_path)
    client.screen(None, limit=50)
    client.screen(None, limit=200)

    assert len(seen) == 2
    assert len(list((tmp_path / "companies").glob("*.json"))) == 2


def test_screen_distinguishes_where_clauses_that_differ_only_in_punctuation(tmp_path, monkeypatch):
    seen = _record_calls(monkeypatch, tmp_path)
    client.screen("a-b")
    client.screen("a_b")

    assert len(seen) == 2
    assert len(list((tmp_path / "companies").glob("*.json"))) == 2
```

- [ ] **Step 2: Jalankan test untuk memastikan gagal**

Run: `python -m pytest tests/test_client.py -v`
Expected: FAIL dengan `ModuleNotFoundError: No module named 'freezebyte.client'`

- [ ] **Step 3: Tulis implementasi**

File `freezebyte/client.py`:

```python
"""Satu-satunya modul yang menyentuh jaringan.

Aturan keras: setiap respons ditulis ke disk sebelum dikembalikan ke pemanggil,
dan data yang sudah ada di cache tidak pernah ditarik ulang. Satu-satunya
pengecualian adalah percobaan ulang saat kena 429, dan itu pun dibatasi.
"""
import hashlib
import json
import time
from pathlib import Path
from typing import Any

import requests

from freezebyte import config

TIMEOUT = 30
MAX_RETRIES = 3
RETRY_SLEEP = 5
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
        response = requests.get(
            config.BASE_URL + path,
            headers={"Authorization": config.api_key()},
            params=params,
            timeout=TIMEOUT,
        )
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
```

- [ ] **Step 4: Jalankan test untuk memastikan lulus**

Run: `python -m pytest tests/test_client.py -v`
Expected: 12 passed

- [ ] **Step 5: Tulis script pengambil fixture**

File `scripts/fetch_fixture_alka.py`:

```python
"""Tarik satu window harga ALKA dan simpan sebagai fixture test yang di-commit.

Biaya: 1 kredit. Window 90 hari supaya cukup untuk dist_from_high.
"""
import json

from freezebyte import client, config

START = "2026-06-22"
END = "2026-09-19"


def main():
    rows = client.get_prices("ALKA", START, END)
    if not rows:
        raise SystemExit("ALKA mengembalikan data kosong — periksa API key dan tanggal.")

    config.FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    out = config.FIXTURE_DIR / "alka_daily.json"
    out.write_text(json.dumps(rows, indent=2), encoding="utf-8")

    print(f"{len(rows)} baris tersimpan ke {out}")
    print(f"panggilan jaringan: {len(client.NETWORK_CALLS)}")
    print("\nbaris ber-volume nol:")
    for row in rows:
        if row["volume"] == 0:
            print(" ", row["date"], row["close"])
    print("\nbaris dengan high kosong atau nol:")
    for row in rows:
        if not row.get("high"):
            print(" ", row["date"], "high =", row.get("high"))


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Jalankan script dan periksa hasilnya**

Run: `python scripts/fetch_fixture_alka.py`
Expected: sekitar 60 baris tersimpan, `panggilan jaringan: 1`, dan daftar baris volume nol memuat 2026-09-16, 2026-09-17, 2026-09-18 serta rentang 2026-08-24 sampai 2026-09-02.

Kalau daftar volume nol kosong, berhenti dan laporkan — seluruh asumsi forensik bertumpu pada jejak ini.

Catat nilai `close` pada 2026-09-05 dan 2026-09-01 dari fixture; dua angka itu dipakai di Task 4 Step 1.

- [ ] **Step 7: Commit**

```bash
git add freezebyte/client.py tests/test_client.py scripts/fetch_fixture_alka.py tests/fixtures/alka_daily.json
git commit -m "feat: add caching API client and commit ALKA price fixture"
```

---

### Task 3: `freeze.py` — deteksi jendela beku

**Files:**
- Create: `freezebyte/freeze.py`
- Create: `tests/test_freeze.py`

**Interfaces:**
- Consumes: fixture `tests/fixtures/alka_daily.json`.
- Produces:
  - `freeze.FreezeWindow` — dataclass beku dengan field `start_date: date`, `end_date: date`, `n_days: int`, `price_at_freeze: float`, `reopen_close: float | None`, `reopen_return: float | None`, `confirmed: bool`.
  - `freeze.detect_freeze_windows(rows: list[dict], suspension_dates: Iterable = (), min_days: int = 1) -> list[FreezeWindow]`
  - `freeze.as_date(value) -> date`

**Catatan desain:** spec §5 menulis signature tanpa `suspension_dates`, tapi flag `confirmed` butuh data suspensi. Menaruhnya sebagai parameter mempertahankan fungsi ini tetap murni dan tetap bisa dites tanpa jaringan. Ini penyimpangan yang disengaja dari spec dan lebih baik daripada memanggil client dari dalam fungsi.

- [ ] **Step 1: Tulis test yang gagal**

File `tests/test_freeze.py`:

```python
import json
from datetime import date

import pytest

from freezebyte import config
from freezebyte.freeze import detect_freeze_windows


@pytest.fixture
def alka_rows():
    return json.loads((config.FIXTURE_DIR / "alka_daily.json").read_text(encoding="utf-8"))


def _row(day, close, volume):
    return {"symbol": "TEST", "date": day, "close": close, "high": close,
            "open": close, "low": close, "volume": volume, "market_cap": 0}


def test_detects_four_zero_volume_runs_in_alka(alka_rows):
    """Fixture nyata punya empat deret volume nol, bukan dua.

    Dua di antaranya (2026-07-27 sehari, dan 2026-07-29..2026-08-05) tidak punya
    record suspensi resmi — persis kasus yang membuat flag `confirmed` ada.
    """
    windows = detect_freeze_windows(alka_rows)
    assert len(windows) == 4
    assert [w.n_days for w in windows] == [1, 6, 7, 3]
    assert windows[2].start_date == date(2026, 8, 24)
    assert windows[2].end_date == date(2026, 9, 2)
    assert windows[3].start_date == date(2026, 9, 16)


def test_reopen_return_of_the_august_alka_window(alka_rows):
    august = detect_freeze_windows(alka_rows)[2]
    assert august.price_at_freeze == 4580
    assert august.reopen_close == 4130
    assert august.reopen_return == pytest.approx(-0.0983, abs=5e-4)


def test_open_window_has_no_reopen_values(alka_rows):
    last = detect_freeze_windows(alka_rows)[-1]
    assert last.reopen_close is None
    assert last.reopen_return is None


def test_window_measured_by_row_order_not_calendar_gap():
    """Akhir pekan bukan hari beku. Dua baris beku yang dipisah akhir pekan tetap satu jendela."""
    rows = [
        _row("2026-03-05", 100, 500),
        _row("2026-03-06", 100, 0),   # Jumat
        _row("2026-03-09", 100, 0),   # Senin, ada jeda 2 hari kalender
        _row("2026-03-10", 90, 400),
    ]
    windows = detect_freeze_windows(rows)
    assert len(windows) == 1
    assert windows[0].n_days == 2
    assert windows[0].reopen_return == pytest.approx(-0.10)


def test_confirmed_when_suspension_date_falls_inside_window():
    rows = [
        _row("2026-03-05", 100, 500),
        _row("2026-03-06", 100, 0),
        _row("2026-03-09", 90, 400),
    ]
    confirmed = detect_freeze_windows(rows, suspension_dates=["2026-03-06"])
    assert confirmed[0].confirmed is True


def test_inferred_when_no_matching_suspension_record():
    rows = [
        _row("2026-03-05", 100, 500),
        _row("2026-03-06", 100, 0),
        _row("2026-03-09", 90, 400),
    ]
    inferred = detect_freeze_windows(rows, suspension_dates=["2025-01-02"])
    assert inferred[0].confirmed is False


def test_rows_are_sorted_before_scanning():
    rows = [
        _row("2026-03-09", 90, 400),
        _row("2026-03-05", 100, 500),
        _row("2026-03-06", 100, 0),
    ]
    windows = detect_freeze_windows(rows)
    assert len(windows) == 1
    assert windows[0].start_date == date(2026, 3, 6)


def test_min_days_filters_short_windows():
    rows = [
        _row("2026-03-05", 100, 500),
        _row("2026-03-06", 100, 0),
        _row("2026-03-09", 90, 400),
    ]
    assert detect_freeze_windows(rows, min_days=2) == []
```

- [ ] **Step 2: Jalankan test untuk memastikan gagal**

Run: `python -m pytest tests/test_freeze.py -v`
Expected: FAIL dengan `ModuleNotFoundError: No module named 'freezebyte.freeze'`

- [ ] **Step 3: Tulis implementasi**

File `freezebyte/freeze.py`:

```python
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
```

- [ ] **Step 4: Jalankan test untuk memastikan lulus**

Run: `python -m pytest tests/test_freeze.py -v`
Expected: 8 passed

Angka di test sudah diverifikasi terhadap fixture yang di-commit (63 baris, 2026-06-22 sampai 2026-09-18). Deret volume nol yang sebenarnya:

| # | Mulai | Selesai | Baris | Harga beku | Harga buka | Return |
|---|---|---|---|---|---|---|
| 0 | 2026-07-27 | 2026-07-27 | 1 | 1375 | 1715 | +24,73% |
| 1 | 2026-07-29 | 2026-08-05 | 6 | 1715 | 1885 | +9,91% |
| 2 | 2026-08-24 | 2026-09-02 | 7 | 4580 | 4130 | −9,83% |
| 3 | 2026-09-16 | 2026-09-18 | 3 | 7400 | — | masih terbuka |

Catatan: 2026-08-25 tidak ada barisnya sama sekali di data, dan 2026-09-18 punya `open`/`high`/`low` bernilai 0. Keduanya sengaja dibiarkan apa adanya di fixture — itu bentuk data yang nyata.

Kalau ada test yang gagal karena angka `close` berbeda, **jangan ubah implementasinya**. Periksa fixture dulu, perbaiki angka di test agar cocok, lalu catat nilai sebenarnya di tabel ini.

- [ ] **Step 5: Commit**

```bash
git add freezebyte/freeze.py tests/test_freeze.py
git commit -m "feat: detect freeze windows with confirmed vs inferred cross-check"
```

---

### Task 4: `features.py` — mesin fitur

**Files:**
- Create: `freezebyte/features.py`
- Create: `tests/test_features.py`

**Interfaces:**
- Consumes: `freeze.detect_freeze_windows`, `freeze.as_date`.
- Produces:
  - `features.ret_n(rows, as_of, n) -> float | None`
  - `features.vol_ratio(rows, as_of, window=20) -> float | None`
  - `features.dist_from_high(rows, as_of, window=90) -> float | None`
  - `features.consecutive_up_days(rows, as_of) -> int`
  - `features.compute_features(rows, as_of, suspension_dates=(), structural=None) -> dict` dengan kunci `ret_5d`, `ret_10d`, `ret_20d`, `vol_ratio`, `dist_from_high`, `prior_freeze_count`, `consecutive_up_days`, `structural`.

**Koreksi terhadap spec:** spec §7 menyebut `test_features_alka` menguji "`ret_10d` pada as_of 2026-09-15 = +97,3%". Angka +97,3% itu perjalanan 3.750 (2026-09-07) ke 7.400 (2026-09-15), yang jaraknya **6 baris bursa, bukan 10**. Test di bawah karena itu menguji `ret_n(..., n=6)` untuk angka +97,3%, dan menguji `ret_10d` secara terpisah dengan deret sintetis. Menamai yang 6-baris sebagai `ret_10d` akan menghasilkan angka yang salah di seluruh produk.

**Semantik `dist_from_high`:** mengikuti spec §5, nilainya adalah rasio `close / max(high)`, bukan selisih. 1,0 berarti sedang berada di puncak. Ini didokumentasikan di docstring dan di tooltip situs supaya tidak salah baca.

- [ ] **Step 1: Tulis test yang gagal**

File `tests/test_features.py`:

```python
import json
from datetime import date

import pytest

from freezebyte import config
from freezebyte.features import (
    compute_features,
    consecutive_up_days,
    dist_from_high,
    ret_n,
    vol_ratio,
)


@pytest.fixture
def alka_rows():
    return json.loads((config.FIXTURE_DIR / "alka_daily.json").read_text(encoding="utf-8"))


def _row(day, close, volume, high=None):
    return {"symbol": "TEST", "date": day, "close": close, "open": close,
            "high": close if high is None else high, "low": close,
            "volume": volume, "market_cap": 0}


def test_alka_six_row_return_matches_known_move(alka_rows):
    """3.750 pada 2026-09-07 ke 7.400 pada 2026-09-15 = +97,3% dalam 6 baris bursa."""
    assert ret_n(alka_rows, date(2026, 9, 15), 6) == pytest.approx(0.9733, abs=1e-3)


def test_ret_n_returns_none_when_history_too_short():
    rows = [_row("2026-03-05", 100, 10), _row("2026-03-06", 110, 10)]
    assert ret_n(rows, date(2026, 3, 6), 20) is None


def test_ret_n_uses_row_offset_not_calendar_offset():
    rows = [
        _row("2026-03-05", 100, 10),
        _row("2026-03-06", 110, 10),
        _row("2026-03-09", 121, 10),
    ]
    assert ret_n(rows, date(2026, 3, 9), 2) == pytest.approx(0.21)


def test_vol_ratio_excludes_frozen_rows_from_the_average():
    """Baris ber-volume nol tidak boleh menarik rata-rata ke bawah."""
    rows = [
        _row("2026-03-02", 100, 100),
        _row("2026-03-03", 100, 0),
        _row("2026-03-04", 100, 0),
        _row("2026-03-05", 100, 300),
        _row("2026-03-06", 100, 800),
    ]
    # rata-rata dari baris berdagang saja: (100 + 300) / 2 = 200; 800 / 200 = 4.0
    assert vol_ratio(rows, date(2026, 3, 6), window=4) == pytest.approx(4.0)


def test_vol_ratio_returns_none_when_no_trading_history():
    rows = [_row("2026-03-03", 100, 0), _row("2026-03-04", 100, 500)]
    assert vol_ratio(rows, date(2026, 3, 4), window=1) is None


def test_dist_from_high_ignores_zero_and_null_high():
    """Baris dengan high nol atau null muncul di data nyata dan merusak pembagian."""
    null_high_row = _row("2026-03-04", 100, 0)
    null_high_row["high"] = None

    rows = [
        _row("2026-03-02", 100, 10, high=120),
        _row("2026-03-03", 100, 0, high=0),
        null_high_row,
        _row("2026-03-05", 90, 10, high=95),
    ]
    assert dist_from_high(rows, date(2026, 3, 5), window=90) == pytest.approx(90 / 120)


def test_dist_from_high_returns_none_when_every_high_is_unusable():
    rows = [_row("2026-03-04", 100, 0, high=0), _row("2026-03-05", 100, 0, high=0)]
    assert dist_from_high(rows, date(2026, 3, 5)) is None


def test_consecutive_up_days_stops_at_flat_row():
    rows = [
        _row("2026-03-02", 100, 10),
        _row("2026-03-03", 110, 10),
        _row("2026-03-04", 110, 0),
        _row("2026-03-05", 120, 10),
    ]
    assert consecutive_up_days(rows, date(2026, 3, 5)) == 1


def test_compute_features_returns_every_documented_key(alka_rows):
    result = compute_features(alka_rows, date(2026, 9, 15))
    assert set(result) == {
        "ret_5d", "ret_10d", "ret_20d", "vol_ratio", "dist_from_high",
        "prior_freeze_count", "consecutive_up_days", "structural",
    }


def test_prior_freeze_count_only_counts_confirmed_windows_before_as_of(alka_rows):
    """Hanya jendela confirmed yang dihitung.

    Fixture punya empat deret volume nol; tiga di antaranya selesai sebelum
    2026-09-15. Dengan satu tanggal suspensi resmi (24 Agustus), hanya satu yang
    confirmed. Dua sisanya inferred dan tidak boleh ikut dihitung.
    """
    result = compute_features(
        alka_rows, date(2026, 9, 15), suspension_dates=["2026-08-24"]
    )
    assert result["prior_freeze_count"] == 1


def test_prior_freeze_count_is_zero_without_official_suspension_dates(alka_rows):
    result = compute_features(alka_rows, date(2026, 9, 15))
    assert result["prior_freeze_count"] == 0


def test_as_of_not_in_series_raises():
    rows = [_row("2026-03-05", 100, 10)]
    with pytest.raises(ValueError, match="2026-03-06"):
        compute_features(rows, date(2026, 3, 6))
```

- [ ] **Step 2: Jalankan test untuk memastikan gagal**

Run: `python -m pytest tests/test_features.py -v`
Expected: FAIL dengan `ModuleNotFoundError: No module named 'freezebyte.features'`

- [ ] **Step 3: Tulis implementasi**

File `freezebyte/features.py`:

```python
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
```

- [ ] **Step 4: Jalankan test untuk memastikan lulus**

Run: `python -m pytest tests/test_features.py -v`
Expected: 12 passed

- [ ] **Step 5: Jalankan seluruh test suite**

Run: `python -m pytest -v`
Expected: semua lulus, dan tidak ada test yang menyentuh jaringan

- [ ] **Step 6: Commit**

```bash
git add freezebyte/features.py tests/test_features.py
git commit -m "feat: add pure feature engine with zero-volume and null-high guards"
```

---

### Task 5: ETL suspensi dan klasifikasi alasan

**Files:**
- Create: `scripts/etl_suspensions.py`
- Create: `freezebyte/reasons.py`
- Create: `tests/test_reasons.py`
- Create: `docs/discovery/2026-09-21-suspensions.md`

**Interfaces:**
- Consumes: `client.get_suspensions_page`.
- Produces:
  - `reasons.classify(reason: str | None) -> str` — mengembalikan salah satu dari `"lonjakan_harga"`, `"papan_pemantauan_khusus"`, `"kelangsungan_usaha"`, `"keterbukaan_informasi"`, `"lainnya"`, `"tanpa_alasan"`.
  - File cache `data/raw/suspensions/offset_*.json`.

**Biaya: 20 kredit** (592 record dibagi 30 per halaman).

- [ ] **Step 1: Tulis test yang gagal**

File `tests/test_reasons.py`:

```python
import pytest

from freezebyte.reasons import classify


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Penghentian Sementara Perdagangan Efek PT ALKA Tbk dalam rangka cooling down",
         "lonjakan_harga"),
        ("terjadi peningkatan harga kumulatif yang signifikan", "lonjakan_harga"),
        ("telah berada di Papan Pemantauan Khusus selama lebih dari 1 tahun",
         "papan_pemantauan_khusus"),
        ("adanya ketidakpastian kelangsungan usaha perusahaan tercatat",
         "kelangsungan_usaha"),
        ("keterlambatan penyampaian laporan keuangan", "keterbukaan_informasi"),
        ("alasan yang belum pernah kita lihat sebelumnya", "lainnya"),
        (None, "tanpa_alasan"),
        ("", "tanpa_alasan"),
    ],
)
def test_classify(text, expected):
    assert classify(text) == expected


def test_classify_is_case_insensitive():
    assert classify("COOLING DOWN") == "lonjakan_harga"


def test_price_surge_wins_when_text_mentions_both_surge_and_special_board():
    text = "peningkatan harga kumulatif signifikan pada saham di papan pemantauan khusus"
    assert classify(text) == "lonjakan_harga"
```

- [ ] **Step 2: Jalankan test untuk memastikan gagal**

Run: `python -m pytest tests/test_reasons.py -v`
Expected: FAIL dengan `ModuleNotFoundError: No module named 'freezebyte.reasons'`

- [ ] **Step 3: Tulis implementasi**

File `freezebyte/reasons.py`:

```python
"""Klasifikasi teks alasan resmi IDX ke kategori. Fungsi murni.

Urutan aturan menentukan: kategori yang lebih spesifik diperiksa lebih dulu.
Kosakata di bawah berasal dari 10 record terbaru yang dibaca manual pada
2026-09-19 dan diperluas setelah ETL penuh (lihat docs/discovery/).
"""

RULES = [
    ("lonjakan_harga", ["cooling down", "peningkatan harga", "penurunan harga",
                        "harga kumulatif", "pergerakan harga di luar kebiasaan",
                        "unusual market activity"]),
    ("kelangsungan_usaha", ["kelangsungan usaha", "going concern", "pkpu",
                            "kepailitan", "pailit"]),
    ("papan_pemantauan_khusus", ["papan pemantauan khusus", "pemantauan khusus"]),
    ("keterbukaan_informasi", ["laporan keuangan", "keterbukaan informasi",
                               "keterlambatan penyampaian", "belum menyampaikan"]),
]

UNKNOWN = "lainnya"
MISSING = "tanpa_alasan"


def classify(reason: str | None) -> str:
    if not reason or not reason.strip():
        return MISSING
    text = reason.lower()
    for label, keywords in RULES:
        if any(keyword in text for keyword in keywords):
            return label
    return UNKNOWN
```

- [ ] **Step 4: Jalankan test untuk memastikan lulus**

Run: `python -m pytest tests/test_reasons.py -v`
Expected: 10 passed

- [ ] **Step 5: Tulis script ETL**

File `scripts/etl_suspensions.py`:

```python
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
    """Ambil seluruh halaman suspensi.

    Paginasi ditangani defensif karena script ini menghabiskan kredit sungguhan:
    `next_offset` yang hilang, null, atau tidak maju akan menghentikan loop
    dengan bunyi, bukan mengirim permintaan cacat atau berputar selamanya.
    """
    records, offset, pages = [], 0, 0
    truncated = False

    while True:
        if pages >= MAX_PAGES:
            truncated = True
            break

        page = client.get_suspensions_page(limit=PAGE_SIZE, offset=offset)
        records.extend(page.get("results") or [])
        pages += 1

        pagination = page.get("pagination") or {}
        next_offset = pagination.get("next_offset")
        if not pagination.get("has_next") or next_offset is None:
            break
        if next_offset <= offset:
            raise SystemExit(
                f"Paginasi tidak maju: next_offset {next_offset} <= offset {offset}. "
                "Berhenti daripada mengulang halaman yang sama tanpa henti."
            )
        offset = next_offset

    if truncated:
        print(
            f"PERINGATAN: berhenti di batas {MAX_PAGES} halaman dan API masih "
            "melaporkan halaman berikutnya. Data di bawah ini TIDAK lengkap."
        )

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
```

- [ ] **Step 6: Jalankan ETL**

Run: `python scripts/etl_suspensions.py`
Expected: `total record: 592` (atau lebih kalau ada suspensi baru sejak 2026-09-19), `panggilan jaringan: 20`

- [ ] **Step 7: Perluas aturan klasifikasi sampai kategori `lainnya` di bawah 10%**

Baca daftar "contoh teks yang belum terklasifikasi" dari output. Tambahkan kata kunci baru ke `RULES` di `freezebyte/reasons.py`, tambahkan satu kasus test baru per kata kunci di `tests/test_reasons.py`, lalu jalankan ulang:

Run: `python -m pytest tests/test_reasons.py -v && python scripts/etl_suspensions.py`
Expected: proporsi `lainnya` turun di bawah 10%, dan `panggilan jaringan: 0` pada eksekusi kedua karena seluruh halaman sudah ada di cache.

Angka `panggilan jaringan: 0` itu bukti caching bekerja. Kalau bukan nol, hentikan dan perbaiki `client.get_json` sebelum lanjut — setiap eksekusi ulang akan membakar 20 kredit.

- [ ] **Step 8: Tulis catatan discovery**

File `docs/discovery/2026-09-21-suspensions.md` — salin angka sebenarnya dari output ke tabel berikut:

```markdown
# Discovery: dataset suspensi

Dijalankan <tanggal>. Sumber: `GET /v2/suspensions/`, 20 halaman, 20 kredit.

| Angka | Nilai |
|---|---|
| Total record | |
| Emiten unik | |
| Record dengan `pdf_url` | |
| Tanggal tertua | |
| Tanggal terbaru | |

## Distribusi alasan

| Kategori | Jumlah | Proporsi |
|---|---|---|

## Yang masih masuk kategori "lainnya"

<daftar contoh teks>
```

- [ ] **Step 9: Commit**

```bash
git add scripts/etl_suspensions.py freezebyte/reasons.py tests/test_reasons.py docs/discovery/
git commit -m "feat: fetch full suspension dataset and classify official reasons"
```

---

### Task 6: ETL harga untuk sampel kejadian dan kelompok kontrol

**Files:**
- Create: `scripts/etl_prices.py`
- Create: `freezebyte/sampling.py`
- Create: `tests/test_sampling.py`

**Interfaces:**
- Consumes: `client.get_prices`, `client.screen`, cache `data/raw/suspensions/all.json`.
- Produces:
  - `sampling.pick_events(records: list[dict], limit: int) -> list[dict]` — kejadian terbaru, satu per emiten.
  - `sampling.pick_controls(all_symbols: list[str], suspended_symbols: set[str], limit: int, seed: int) -> list[str]`
  - Cache harga di `data/raw/daily/`.

**Biaya: sekitar 125 kredit** — 60 kejadian, 60 kontrol, dan 5 halaman screener untuk daftar emiten.

**Definisi kelompok kontrol:** emiten yang tidak pernah muncul di dataset suspensi sama sekali, disampel acak dengan seed tetap supaya hasilnya bisa direproduksi. Definisi ini disebutkan terbuka di halaman coverage. Kontrol diambil pada window tanggal yang sama dengan kejadian pasangannya agar kondisi pasar sebanding.

- [ ] **Step 1: Tulis test yang gagal**

File `tests/test_sampling.py`:

```python
from freezebyte.sampling import pick_controls, pick_events


def test_pick_events_takes_most_recent_first():
    records = [
        {"symbol": "AAAA", "suspension_date": "2026-01-05"},
        {"symbol": "BBBB", "suspension_date": "2026-09-01"},
        {"symbol": "CCCC", "suspension_date": "2026-05-05"},
    ]
    assert [e["symbol"] for e in pick_events(records, limit=2)] == ["BBBB", "CCCC"]


def test_pick_events_keeps_only_latest_event_per_symbol():
    records = [
        {"symbol": "AAAA", "suspension_date": "2026-01-05"},
        {"symbol": "AAAA", "suspension_date": "2026-09-01"},
        {"symbol": "BBBB", "suspension_date": "2026-08-01"},
    ]
    picked = {e["symbol"]: e["suspension_date"] for e in pick_events(records, limit=10)}
    assert picked == {"AAAA": "2026-09-01", "BBBB": "2026-08-01"}


def test_pick_controls_excludes_every_suspended_symbol():
    controls = pick_controls(
        ["AAAA", "BBBB", "CCCC", "DDDD"], {"BBBB", "CCCC"}, limit=10, seed=1
    )
    assert set(controls) == {"AAAA", "DDDD"}


def test_pick_controls_is_deterministic_for_a_given_seed():
    universe = [f"S{i:03}" for i in range(200)]
    first = pick_controls(universe, set(), limit=20, seed=42)
    second = pick_controls(universe, set(), limit=20, seed=42)
    assert first == second


def test_pick_controls_respects_limit():
    universe = [f"S{i:03}" for i in range(200)]
    assert len(pick_controls(universe, set(), limit=20, seed=42)) == 20
```

- [ ] **Step 2: Jalankan test untuk memastikan gagal**

Run: `python -m pytest tests/test_sampling.py -v`
Expected: FAIL dengan `ModuleNotFoundError: No module named 'freezebyte.sampling'`

- [ ] **Step 3: Tulis implementasi**

File `freezebyte/sampling.py`:

```python
"""Pemilihan sampel kejadian dan kelompok kontrol. Fungsi murni dan deterministik."""
import random


def pick_events(records: list[dict], limit: int) -> list[dict]:
    """Kejadian suspensi terbaru, satu per emiten.

    Satu emiten bisa punya banyak record; hanya yang terbaru yang diambil supaya
    sampel tidak didominasi segelintir emiten yang sering disuspensi.
    """
    latest: dict[str, dict] = {}
    for record in records:
        symbol = record["symbol"]
        current = latest.get(symbol)
        if current is None or record["suspension_date"] > current["suspension_date"]:
            latest[symbol] = record

    ordered = sorted(latest.values(), key=lambda r: r["suspension_date"], reverse=True)
    return ordered[:limit]


def pick_controls(
    all_symbols: list[str],
    suspended_symbols: set[str],
    limit: int,
    seed: int = 20260920,
) -> list[str]:
    """Emiten yang tidak pernah muncul di dataset suspensi, disampel dengan seed tetap."""
    eligible = sorted(set(all_symbols) - set(suspended_symbols))
    rng = random.Random(seed)
    if len(eligible) <= limit:
        return eligible
    return sorted(rng.sample(eligible, limit))
```

- [ ] **Step 4: Jalankan test untuk memastikan lulus**

Run: `python -m pytest tests/test_sampling.py -v`
Expected: 5 passed

- [ ] **Step 5: Tulis script ETL harga**

File `scripts/etl_prices.py`:

```python
"""Tarik harga 90 hari untuk sampel kejadian suspensi dan kelompok kontrol.

Biaya: sekitar 125 kredit pada eksekusi pertama. Nol pada eksekusi ulang.
Window kontrol disamakan dengan kejadian pasangannya agar kondisi pasar sebanding.
"""
import json
from datetime import timedelta

from freezebyte import client, config
from freezebyte.freeze import as_date
from freezebyte.sampling import pick_controls, pick_events

N_EVENTS = 60
N_CONTROLS = 60
WINDOW_DAYS = 90
MAX_SCREENER_PAGES = 20  # 200 emiten per halaman; IDX punya sekitar 960


def load_suspensions() -> list[dict]:
    path = config.RAW_DIR / "suspensions" / "all.json"
    if not path.exists():
        raise SystemExit("Jalankan scripts/etl_suspensions.py lebih dulu.")
    return json.loads(path.read_text(encoding="utf-8"))


def all_listed_symbols() -> list[str]:
    """Daftar seluruh emiten lewat screener terstruktur.

    Dibatasi jumlah halaman dan menolak `next_offset` yang tidak maju. Loop
    paginasi tanpa batas di script berbayar adalah cara termahal untuk salah.
    """
    symbols, offset, pages = [], 0, 0
    while pages < MAX_SCREENER_PAGES:
        page = client.screen(where=None, limit=200, offset=offset)
        symbols.extend(r["symbol"] for r in page.get("results") or [])
        pages += 1

        pagination = page.get("pagination") or {}
        next_offset = pagination.get("next_offset")
        if not pagination.get("has_next") or next_offset is None:
            break
        if next_offset <= offset:
            raise SystemExit(
                f"Paginasi screener tidak maju: next_offset {next_offset} <= offset {offset}."
            )
        offset = next_offset
    else:
        print(
            f"PERINGATAN: berhenti di batas {MAX_SCREENER_PAGES} halaman screener. "
            "Daftar emiten TIDAK lengkap."
        )
    return symbols


def window_for(end_date) -> tuple[str, str]:
    end = as_date(end_date)
    start = end - timedelta(days=WINDOW_DAYS - 1)
    return start.isoformat(), end.isoformat()


def main():
    records = load_suspensions()
    events = pick_events(records, N_EVENTS)

    manifest = {"events": [], "controls": [], "failures": []}

    for event in events:
        start, end = window_for(event["suspension_date"])
        rows = client.get_prices(event["symbol"], start, end)
        if not rows:
            manifest["failures"].append(
                {"symbol": event["symbol"], "role": "event",
                 "reason": "harga tidak tersedia", "window": [start, end]}
            )
            continue
        manifest["events"].append(
            {"symbol": event["symbol"], "suspension_date": event["suspension_date"],
             "reason": event.get("reason"), "pdf_url": event.get("pdf_url"),
             "window": [start, end], "n_rows": len(rows)}
        )

    suspended = {r["symbol"] for r in records}
    controls = pick_controls(all_listed_symbols(), suspended, N_CONTROLS)

    if not events:
        raise SystemExit(
            "Tidak ada kejadian suspensi, jadi kontrol tidak punya window pembanding."
        )

    # Setiap kontrol dipasangkan ke satu kejadian dan memakai window kejadian itu.
    # Memakai satu window global untuk semua kontrol akan menghadapkan kontrol
    # milik suspensi Januari pada kondisi pasar September, dan perbandingannya
    # kehilangan artinya. Pasangannya dicatat di manifest supaya bisa diaudit.
    for i, symbol in enumerate(controls):
        paired = events[i % len(events)]
        start, end = window_for(paired["suspension_date"])
        rows = client.get_prices(symbol, start, end)
        if not rows:
            manifest["failures"].append(
                {"symbol": symbol, "role": "control",
                 "reason": "harga tidak tersedia", "window": [start, end],
                 "paired_event": paired["symbol"]}
            )
            continue
        manifest["controls"].append(
            {"symbol": symbol, "window": [start, end], "n_rows": len(rows),
             "paired_event": paired["symbol"],
             "paired_suspension_date": paired["suspension_date"]}
        )

    path = config.RAW_DIR / "manifest_prices.json"
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"kejadian berhasil : {len(manifest['events'])} dari {len(events)}")
    print(f"kontrol berhasil  : {len(manifest['controls'])} dari {len(controls)}")
    print(f"gagal             : {len(manifest['failures'])}")
    print(f"panggilan jaringan (kredit terpakai): {len(client.NETWORK_CALLS)}")

    for failure in manifest["failures"]:
        print("  gagal:", failure["symbol"], failure["role"], failure["reason"])


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Jalankan ETL harga**

Run: `python scripts/etl_prices.py`
Expected: sekitar 125 panggilan jaringan, dan `manifest_prices.json` berisi daftar kejadian, kontrol, serta kegagalan.

- [ ] **Step 7: Jalankan ulang untuk membuktikan cache bekerja**

Run: `python scripts/etl_prices.py`
Expected: `panggilan jaringan (kredit terpakai): 0`

Kalau bukan nol, hentikan dan perbaiki sebelum lanjut.

- [ ] **Step 8: Gerbang keputusan risiko**

Spec §13 mewajibkan keputusan ini diambil **segera setelah ETL pertama**, bukan di minggu kedua.

Hitung berapa kejadian yang punya data harga cukup panjang untuk menghitung `ret_10d` dan `vol_ratio`:

Run:
```bash
python -c "
import json
from freezebyte import config
m = json.loads((config.RAW_DIR / 'manifest_prices.json').read_text(encoding='utf-8'))
usable = [e for e in m['events'] if e['n_rows'] >= 21]
print('kejadian dengan >= 21 baris:', len(usable), 'dari', len(m['events']))
"
```

Keputusan:
- **30 kejadian atau lebih** → lanjut sesuai rencana, pilar prediktif tetap berlabel base rate.
- **Kurang dari 30** → ubah label pilar 3 jadi "daftar pantau, akurasi belum diketahui" dengan snapshot bertanggal di repo, dan catat keputusan ini di `docs/discovery/`. Jangan menaikkan klaim.

Catat hasilnya di `docs/discovery/2026-09-21-suspensions.md`.

- [ ] **Step 9: Commit**

```bash
git add scripts/etl_prices.py freezebyte/sampling.py tests/test_sampling.py docs/discovery/
git commit -m "feat: sample suspension events and controls, fetch price history"
```

---

### Task 7: ETL overview dan pemetaan kosakata tag

**Files:**
- Create: `scripts/etl_overviews.py`
- Create: `freezebyte/structural.py`
- Create: `tests/test_structural.py`

**Interfaces:**
- Consumes: `client.get_overview`, `client.screen`, `manifest_prices.json`.
- Produces:
  - `structural.extract(overview: dict | None) -> dict` dengan kunci `float_under_25: bool`, `single_entity_70: bool`, `insider_1m_sell: bool`, `at_52w_high: bool`, `tags: list[str]`, `market_cap: int | None`, `listing_board: str | None`, `available: bool`.
  - Cache overview di `data/raw/overview/`.

**Biaya: sekitar 140 kredit** — 60 emiten sampel untuk kosakata tag dan sekitar 80 kandidat aktif.

- [ ] **Step 1: Tulis test yang gagal**

File `tests/test_structural.py`:

```python
from freezebyte.structural import extract


INPS_OVERVIEW = {
    "overview": {
        "listing_board": "Development",
        "market_cap": 1234567890,
        "tags": ["52-w-high", "90-d-high", "insider-1-month-sell",
                 "public-float-under-25", "single-entity-holding-70", "ytd-high"],
    }
}


def test_extract_reads_every_structural_flag_from_tags():
    result = extract(INPS_OVERVIEW)
    assert result["float_under_25"] is True
    assert result["single_entity_70"] is True
    assert result["insider_1m_sell"] is True
    assert result["at_52w_high"] is True
    assert result["available"] is True


def test_missing_tag_means_false_not_unknown():
    result = extract({"overview": {"tags": ["52-w-high"]}})
    assert result["at_52w_high"] is True
    assert result["float_under_25"] is False


def test_none_overview_marks_unavailable_and_flags_are_false():
    result = extract(None)
    assert result["available"] is False
    assert result["float_under_25"] is False
    assert result["tags"] == []


def test_listing_board_is_carried_through_but_is_not_special_board_status():
    """listing_board INPS berbunyi Development padahal INPS disuspensi karena
    berada di Papan Pemantauan Khusus. Field ini bukan status PPK."""
    assert extract(INPS_OVERVIEW)["listing_board"] == "Development"
```

- [ ] **Step 2: Jalankan test untuk memastikan gagal**

Run: `python -m pytest tests/test_structural.py -v`
Expected: FAIL dengan `ModuleNotFoundError: No module named 'freezebyte.structural'`

- [ ] **Step 3: Tulis implementasi**

File `freezebyte/structural.py`:

```python
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
```

- [ ] **Step 4: Jalankan test untuk memastikan lulus**

Run: `python -m pytest tests/test_structural.py -v`
Expected: 4 passed

- [ ] **Step 5: Tulis script ETL overview**

File `scripts/etl_overviews.py`:

```python
"""Tarik overview untuk emiten sampel dan kandidat aktif, lalu petakan kosakata tag.

Biaya: 1 kredit per emiten karena hanya section overview yang diminta.
Memanggil tanpa parameter sections akan menarik 8 section dan menghabiskan 8 kredit.
"""
import json
from collections import Counter

from freezebyte import client, config
from freezebyte.structural import extract

CANDIDATE_WHERE = (
    "tags in ['52-w-high'] and tags in ['public-float-under-25']"
)
CANDIDATE_LIMIT = 80


def sampled_symbols() -> list[str]:
    manifest = json.loads(
        (config.RAW_DIR / "manifest_prices.json").read_text(encoding="utf-8")
    )
    return [e["symbol"] for e in manifest["events"]]


def candidate_symbols() -> list[str]:
    page = client.screen(where=CANDIDATE_WHERE, limit=CANDIDATE_LIMIT, offset=0)
    print(f"kandidat dari screener: {page['pagination']['total_count']} total, "
          f"mengambil {len(page['results'])}")
    return [r["symbol"] for r in page["results"]]


def main():
    symbols = list(dict.fromkeys(sampled_symbols() + candidate_symbols()))

    vocabulary = Counter()
    unavailable = []

    for symbol in symbols:
        data = extract(client.get_overview(symbol))
        if not data["available"]:
            unavailable.append(symbol)
            continue
        vocabulary.update(data["tags"])

    path = config.RAW_DIR / "tag_vocabulary.json"
    path.write_text(
        json.dumps(dict(vocabulary.most_common()), indent=2), encoding="utf-8"
    )

    print(f"emiten diproses: {len(symbols)}")
    print(f"overview tidak tersedia: {len(unavailable)} {unavailable}")
    print(f"panggilan jaringan (kredit terpakai): {len(client.NETWORK_CALLS)}")
    print(f"\nkosakata tag ({len(vocabulary)} tag unik):")
    for tag, count in vocabulary.most_common():
        print(f"  {tag:34} {count:4}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Jalankan ETL overview**

Run: `python scripts/etl_overviews.py`
Expected: sekitar 140 panggilan jaringan, dan daftar kosakata tag tercetak.

Periksa apakah keempat tag di `TAG_FLAGS` benar-benar muncul di kosakata. Kalau ada yang tidak pernah muncul, periksa ejaan slug-nya di output dan perbaiki konstanta di `freezebyte/structural.py` beserta test-nya.

- [ ] **Step 7: Catat kosakata tag di dokumen discovery**

Tambahkan bagian "Kosakata tag teramati" ke `docs/discovery/2026-09-21-suspensions.md` berisi tabel tag dan frekuensinya.

- [ ] **Step 8: Commit**

```bash
git add scripts/etl_overviews.py freezebyte/structural.py tests/test_structural.py docs/discovery/
git commit -m "feat: fetch company overviews and map observed tag vocabulary"
```

---

### Task 8: `baserates.py` — bucketing dan base rate

**Files:**
- Create: `freezebyte/baserates.py`
- Create: `tests/test_baserates.py`
- Create: `scripts/report_discovery.py`
- Modify: `freezebyte/baserates.py` (isi konstanta tercile setelah script dijalankan)

**Interfaces:**
- Consumes: `features.compute_features`.
- Produces:
  - `baserates.Event` — dataclass dengan `symbol: str`, `as_of: date`, `features: dict`, `frozen_within_30d: bool`, `reopen_return: float | None`.
  - `baserates.RET10_TERCILES: tuple[float, float]`
  - `baserates.VOL_TERCILES: tuple[float, float]`
  - `baserates.MIN_SAMPLE: int`
  - `baserates.bucket(features: dict) -> str` — mengembalikan `"r1v1"` sampai `"r3v3"`, atau `"unknown"` kalau salah satu fitur None.
  - `baserates.BaseRate` — dataclass dengan `bucket: str`, `n: int`, `n_frozen_within_30d: int`, `median_reopen_return: float | None`, `sufficient: bool`.
  - `baserates.base_rate(events: list[Event], bucket: str) -> BaseRate`
  - `baserates.terciles(values: list[float]) -> tuple[float, float]`

- [ ] **Step 1: Tulis test yang gagal**

File `tests/test_baserates.py`:

```python
from datetime import date

import pytest

from freezebyte import baserates
from freezebyte.baserates import BaseRate, Event, base_rate, bucket, terciles


def _event(ret10, vol, frozen, reopen=None):
    return Event(
        symbol="TEST",
        as_of=date(2026, 9, 1),
        features={"ret_10d": ret10, "vol_ratio": vol},
        frozen_within_30d=frozen,
        reopen_return=reopen,
    )


def test_terciles_split_values_into_three_parts():
    low, high = terciles([float(i) for i in range(1, 10)])
    assert low == pytest.approx(3.67, abs=0.2)
    assert high == pytest.approx(6.33, abs=0.2)


def test_bucket_uses_configured_boundaries(monkeypatch):
    monkeypatch.setattr(baserates, "RET10_TERCILES", (0.05, 0.20))
    monkeypatch.setattr(baserates, "VOL_TERCILES", (1.0, 3.0))
    assert bucket({"ret_10d": 0.01, "vol_ratio": 0.5}) == "r1v1"
    assert bucket({"ret_10d": 0.10, "vol_ratio": 2.0}) == "r2v2"
    assert bucket({"ret_10d": 0.90, "vol_ratio": 9.0}) == "r3v3"


def test_bucket_is_unknown_when_a_feature_is_missing():
    assert bucket({"ret_10d": None, "vol_ratio": 2.0}) == "unknown"
    assert bucket({"ret_10d": 0.1, "vol_ratio": None}) == "unknown"


def test_base_rate_reports_insufficient_sample_below_threshold(monkeypatch):
    monkeypatch.setattr(baserates, "RET10_TERCILES", (0.05, 0.20))
    monkeypatch.setattr(baserates, "VOL_TERCILES", (1.0, 3.0))
    events = [_event(0.90, 9.0, True) for _ in range(9)]
    result = base_rate(events, "r3v3")
    assert result.n == 9
    assert result.sufficient is False


def test_base_rate_counts_frozen_and_takes_median_reopen(monkeypatch):
    monkeypatch.setattr(baserates, "RET10_TERCILES", (0.05, 0.20))
    monkeypatch.setattr(baserates, "VOL_TERCILES", (1.0, 3.0))
    events = (
        [_event(0.90, 9.0, True, -0.10) for _ in range(6)]
        + [_event(0.90, 9.0, False, -0.30) for _ in range(6)]
    )
    result = base_rate(events, "r3v3")
    assert result.n == 12
    assert result.n_frozen_within_30d == 6
    assert result.sufficient is True
    assert result.median_reopen_return == pytest.approx(-0.20)


def test_base_rate_ignores_events_from_other_buckets(monkeypatch):
    monkeypatch.setattr(baserates, "RET10_TERCILES", (0.05, 0.20))
    monkeypatch.setattr(baserates, "VOL_TERCILES", (1.0, 3.0))
    events = [_event(0.90, 9.0, True)] + [_event(0.01, 0.5, True) for _ in range(20)]
    assert base_rate(events, "r3v3").n == 1


def test_median_reopen_is_none_when_no_event_has_reopened(monkeypatch):
    monkeypatch.setattr(baserates, "RET10_TERCILES", (0.05, 0.20))
    monkeypatch.setattr(baserates, "VOL_TERCILES", (1.0, 3.0))
    events = [_event(0.90, 9.0, True, None) for _ in range(12)]
    assert base_rate(events, "r3v3").median_reopen_return is None
```

- [ ] **Step 2: Jalankan test untuk memastikan gagal**

Run: `python -m pytest tests/test_baserates.py -v`
Expected: FAIL dengan `ModuleNotFoundError: No module named 'freezebyte.baserates'`

- [ ] **Step 3: Tulis implementasi dengan konstanta sementara**

File `freezebyte/baserates.py`:

```python
"""Bucketing kejadian dan perhitungan base rate. Fungsi murni.

Pembekuan adalah peristiwa jarang, jadi framing yang benar bersifat kondisional
dan berbasis frekuensi, bukan prediksi individual.
"""
import statistics
from dataclasses import dataclass
from datetime import date

# Batas tercile. Nilai di bawah adalah PLACEHOLDER sementara dan diganti di
# Step 6 dengan angka dari distribusi yang benar-benar teramati.
RET10_TERCILES: tuple[float, float] = (0.0, 0.0)
VOL_TERCILES: tuple[float, float] = (0.0, 0.0)

MIN_SAMPLE = 10
UNKNOWN_BUCKET = "unknown"


@dataclass(frozen=True)
class Event:
    symbol: str
    as_of: date
    features: dict
    frozen_within_30d: bool
    reopen_return: float | None


@dataclass(frozen=True)
class BaseRate:
    bucket: str
    n: int
    n_frozen_within_30d: int
    median_reopen_return: float | None
    sufficient: bool


def terciles(values: list[float]) -> tuple[float, float]:
    """Dua batas yang membagi nilai jadi tiga kelompok seukuran."""
    clean = sorted(v for v in values if v is not None)
    if len(clean) < 3:
        raise ValueError("butuh minimal 3 nilai untuk menghitung tercile")
    cut = statistics.quantiles(clean, n=3, method="inclusive")
    return (cut[0], cut[1])


def _tercile_label(value: float, bounds: tuple[float, float], prefix: str) -> str:
    low, high = bounds
    if value < low:
        return f"{prefix}1"
    if value < high:
        return f"{prefix}2"
    return f"{prefix}3"


def bucket(features: dict) -> str:
    ret10 = features.get("ret_10d")
    vol = features.get("vol_ratio")
    if ret10 is None or vol is None:
        return UNKNOWN_BUCKET
    return _tercile_label(ret10, RET10_TERCILES, "r") + _tercile_label(
        vol, VOL_TERCILES, "v"
    )


def base_rate(events: list[Event], target: str) -> BaseRate:
    """Frekuensi kondisional untuk satu bucket.

    n_frozen_within_30d dihitung dalam 30 hari KALENDER sejak as_of, bukan
    30 baris bursa, supaya bisa dibandingkan dengan tanggal suspensi resmi apa adanya.
    Penandaan itu dilakukan di build.py; fungsi ini hanya menjumlahkan.
    """
    matching = [e for e in events if bucket(e.features) == target]
    reopens = [e.reopen_return for e in matching if e.reopen_return is not None]

    return BaseRate(
        bucket=target,
        n=len(matching),
        n_frozen_within_30d=sum(1 for e in matching if e.frozen_within_30d),
        median_reopen_return=statistics.median(reopens) if reopens else None,
        sufficient=len(matching) >= MIN_SAMPLE,
    )
```

- [ ] **Step 4: Jalankan test untuk memastikan lulus**

Run: `python -m pytest tests/test_baserates.py -v`
Expected: 7 passed

Test memakai `monkeypatch` untuk batas tercile, jadi lulus meskipun konstanta modulnya masih placeholder.

- [ ] **Step 5: Tulis script penghitung tercile**

File `scripts/report_discovery.py`:

```python
"""Hitung batas tercile dari distribusi yang teramati.

Outputnya disalin sebagai konstanta ke freezebyte/baserates.py. Batas bucket
tidak dikarang di muka; dihitung setelah ETL selesai.
"""
import json
from datetime import date

from freezebyte import client, config
from freezebyte.baserates import terciles
from freezebyte.features import compute_features
from freezebyte.freeze import as_date


def price_rows(symbol: str, window: list[str]) -> list[dict] | None:
    return client.get_prices(symbol, window[0], window[1])


def main():
    manifest = json.loads(
        (config.RAW_DIR / "manifest_prices.json").read_text(encoding="utf-8")
    )

    ret10_values, vol_values, skipped = [], [], []

    for entry in manifest["events"] + manifest["controls"]:
        rows = price_rows(entry["symbol"], entry["window"])
        if not rows:
            skipped.append((entry["symbol"], "tidak ada baris"))
            continue

        ordered = sorted(rows, key=lambda r: as_date(r["date"]))
        trading = [r for r in ordered if r["volume"]]
        if len(trading) < 21:
            skipped.append((entry["symbol"], f"hanya {len(trading)} baris berdagang"))
            continue

        as_of = as_date(trading[-1]["date"])
        computed = compute_features(ordered, as_of)
        if computed["ret_10d"] is not None:
            ret10_values.append(computed["ret_10d"])
        if computed["vol_ratio"] is not None:
            vol_values.append(computed["vol_ratio"])

    print(f"ret_10d  n={len(ret10_values)}  terciles={terciles(ret10_values)}")
    print(f"vol_ratio n={len(vol_values)}  terciles={terciles(vol_values)}")
    print(f"\ndilewati: {len(skipped)}")
    for symbol, reason in skipped:
        print("  ", symbol, reason)
    print(f"\npanggilan jaringan: {len(client.NETWORK_CALLS)}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Jalankan script dan isi konstanta**

Run: `python scripts/report_discovery.py`
Expected: `panggilan jaringan: 0` (seluruh harga sudah di cache), dan dua pasang angka tercile tercetak.

Salin angka itu ke `freezebyte/baserates.py`, ganti dua baris placeholder:

```python
# Batas tercile dihitung dari distribusi teramati pada <tanggal>:
# 60 kejadian suspensi + 60 emiten kontrol, dihitung oleh scripts/report_discovery.py.
# Angka ini tidak dikarang di muka.
RET10_TERCILES: tuple[float, float] = (<isi>, <isi>)
VOL_TERCILES: tuple[float, float] = (<isi>, <isi>)
```

- [ ] **Step 7: Jalankan seluruh test suite**

Run: `python -m pytest -v`
Expected: semua lulus

- [ ] **Step 8: Commit**

```bash
git add freezebyte/baserates.py tests/test_baserates.py scripts/report_discovery.py
git commit -m "feat: add base rate buckets with terciles from observed distribution"
```

---

### Task 9: `coverage.py` dan `build.py` — orkestrasi ke JSON

**Files:**
- Create: `freezebyte/coverage.py`
- Create: `tests/test_coverage.py`
- Create: `freezebyte/build.py`
- Create: `tests/test_build.py`

**Interfaces:**
- Consumes: seluruh modul sebelumnya.
- Produces:
  - `coverage.Coverage` — kelas dengan `total: int`, `analyzed: int`, `exclude(symbol, reason)`, `as_dict() -> dict`.
  - `build.main()` menulis `data/web/alka.json`, `events.json`, `distribution.json`, `baserates.json`, `watchlist.json`, `coverage.json`, `meta.json`.
  - `build.frozen_within_30d(symbol, as_of, suspensions) -> bool`

- [ ] **Step 1: Tulis test yang gagal**

File `tests/test_coverage.py`:

```python
from freezebyte.coverage import Coverage


def test_counts_analyzed_and_excluded():
    coverage = Coverage(total=100)
    coverage.exclude("AAAA", "harga tidak tersedia")
    coverage.exclude("BBBB", "harga tidak tersedia")
    coverage.exclude("CCCC", "riwayat terlalu pendek")
    coverage.analyzed = 97

    result = coverage.as_dict()
    assert result["total"] == 100
    assert result["analyzed"] == 97
    assert result["excluded"] == 3
    assert result["by_reason"]["harga tidak tersedia"] == 2
    assert result["by_reason"]["riwayat terlalu pendek"] == 1


def test_excluded_symbols_are_listed_per_reason():
    coverage = Coverage(total=2)
    coverage.exclude("AAAA", "404")
    assert coverage.as_dict()["symbols"]["404"] == ["AAAA"]
```

File `tests/test_build.py`:

```python
from datetime import date

from freezebyte.build import frozen_within_30d


SUSPENSIONS = [
    {"symbol": "AAAA", "suspension_date": "2026-09-20"},
    {"symbol": "BBBB", "suspension_date": "2026-09-20"},
]


def test_true_when_suspension_falls_inside_30_calendar_days():
    assert frozen_within_30d("AAAA", date(2026, 9, 1), SUSPENSIONS) is True


def test_false_when_suspension_is_beyond_30_calendar_days():
    assert frozen_within_30d("AAAA", date(2026, 8, 1), SUSPENSIONS) is False


def test_false_when_suspension_precedes_as_of():
    assert frozen_within_30d("AAAA", date(2026, 9, 25), SUSPENSIONS) is False


def test_window_is_calendar_days_not_trading_rows():
    """30 hari kalender persis masih dihitung masuk."""
    assert frozen_within_30d("AAAA", date(2026, 8, 21), SUSPENSIONS) is True
    assert frozen_within_30d("AAAA", date(2026, 8, 20), SUSPENSIONS) is False


def test_other_symbols_do_not_count():
    assert frozen_within_30d("ZZZZ", date(2026, 9, 1), SUSPENSIONS) is False
```

- [ ] **Step 2: Jalankan test untuk memastikan gagal**

Run: `python -m pytest tests/test_coverage.py tests/test_build.py -v`
Expected: FAIL dengan `ModuleNotFoundError`

- [ ] **Step 3: Tulis `coverage.py`**

File `freezebyte/coverage.py`:

```python
"""Akumulator pengecualian.

Setiap pengecualian dihitung dan ditampilkan, tidak pernah dibuang diam-diam.
Menampilkan angka ini yang membuat produk terbaca jujur.
"""
from collections import defaultdict


class Coverage:
    def __init__(self, total: int):
        self.total = total
        self.analyzed = 0
        self._excluded: dict[str, list[str]] = defaultdict(list)

    def exclude(self, symbol: str, reason: str) -> None:
        self._excluded[reason].append(symbol)

    @property
    def excluded_count(self) -> int:
        return sum(len(symbols) for symbols in self._excluded.values())

    def as_dict(self) -> dict:
        return {
            "total": self.total,
            "analyzed": self.analyzed,
            "excluded": self.excluded_count,
            "by_reason": {r: len(s) for r, s in self._excluded.items()},
            "symbols": {r: sorted(s) for r, s in self._excluded.items()},
        }
```

- [ ] **Step 4: Tulis `build.py`**

File `freezebyte/build.py`:

```python
"""Orkestrasi: baca cache, jalankan mesin, tulis data/web/*.json.

Tidak memanggil jaringan untuk data yang sudah ada di cache, jadi build ulang gratis.
"""
import json
from dataclasses import asdict
from datetime import date, datetime, timedelta

from freezebyte import client, config
from freezebyte.baserates import (
    MIN_SAMPLE,
    RET10_TERCILES,
    VOL_TERCILES,
    Event,
    base_rate,
    bucket,
)
from freezebyte.coverage import Coverage
from freezebyte.features import compute_features
from freezebyte.freeze import as_date, detect_freeze_windows
from freezebyte.reasons import classify
from freezebyte.structural import extract

ALL_BUCKETS = [f"r{r}v{v}" for r in (1, 2, 3) for v in (1, 2, 3)]
MIN_TRADING_ROWS = 21


def frozen_within_30d(symbol: str, as_of: date, suspensions: list[dict]) -> bool:
    """30 hari KALENDER sejak as_of, bukan 30 baris bursa."""
    deadline = as_date(as_of) + timedelta(days=30)
    for record in suspensions:
        if record["symbol"] != symbol:
            continue
        when = as_date(record["suspension_date"])
        if as_date(as_of) < when <= deadline:
            return True
    return False


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _write(name: str, payload) -> None:
    config.WEB_DIR.mkdir(parents=True, exist_ok=True)
    (config.WEB_DIR / name).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    print(f"  ditulis: data/web/{name}")


def build_alka(suspensions: list[dict]) -> dict:
    rows = _read(config.FIXTURE_DIR / "alka_daily.json")
    dates = [r["suspension_date"] for r in suspensions if r["symbol"] == "ALKA"]
    windows = detect_freeze_windows(rows, dates)
    return {
        "symbol": "ALKA",
        "rows": rows,
        "windows": [asdict(w) for w in windows],
        "suspension_records": [r for r in suspensions if r["symbol"] == "ALKA"],
    }


def build_events(manifest: dict, suspensions: list[dict], coverage: Coverage):
    """Kembalikan (events, serialised_events, serialised_controls).

    `events` menggabungkan kejadian dan kontrol karena base rate dihitung dari
    keduanya. Dua daftar serialised dipisah supaya halaman bisa membandingkan
    sebaran kenaikan harga kejadian terhadap kelompok kontrol.
    """
    events, serialised, controls_serialised = [], [], []

    for entry in manifest["events"]:
        symbol = entry["symbol"]
        rows = client.get_prices(symbol, entry["window"][0], entry["window"][1])
        if not rows:
            coverage.exclude(symbol, "harga tidak tersedia")
            continue

        ordered = sorted(rows, key=lambda r: as_date(r["date"]))
        trading = [r for r in ordered if r["volume"]]
        if len(trading) < MIN_TRADING_ROWS:
            coverage.exclude(symbol, "riwayat perdagangan terlalu pendek")
            continue

        # as_of adalah hari bursa terakhir SEBELUM saham dibekukan.
        suspension_date = as_date(entry["suspension_date"])
        before = [r for r in trading if as_date(r["date"]) < suspension_date]
        if not before:
            coverage.exclude(symbol, "tidak ada hari bursa sebelum suspensi")
            continue

        as_of = as_date(before[-1]["date"])
        structural = extract(client.get_overview(symbol))
        computed = compute_features(
            ordered, as_of, suspension_dates=[entry["suspension_date"]],
            structural=structural,
        )

        windows = detect_freeze_windows(ordered, [entry["suspension_date"]])
        confirmed = [w for w in windows if w.confirmed]
        reopen = confirmed[-1].reopen_return if confirmed else None

        events.append(
            Event(symbol=symbol, as_of=as_of, features=computed,
                  frozen_within_30d=True, reopen_return=reopen)
        )
        serialised.append({
            "symbol": symbol,
            "as_of": as_of.isoformat(),
            "suspension_date": entry["suspension_date"],
            "reason": entry.get("reason"),
            "reason_category": classify(entry.get("reason")),
            "pdf_url": entry.get("pdf_url"),
            "features": computed,
            "bucket": bucket(computed),
            "reopen_return": reopen,
            "windows": [asdict(w) for w in windows],
        })
        coverage.analyzed += 1

    for entry in manifest["controls"]:
        symbol = entry["symbol"]
        rows = client.get_prices(symbol, entry["window"][0], entry["window"][1])
        if not rows:
            coverage.exclude(symbol, "harga kontrol tidak tersedia")
            continue
        ordered = sorted(rows, key=lambda r: as_date(r["date"]))
        trading = [r for r in ordered if r["volume"]]
        if len(trading) < MIN_TRADING_ROWS:
            coverage.exclude(symbol, "riwayat kontrol terlalu pendek")
            continue

        as_of = as_date(trading[-1]["date"])
        computed = compute_features(ordered, as_of)
        events.append(
            Event(symbol=symbol, as_of=as_of, features=computed,
                  frozen_within_30d=frozen_within_30d(symbol, as_of, suspensions),
                  reopen_return=None)
        )
        controls_serialised.append({
            "symbol": symbol,
            "as_of": as_of.isoformat(),
            "features": computed,
            "bucket": bucket(computed),
        })

    return events, serialised, controls_serialised


def build_watchlist(suspensions: list[dict], coverage: Coverage) -> list[dict]:
    vocabulary_path = config.RAW_DIR / "tag_vocabulary.json"
    if not vocabulary_path.exists():
        return []

    manifest = _read(config.RAW_DIR / "manifest_prices.json")
    seen = {e["symbol"] for e in manifest["events"]}
    rows = []

    for cache_file in sorted((config.RAW_DIR / "overview").glob("*.json")):
        symbol = cache_file.stem
        if symbol in seen:
            continue
        structural = extract(client.get_overview(symbol))
        if not structural["available"]:
            coverage.exclude(symbol, "overview tidak tersedia")
            continue

        end = date.today().isoformat()
        start = (date.today() - timedelta(days=89)).isoformat()
        prices = client.get_prices(symbol, start, end)
        if not prices:
            coverage.exclude(symbol, "harga kandidat tidak tersedia")
            continue

        ordered = sorted(prices, key=lambda r: as_date(r["date"]))
        trading = [r for r in ordered if r["volume"]]
        if len(trading) < MIN_TRADING_ROWS:
            coverage.exclude(symbol, "riwayat kandidat terlalu pendek")
            continue

        as_of = as_date(trading[-1]["date"])
        computed = compute_features(ordered, as_of, structural=structural)
        rows.append({
            "symbol": symbol,
            "as_of": as_of.isoformat(),
            "features": computed,
            "bucket": bucket(computed),
            "structural": structural,
        })

    rows.sort(key=lambda r: (r["features"]["ret_10d"] or -99), reverse=True)
    return rows


def main():
    suspensions = _read(config.RAW_DIR / "suspensions" / "all.json")
    manifest = _read(config.RAW_DIR / "manifest_prices.json")

    coverage = Coverage(total=len(suspensions))
    print("membangun output...")

    _write("alka.json", build_alka(suspensions))

    events, serialised, controls = build_events(manifest, suspensions, coverage)
    _write("events.json", serialised)

    # Sebaran ret_10d kejadian dibanding kontrol. Dipakai bagian 2 halaman.
    _write("distribution.json", {
        "events": [
            {"symbol": e["symbol"], "ret_10d": e["features"]["ret_10d"],
             "vol_ratio": e["features"]["vol_ratio"]}
            for e in serialised
        ],
        "controls": [
            {"symbol": c["symbol"], "ret_10d": c["features"]["ret_10d"],
             "vol_ratio": c["features"]["vol_ratio"]}
            for c in controls
        ],
        "control_definition": (
            "Emiten yang tidak pernah muncul di dataset suspensi, disampel acak "
            "dengan seed tetap, diukur pada hari bursa terakhir di window yang sama."
        ),
    })

    _write("baserates.json", {
        "min_sample": MIN_SAMPLE,
        "ret10_terciles": list(RET10_TERCILES),
        "vol_terciles": list(VOL_TERCILES),
        "buckets": [asdict(base_rate(events, b)) for b in ALL_BUCKETS],
    })

    _write("watchlist.json", build_watchlist(suspensions, coverage))

    reason_counts: dict[str, int] = {}
    for record in suspensions:
        label = classify(record.get("reason"))
        reason_counts[label] = reason_counts.get(label, 0) + 1

    _write("coverage.json", {
        **coverage.as_dict(),
        "reason_distribution": reason_counts,
        "sample_note": (
            "Sampel forensik dibatasi kejadian terbaru dari total record karena "
            "anggaran kredit API. Kelompok kontrol adalah emiten yang tidak pernah "
            "muncul di dataset suspensi, disampel acak dengan seed tetap."
        ),
    })

    _write("meta.json", {
        "built_at": datetime.now().isoformat(timespec="seconds"),
        "total_suspension_records": len(suspensions),
        "network_calls_this_build": len(client.NETWORK_CALLS),
    })

    print(f"\npanggilan jaringan selama build: {len(client.NETWORK_CALLS)}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Jalankan test untuk memastikan lulus**

Run: `python -m pytest tests/test_coverage.py tests/test_build.py -v`
Expected: 7 passed

- [ ] **Step 6: Jalankan build**

Run: `python -m freezebyte.build`
Expected: tujuh file tertulis di `data/web/`, dan `panggilan jaringan selama build` mendekati nol kecuali untuk harga kandidat watchlist yang tanggalnya baru.

- [ ] **Step 7: Periksa isi output**

Run:
```bash
python -c "
import json
from freezebyte import config
cov = json.loads((config.WEB_DIR / 'coverage.json').read_text(encoding='utf-8'))
print('dianalisis:', cov['analyzed'], 'dari', cov['total'])
print('dikecualikan per alasan:', cov['by_reason'])
br = json.loads((config.WEB_DIR / 'baserates.json').read_text(encoding='utf-8'))
print('bucket dengan sampel cukup:', [b['bucket'] for b in br['buckets'] if b['sufficient']])
"
```

Kalau tidak ada satu pun bucket yang `sufficient`, itu hasil yang sah dan wajib ditampilkan apa adanya sebagai "sampel tidak cukup". Jangan turunkan `MIN_SAMPLE` untuk memaksa angka muncul.

- [ ] **Step 8: Commit**

```bash
git add freezebyte/coverage.py freezebyte/build.py tests/test_coverage.py tests/test_build.py data/web/
git commit -m "feat: orchestrate build pipeline and emit committed web JSON"
```

---

### Task 10: Situs bagian 1 — studi kasus ALKA

**Files:**
- Create: `site/index.html`
- Create: `site/style.css`
- Create: `site/chart.js`

**Interfaces:**
- Consumes: `data/web/alka.json`.
- Produces: fungsi global `renderPriceChart(container, data)` di `chart.js`.

Grafik digambar sebagai SVG buatan sendiri, bukan library. Alasannya bukan ideologi: shading jendela beku dan anotasi persentase jauh lebih mudah dikendalikan dengan SVG langsung, dan tidak ada dependensi eksternal berarti juri bisa membuka halaman tanpa jaringan.

- [ ] **Step 1: Tulis `site/chart.js`**

```javascript
// Grafik harga SVG tanpa dependensi. Jendela beku diberi shading.
const NS = "http://www.w3.org/2000/svg";

function el(name, attrs, text) {
  const node = document.createElementNS(NS, name);
  for (const [key, value] of Object.entries(attrs || {})) {
    node.setAttribute(key, value);
  }
  if (text !== undefined) node.textContent = text;
  return node;
}

function renderPriceChart(container, data) {
  const rows = data.rows.slice().sort((a, b) => a.date.localeCompare(b.date));
  const W = 900, H = 380, PAD = { top: 24, right: 20, bottom: 40, left: 64 };
  const plotW = W - PAD.left - PAD.right;
  const plotH = H - PAD.top - PAD.bottom;

  const closes = rows.map((r) => r.close);
  const yMin = Math.min(...closes) * 0.95;
  const yMax = Math.max(...closes) * 1.05;

  const x = (i) => PAD.left + (i / (rows.length - 1)) * plotW;
  const y = (v) => PAD.top + plotH - ((v - yMin) / (yMax - yMin)) * plotH;
  const indexOf = (date) => rows.findIndex((r) => r.date === date);

  const svg = el("svg", {
    viewBox: `0 0 ${W} ${H}`,
    class: "price-chart",
    role: "img",
    "aria-label": `Grafik harga ${data.symbol} dengan jendela pembekuan ditandai`,
  });

  // Shading jendela beku. Confirmed dan inferred dibedakan secara visual.
  data.windows.forEach((win) => {
    const from = indexOf(win.start_date);
    const to = indexOf(win.end_date);
    if (from < 0 || to < 0) return;
    const left = x(from);
    const width = Math.max(x(to) - left, 3);
    svg.appendChild(
      el("rect", {
        x: left,
        y: PAD.top,
        width: width,
        height: plotH,
        class: win.confirmed ? "freeze-band confirmed" : "freeze-band inferred",
      })
    );
    svg.appendChild(
      el(
        "text",
        { x: left + width / 2, y: PAD.top + 14, class: "freeze-label" },
        win.confirmed ? "beku (terkonfirmasi)" : "volume nol (tersimpulkan)"
      )
    );
  });

  // Sumbu Y
  for (let i = 0; i <= 4; i += 1) {
    const value = yMin + ((yMax - yMin) * i) / 4;
    svg.appendChild(
      el("line", { x1: PAD.left, y1: y(value), x2: W - PAD.right, y2: y(value), class: "grid" })
    );
    svg.appendChild(
      el("text", { x: PAD.left - 8, y: y(value) + 4, class: "axis-label y" },
        Math.round(value).toLocaleString("id-ID"))
    );
  }

  // Sumbu X: tampilkan setiap baris ke-5 supaya tidak bertumpuk
  rows.forEach((row, i) => {
    if (i % 5 !== 0) return;
    svg.appendChild(
      el("text", { x: x(i), y: H - PAD.bottom + 18, class: "axis-label x" },
        row.date.slice(5))
    );
  });

  const path = rows.map((r, i) => `${i === 0 ? "M" : "L"}${x(i)},${y(r.close)}`).join(" ");
  svg.appendChild(el("path", { d: path, class: "price-line" }));

  rows.forEach((row, i) => {
    const dot = el("circle", { cx: x(i), cy: y(row.close), r: 3, class: "price-dot" });
    dot.appendChild(
      el("title", {}, `${row.date}\nclose ${row.close.toLocaleString("id-ID")}\nvolume ${row.volume.toLocaleString("id-ID")}`)
    );
    svg.appendChild(dot);
  });

  container.innerHTML = "";
  container.appendChild(svg);
}

window.renderPriceChart = renderPriceChart;
```

- [ ] **Step 2: Tulis kerangka `site/index.html` dengan bagian 1**

```html
<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>FREEZE BYTE — anatomi suspensi perdagangan IDX</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <header class="site-header">
    <h1>FREEZE BYTE</h1>
    <p class="tagline">
      Investor ritel IDX membeli saham yang sedang lari tanpa tahu bahwa kombinasi
      float tipis, insider yang sedang menjual, dan harga di puncak adalah kondisi
      yang secara historis berakhir dengan saham dibekukan &mdash; dan saat beku,
      mereka tidak bisa keluar.
    </p>
  </header>

  <main>
    <section id="case-study">
      <h2>1. Apa yang terjadi pada ALKA</h2>
      <div id="alka-chart" class="chart-slot">Memuat data&hellip;</div>
      <div id="alka-annotations" class="annotations"></div>
    </section>

    <section id="anatomy">
      <h2>2. Anatomi pembekuan yang tercatat</h2>
      <div id="reason-distribution"></div>
      <div id="regulatory-context"></div>
      <div id="distribution-compare"></div>
      <div id="event-table"></div>
    </section>

    <section id="watchlist">
      <h2>3. Pantau hari ini</h2>
      <p class="caveat">
        Daftar ini deskriptif. Setiap baris menunjukkan kondisi yang menyerupai
        kejadian lampau, bukan prediksi atas emiten tertentu.
      </p>
      <div id="watchlist-table"></div>
    </section>

    <section id="coverage">
      <h2>Coverage dan batasan</h2>
      <div id="coverage-report"></div>
    </section>
  </main>

  <footer>
    <p class="disclaimer">
      <strong>Bukan saran investasi.</strong> FREEZE BYTE bersifat deskriptif dan
      menyajikan statistik historis serta frekuensi kondisional. Produk ini tidak
      merekomendasikan pembelian atau penjualan efek apa pun dan tidak mengeksekusi
      order. Data bersumber dari Sectors API.
    </p>
  </footer>

  <script src="chart.js"></script>
  <script src="app.js"></script>
</body>
</html>
```

- [ ] **Step 3: Tulis `site/style.css`**

```css
:root {
  --bg: #0d1117;
  --panel: #161b22;
  --ink: #e6edf3;
  --muted: #8b949e;
  --line: #58a6ff;
  --confirmed: rgba(248, 81, 73, 0.22);
  --inferred: rgba(139, 148, 158, 0.16);
  --border: #30363d;
}

* { box-sizing: border-box; }

body {
  margin: 0;
  background: var(--bg);
  color: var(--ink);
  font: 16px/1.6 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

.site-header { padding: 48px 24px 24px; max-width: 900px; margin: 0 auto; }
.site-header h1 { font-size: 2.4rem; letter-spacing: 0.08em; margin: 0 0 12px; }
.tagline { color: var(--muted); max-width: 62ch; }

main { max-width: 960px; margin: 0 auto; padding: 0 24px 64px; }
section { margin: 56px 0; }
section h2 { border-bottom: 1px solid var(--border); padding-bottom: 8px; }

.chart-slot { background: var(--panel); border: 1px solid var(--border); border-radius: 8px; padding: 12px; }
.price-chart { width: 100%; height: auto; }
.price-line { fill: none; stroke: var(--line); stroke-width: 2; }
.price-dot { fill: var(--line); opacity: 0.55; }
.grid { stroke: var(--border); stroke-width: 1; }
.axis-label { fill: var(--muted); font-size: 11px; }
.axis-label.y { text-anchor: end; }
.axis-label.x { text-anchor: middle; }

.freeze-band.confirmed { fill: var(--confirmed); }
.freeze-band.inferred { fill: var(--inferred); stroke: var(--muted); stroke-dasharray: 4 4; }
.freeze-label { fill: var(--muted); font-size: 10px; text-anchor: middle; }

.annotations { display: flex; gap: 16px; flex-wrap: wrap; margin-top: 16px; }
.annotation {
  background: var(--panel); border: 1px solid var(--border);
  border-radius: 8px; padding: 12px 16px; min-width: 180px;
}
.annotation .value { font-size: 1.5rem; font-weight: 600; }
.annotation .label { color: var(--muted); font-size: 0.85rem; }

table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
th, td { text-align: left; padding: 8px; border-bottom: 1px solid var(--border); }
th { color: var(--muted); font-weight: 500; }

.chip {
  display: inline-block; padding: 2px 8px; margin: 2px;
  border: 1px solid var(--border); border-radius: 999px; font-size: 0.75rem;
}
.chip.now { border-style: dashed; color: var(--muted); }

.caveat, .disclaimer { color: var(--muted); font-size: 0.9rem; }
.insufficient { color: var(--muted); font-style: italic; }

footer { border-top: 1px solid var(--border); padding: 24px; }
footer .disclaimer { max-width: 900px; margin: 0 auto; }
```

- [ ] **Step 4: Tulis `site/app.js` bagian ALKA saja**

```javascript
const fmtPct = (v) =>
  v === null || v === undefined ? "—" : `${(v * 100).toFixed(1).replace(".", ",")}%`;

async function load(name) {
  const response = await fetch(`../data/web/${name}.json`);
  if (!response.ok) throw new Error(`gagal memuat ${name}.json`);
  return response.json();
}

function annotate(container, alka) {
  const confirmed = alka.windows.filter((w) => w.confirmed);
  const cards = [];

  const reopened = confirmed.filter((w) => w.reopen_return !== null);
  if (reopened.length) {
    const last = reopened[reopened.length - 1];
    cards.push({
      value: fmtPct(last.reopen_return),
      label: `perubahan harga saat dibuka kembali (${last.end_date})`,
    });
  }

  cards.push({ value: confirmed.length, label: "jendela beku terkonfirmasi di window ini" });

  const inferred = alka.windows.length - confirmed.length;
  if (inferred > 0) {
    cards.push({ value: inferred, label: "jendela tersimpulkan dari volume nol saja" });
  }

  container.innerHTML = cards
    .map((c) => `<div class="annotation"><div class="value">${c.value}</div><div class="label">${c.label}</div></div>`)
    .join("");
}

async function main() {
  const alka = await load("alka");
  renderPriceChart(document.getElementById("alka-chart"), alka);
  annotate(document.getElementById("alka-annotations"), alka);
}

main().catch((err) => {
  document.getElementById("alka-chart").textContent = err.message;
});
```

- [ ] **Step 5: Buka situs dan periksa secara visual**

Run: `python -m http.server 8000`
Buka `http://localhost:8000/site/`

Expected: grafik ALKA tampil, dua jendela beku diberi shading, jendela terkonfirmasi berwarna merah solid dan yang tersimpulkan bergaris putus-putus.

Kalau grafik kosong, buka konsol browser. Penyebab paling mungkin adalah path relatif `../data/web/` yang tidak cocok dengan direktori tempat server dijalankan — server harus dijalankan dari akar repo, bukan dari dalam `site/`.

- [ ] **Step 6: Commit**

```bash
git add site/
git commit -m "feat: add ALKA case study section with hand-rolled SVG chart"
```

---

### Task 11: Situs bagian 2 dan 3 — anatomi, pantau hari ini, coverage

**Files:**
- Modify: `site/app.js`

**Interfaces:**
- Consumes: `data/web/events.json`, `baserates.json`, `watchlist.json`, `coverage.json`, `meta.json`, `distribution.json`.

- [ ] **Step 1: Tambahkan render distribusi alasan dan tabel kejadian**

Sisipkan ke `site/app.js` sebelum `async function main()`:

```javascript
const CATEGORY_LABELS = {
  lonjakan_harga: "Lonjakan harga / cooling down",
  papan_pemantauan_khusus: "Papan Pemantauan Khusus >1 tahun",
  kelangsungan_usaha: "Ketidakpastian kelangsungan usaha",
  keterbukaan_informasi: "Keterbukaan informasi / laporan keuangan",
  lainnya: "Lainnya",
  tanpa_alasan: "Tanpa keterangan alasan",
};

function renderReasons(container, distribution) {
  const total = Object.values(distribution).reduce((a, b) => a + b, 0);
  const rows = Object.entries(distribution)
    .sort((a, b) => b[1] - a[1])
    .map(([key, count]) => {
      const label = CATEGORY_LABELS[key] || key;
      const pct = ((count / total) * 100).toFixed(1).replace(".", ",");
      return `<tr><td>${label}</td><td>${count}</td><td>${pct}%</td></tr>`;
    })
    .join("");

  container.innerHTML = `
    <p>Alasan resmi dari ${total} record suspensi.</p>
    <table><thead><tr><th>Alasan</th><th>Jumlah</th><th>Proporsi</th></tr></thead>
    <tbody>${rows}</tbody></table>`;
}

function renderEvents(container, events) {
  const rows = events
    .map((e) => {
      const pdf = e.pdf_url
        ? `<a href="${e.pdf_url}" target="_blank" rel="noopener">pengumuman IDX</a>`
        : "—";
      return `<tr>
        <td><strong>${e.symbol}</strong></td>
        <td>${e.suspension_date}</td>
        <td>${fmtPct(e.features.ret_10d)}</td>
        <td>${e.features.vol_ratio === null ? "—" : e.features.vol_ratio.toFixed(1).replace(".", ",")}&times;</td>
        <td>${fmtPct(e.reopen_return)}</td>
        <td>${pdf}</td>
      </tr>`;
    })
    .join("");

  container.innerHTML = `
    <p>Kondisi setiap emiten pada hari bursa terakhir sebelum dibekukan.
       Setiap baris tertaut ke PDF pengumuman resmi IDX.</p>
    <table><thead><tr>
      <th>Emiten</th><th>Tanggal suspensi</th><th>Return 10 baris</th>
      <th>Rasio volume</th><th>Saat dibuka</th><th>Bukti</th>
    </tr></thead><tbody>${rows}</tbody></table>`;
}
```

- [ ] **Step 2: Tambahkan render daftar pantau dengan base rate**

```javascript
const STRUCTURAL_LABELS = {
  float_under_25: "float &lt;25%",
  single_entity_70: "satu entitas &ge;70%",
  insider_1m_sell: "insider menjual 1 bulan",
  at_52w_high: "di puncak 52 minggu",
};

function chips(structural) {
  return Object.entries(STRUCTURAL_LABELS)
    .filter(([key]) => structural[key])
    .map(([, label]) => `<span class="chip now">${label} &middot; kondisi sekarang</span>`)
    .join("");
}

function renderWatchlist(container, watchlist, baserates) {
  if (!watchlist.length) {
    container.innerHTML = `<p class="insufficient">Tidak ada kandidat yang lolos
      syarat data pada build terakhir.</p>`;
    return;
  }

  const lookup = Object.fromEntries(baserates.buckets.map((b) => [b.bucket, b]));

  const rows = watchlist
    .map((row) => {
      const rate = lookup[row.bucket];
      let rateCell = `<span class="insufficient">sampel tidak cukup</span>`;
      if (rate && rate.sufficient) {
        rateCell = `${rate.n_frozen_within_30d} dari ${rate.n} kejadian dengan
                    profil serupa berakhir dibekukan dalam 30 hari`;
      }
      return `<tr>
        <td><strong>${row.symbol}</strong><br>${chips(row.structural)}</td>
        <td>${fmtPct(row.features.ret_10d)}</td>
        <td>${row.features.vol_ratio === null ? "—" : row.features.vol_ratio.toFixed(1).replace(".", ",")}&times;</td>
        <td>${row.features.prior_freeze_count}</td>
        <td>${rateCell}</td>
      </tr>`;
    })
    .join("");

  container.innerHTML = `
    <table><thead><tr>
      <th>Emiten dan kondisi struktural</th><th>Return 10 baris</th>
      <th>Rasio volume</th><th>Pernah beku</th><th>Base rate kelompoknya</th>
    </tr></thead><tbody>${rows}</tbody></table>
    <p class="caveat">Bucket dengan kurang dari ${baserates.min_sample} kejadian
      ditampilkan sebagai "sampel tidak cukup", bukan angka. Penanda
      "kondisi sekarang" berarti nilai itu diambil hari ini, bukan pada tanggal
      historis &mdash; tag emiten tidak tersedia secara historis.</p>`;
}
```

- [ ] **Step 3: Tambahkan render coverage**

```javascript
function renderCoverage(container, coverage, meta) {
  const reasons = Object.entries(coverage.by_reason)
    .sort((a, b) => b[1] - a[1])
    .map(([reason, count]) => `<tr><td>${reason}</td><td>${count}</td></tr>`)
    .join("");

  container.innerHTML = `
    <p>Dari <strong>${coverage.total}</strong> record suspensi,
       <strong>${coverage.analyzed}</strong> benar-benar bisa dianalisis dan
       <strong>${coverage.excluded}</strong> gugur.</p>
    <table><thead><tr><th>Alasan gugur</th><th>Jumlah</th></tr></thead>
    <tbody>${reasons}</tbody></table>
    <p class="caveat">${coverage.sample_note}</p>
    <p class="caveat">Data dibangun ${meta.built_at}.
       Jendela yang hanya disimpulkan dari volume nol tidak pernah masuk statistik;
       jendela itu hanya tampil sebagai konteks pada grafik per emiten.</p>`;
}
```

- [ ] **Step 4: Tambahkan perbandingan sebaran kejadian dan kontrol**

Spec §8 mensyaratkan bagian 2 menampilkan sebaran kenaikan harga sebelum pembekuan
**dibanding kelompok kontrol**. Tanpa pembanding, angka kejadian tidak bermakna.

```javascript
function summarise(values) {
  const clean = values.filter((v) => v !== null && v !== undefined).sort((a, b) => a - b);
  if (!clean.length) return null;
  const at = (p) => clean[Math.min(clean.length - 1, Math.floor(p * clean.length))];
  return { n: clean.length, p25: at(0.25), median: at(0.5), p75: at(0.75), max: clean[clean.length - 1] };
}

function renderDistribution(container, distribution) {
  const groups = [
    ["Sebelum dibekukan", distribution.events],
    ["Kelompok kontrol", distribution.controls],
  ];

  const rows = groups
    .map(([label, items]) => {
      const stats = summarise(items.map((i) => i.ret_10d));
      if (!stats) return `<tr><td>${label}</td><td colspan="5" class="insufficient">tidak ada data</td></tr>`;
      return `<tr>
        <td>${label}</td><td>${stats.n}</td><td>${fmtPct(stats.p25)}</td>
        <td><strong>${fmtPct(stats.median)}</strong></td><td>${fmtPct(stats.p75)}</td>
        <td>${fmtPct(stats.max)}</td>
      </tr>`;
    })
    .join("");

  container.innerHTML = `
    <h3>Return 10 baris bursa: kejadian dibanding kontrol</h3>
    <table><thead><tr>
      <th>Kelompok</th><th>n</th><th>p25</th><th>median</th><th>p75</th><th>maks</th>
    </tr></thead><tbody>${rows}</tbody></table>
    <p class="caveat">${distribution.control_definition}</p>`;
}

function renderRegulatoryContext(container) {
  container.innerHTML = `
    <h3>Kenapa Papan Pemantauan Khusus penting dibaca di sini</h3>
    <p>Sejak 25 Maret 2024 seluruh saham di Papan Pemantauan Khusus (notasi
      <strong>X</strong>) diperdagangkan lewat Full Call Auction &mdash; lelang berkala,
      bukan tawar-menawar kontinu. Likuiditas turun, order tidak langsung tereksekusi,
      dan batas bawah harga dilonggarkan sampai Rp1.</p>
    <p>Ada sekitar 11 kriteria masuk dan cukup memenuhi satu. Pemicu tersering adalah
      harga rata-rata 6 bulan di bawah sekitar Rp51, likuiditas sangat tipis selama
      6 bulan, opini auditor disclaimer, dan ekuitas negatif. Notasi lain yang sering
      menyertai: <strong>B</strong> permohonan pailit atau PKPU, <strong>E</strong>
      ekuitas negatif, <strong>L</strong> belum menyampaikan laporan keuangan,
      <strong>M</strong> sedang PKPU, <strong>S</strong> tidak ada pendapatan usaha.</p>
    <p class="caveat">Status Papan Pemantauan Khusus <strong>bukan field</strong> di
      Sectors API. <code>listing_board</code> INPS berbunyi "Development" padahal INPS
      disuspensi justru karena berada di papan pemantauan khusus lebih dari satu tahun.
      Status itu hanya bisa disimpulkan dari teks alasan resmi, dan itulah yang
      dilakukan klasifikasi di atas. Jalur eskalasi yang terlihat di data:
      papan pemantauan khusus &rarr; 1 tahun &rarr; suspensi.</p>`;
}
```

- [ ] **Step 5: Perbarui `main()`**

Ganti fungsi `main()` di `site/app.js`:

```javascript
async function main() {
  const [alka, events, baserates, watchlist, coverage, meta, distribution] =
    await Promise.all([
      load("alka"), load("events"), load("baserates"), load("watchlist"),
      load("coverage"), load("meta"), load("distribution"),
    ]);

  renderPriceChart(document.getElementById("alka-chart"), alka);
  annotate(document.getElementById("alka-annotations"), alka);
  renderReasons(document.getElementById("reason-distribution"), coverage.reason_distribution);
  renderRegulatoryContext(document.getElementById("regulatory-context"));
  renderDistribution(document.getElementById("distribution-compare"), distribution);
  renderEvents(document.getElementById("event-table"), events);
  renderWatchlist(document.getElementById("watchlist-table"), watchlist, baserates);
  renderCoverage(document.getElementById("coverage-report"), coverage, meta);
}
```

- [ ] **Step 6: Periksa secara visual**

Run: `python -m http.server 8000`
Buka `http://localhost:8000/site/`

Checklist yang harus lulus sebelum lanjut:
- Tabel perbandingan sebaran menampilkan baris kejadian dan baris kontrol, keduanya dengan n.
- Setiap kejadian punya tautan PDF yang bisa diklik dan terbuka ke pengumuman IDX.
- Setiap chip struktural bertuliskan "kondisi sekarang".
- Minimal satu bucket menampilkan "sampel tidak cukup" kalau memang `n < 10`.
- Bagian coverage menampilkan angka gugur, bukan disembunyikan.
- Disclaimer terlihat di footer tanpa perlu scroll jauh.
- Tidak ada teks yang berbunyi seperti saran: cari kata "beli", "jual", "hindari", "rekomendasi" di seluruh halaman dan pastikan tidak ada.

Run: `grep -riE "(hindari|jual sekarang|rekomendasi beli|sebaiknya beli)" site/ README.md`
Expected: tidak ada hasil

- [ ] **Step 7: Commit**

```bash
git add site/index.html site/app.js
git commit -m "feat: add anatomy, watchlist, and coverage sections"
```

---

### Task 12: README final, refresh data, dan persiapan freeze

**Files:**
- Modify: `README.md`
- Create: `docs/SUBMISSION.md`

- [ ] **Step 1: Jalankan refresh data final**

Hapus cache harga kandidat watchlist saja supaya angkanya mutakhir, lalu build ulang:

```bash
rm -rf data/raw/daily/*_$(date -d '-89 days' +%Y-%m-%d)_*.json 2>/dev/null || true
python scripts/etl_overviews.py
python -m freezebyte.build
```

Expected: `panggilan jaringan` tercetak dan masih di bawah sisa anggaran. Cek sisa kredit di portal hackathon sebelum menjalankan ini.

- [ ] **Step 2: Jalankan seluruh test suite sekali lagi**

Run: `python -m pytest -v`
Expected: semua lulus

- [ ] **Step 3: Lengkapi README**

Tambahkan bagian berikut ke `README.md` setelah judul, isi angka dari `data/web/coverage.json` yang sebenarnya:

```markdown
## Masalah yang diselesaikan

Investor ritel IDX membeli saham yang sedang lari tanpa tahu bahwa kombinasi float
tipis, insider yang sedang menjual, dan harga di puncak adalah kondisi yang secara
historis berakhir dengan saham dibekukan — dan saat beku, mereka tidak bisa keluar.

## Cara kerjanya

`features.py` menerima `(price_series, as_of_date)` dan mengembalikan satu dict fitur.
Analisis forensik memanggilnya dengan `as_of` sehari sebelum suspensi. Daftar pantau
memanggilnya dengan `as_of` hari bursa terakhir. Kode yang sama, dua sudut pandang.

Jendela beku dideteksi dari deret `volume == 0`, lalu di-cross-check terhadap record
suspensi resmi. Jendela `confirmed` punya record resmi di dalam rentangnya; jendela
`inferred` hanya tersimpulkan dari volume dan tidak pernah masuk statistik.

## Sumber data

Sectors API v2: `/v2/suspensions/`, `/v2/daily/{symbol}/`, `/v2/company/report/{symbol}/`,
`/v2/companies/`. Produk ini kehilangan seluruh fungsinya tanpa data Sectors.

## Coverage

Dari <total> record suspensi, <analyzed> dianalisis. Rincian apa yang gugur dan
kenapa ada di halaman, bagian "Coverage dan batasan".

## Batasan yang diakui

- Tag emiten bersifat kondisi sekarang. Tidak ada cara menanyakan tag pada tanggal
  lampau, jadi fitur struktural pada analisis forensik memakai nilai sekarang
  sebagai perkiraan.
- Pembekuan adalah peristiwa jarang. Framing yang dipakai bersifat kondisional dan
  berbasis frekuensi, bukan prediksi individual.
- Data order book tidak tersedia, jadi spoofing dan wash trade tidak bisa dideteksi.
- Sampel forensik dibatasi kejadian terbaru karena anggaran kredit API.
```

- [ ] **Step 4: Tulis `docs/SUBMISSION.md`**

Aturan hackathon §08 mensyaratkan lima hal. Dokumen ini jadi checklist supaya tidak ada yang terlewat di menit terakhir.

```markdown
# Checklist submission

Deadline: 30 September 2026, 23:59 WIB. Setelah submit, repo freeze total.

| Syarat | Status |
|---|---|
| Link repo publik (wajib tetap publik 90 hari setelah pengumuman) | |
| Video teaser 1 menit, publik di YouTube atau media sosial | |
| Video judging maks 3 menit, walkthrough lengkap | |
| Problem statement satu kalimat | |
| Pilihan track dan daftar nama peserta | |
| Postingan media sosial (Instagram / LinkedIn / Threads / TikTok) tag akun Sectors, pakai template thumbnail | |

## Problem statement

Investor ritel IDX membeli saham yang sedang lari tanpa tahu bahwa kombinasi float
tipis, insider yang sedang menjual, dan harga di puncak adalah kondisi yang secara
historis berakhir dengan saham dibekukan — dan saat beku, mereka tidak bisa keluar.

## Track

Track 03 — Market Intelligence.

## Pemeriksaan akhir sebelum submit

- [ ] `git grep -i "SECTORS_API_KEY=" -- ':!*.example'` tidak mengembalikan apa pun
- [ ] `.env` tidak ada di `git ls-files`
- [ ] `python -m pytest` lulus dari clone bersih tanpa `.env`
- [ ] Situs terbuka dan lengkap dari clone bersih tanpa API key
- [ ] Disclaimer ada di halaman dan di README
- [ ] Tidak ada klaim akurasi berbasis n=2 di mana pun
```

- [ ] **Step 5: Verifikasi dari clone bersih**

```bash
cd /tmp && rm -rf freeze-check && git clone <url-repo> freeze-check
cd freeze-check && python -m pip install -r requirements.txt && python -m pytest
python -m http.server 8010
```

Expected: test lulus tanpa `.env`, dan `http://localhost:8010/site/` tampil lengkap dengan data.

Ini simulasi persis apa yang dilakukan juri. Kalau gagal di sini, produk gagal di eligibility check.

- [ ] **Step 6: Commit dan push**

```bash
git add README.md docs/SUBMISSION.md data/web/
git commit -m "docs: finalize README, add submission checklist, refresh web data"
git push
```

---

### Task 13: Video dan postingan media sosial

**Files:**
- Create: `docs/video-script.md`

Dua hari penuh, 28–29 September. Bobot video 30%, sama besar dengan technical depth. Jangan dikompres jadi setengah hari.

- [ ] **Step 1: Tulis naskah video judging (maks 3 menit)**

File `docs/video-script.md`, struktur yang harus diisi:

```markdown
# Naskah video

## Judging video (maks 3 menit)

### 0:00–0:25 — Masalahnya, lewat ALKA
Tampilkan grafik ALKA. Harga naik hampir dua kali lipat dalam enam hari bursa,
lalu volume jadi nol. Pada titik itu pemegang saham tidak bisa keluar.
Ucapkan problem statement satu kalimat.

### 0:25–1:10 — Anatomi kejadian yang tercatat
Scroll ke bagian 2. Tunjukkan distribusi alasan resmi. Klik satu PDF pengumuman
IDX sampai benar-benar terbuka di layar — ini aset kredibilitas terbesar produk.
Tunjukkan sebaran kenaikan harga sebelum pembekuan dibanding kelompok kontrol.

### 1:10–1:55 — Mesin yang sama, dijalankan hari ini
Buka features.py di editor. Tunjukkan bahwa forensik dan daftar pantau memanggil
fungsi yang sama dengan as_of yang berbeda. Lalu scroll ke bagian 3 dan tunjukkan
daftar pantau beserta chip kondisi struktural dan base rate di sebelahnya.

### 1:55–2:25 — Kenapa angkanya bisa dipercaya
Tunjukkan bagian coverage: berapa yang dianalisis, berapa yang gugur, dan kenapa.
Tunjukkan bucket yang berbunyi "sampel tidak cukup". Tunjukkan perbedaan visual
antara jendela terkonfirmasi dan yang hanya tersimpulkan dari volume nol.

### 2:25–2:50 — Jalankan sendiri
Terminal: clone, pytest lulus, buka halaman. Tanpa API key, tanpa kredit.

### 2:50–3:00 — Disclaimer dan penutup
Tampilkan disclaimer di layar dan ucapkan bahwa produk ini deskriptif.

## Teaser 1 menit

Potong 0:00–0:25 dan 1:55–2:15 dari judging video, tambahkan kartu judul di awal
dan disclaimer di akhir.

## Hal yang DILARANG muncul di kedua video

- Angka akurasi apa pun yang berasal dari temuan n=2 (INPS dan MGLV)
- Kata "prediksi", "sinyal beli", "hindari saham ini", "rekomendasi"
- Klaim bahwa produk memprediksi suspensi emiten tertentu
```

- [ ] **Step 2: Rekam dan edit judging video**

Rekam layar mengikuti naskah. Pastikan teks di layar terbaca pada resolusi 1080p. Unggah ke YouTube sebagai publik atau unlisted, dan **buka tautannya di jendela penyamaran untuk memastikan benar-benar bisa diakses** — video yang tidak bisa diakses tidak dinilai.

- [ ] **Step 3: Potong dan unggah teaser 1 menit**

- [ ] **Step 4: Buat postingan media sosial**

Pakai template thumbnail dari penyelenggara, tag akun resmi Sectors, unggah ke Instagram, LinkedIn, Threads, atau TikTok. Simpan tautannya untuk form submission.

- [ ] **Step 5: Isi seluruh baris di `docs/SUBMISSION.md`, commit, push**

```bash
git add docs/video-script.md docs/SUBMISSION.md
git commit -m "docs: add video script and complete submission checklist"
git push
```

- [ ] **Step 6: Submit lewat portal hackathon**

Setelah tombol submit ditekan, **repo freeze total**: tidak ada commit, push, atau edit, termasuk bugfix. Satu-satunya pengecualian adalah kebocoran kredensial — lapor Slack #support, rotate dulu, lalu push commit yang isinya hanya penghapusan.

---

## Catatan untuk pelaksana

**Kalau sebuah test gagal karena data nyata berbeda dari yang diharapkan,** periksa datanya lebih dulu sebelum mengubah kode. Angka di `tests/test_freeze.py` dan `tests/test_features.py` berasal dari pembacaan manual data ALKA pada 2026-09-19. Kalau fixture yang ditarik berisi angka lain, perbaiki test agar cocok dengan fixture dan catat nilai sebenarnya — jangan melonggarkan toleransi sampai test lulus tanpa tahu kenapa.

**Kalau sebuah endpoint mengembalikan 410,** berarti kode masih memakai path v1. Base URL yang benar adalah `https://api.sectors.app/v2`.

**Kalau sebuah script ETL mencetak panggilan jaringan bukan nol pada eksekusi kedua,** hentikan dan perbaiki caching sebelum lanjut. Setiap eksekusi ulang tanpa cache membakar kredit yang tidak bisa dikembalikan.

**Kalau hasil analisis ternyata lemah,** itu hasil yang sah. Ubah label pilar 3 jadi "daftar pantau, akurasi belum diketahui" dan tampilkan angka apa adanya. Kriteria technical depth menilai apakah proyeknya nyata, bukan apakah hasilnya mengesankan.
