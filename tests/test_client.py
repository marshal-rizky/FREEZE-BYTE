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


def test_connection_error_then_success_returns_the_payload(tmp_path, monkeypatch):
    monkeypatch.setattr(client.config, "RAW_DIR", tmp_path)
    monkeypatch.setattr(client.config, "api_key", lambda: "dummy")
    monkeypatch.setattr(client.time, "sleep", lambda _: None)
    client.NETWORK_CALLS.clear()

    responses = [
        client.requests.exceptions.ConnectionError("connection forcibly closed"),
        FakeResponse({"ok": True}),
    ]

    def fake_get(url, headers, params, timeout):
        item = responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    monkeypatch.setattr(client.requests, "get", fake_get)

    assert client.get_json("/suspensions/", {}, "suspensions/reconnected") == {"ok": True}
    assert len(client.NETWORK_CALLS) == 2


def test_connection_error_gives_up_after_max_retries_instead_of_looping_forever(tmp_path, monkeypatch):
    """Kegagalan transport (tanpa respons sama sekali) harus berhenti, bukan diam-diam hilang."""
    monkeypatch.setattr(client.config, "RAW_DIR", tmp_path)
    monkeypatch.setattr(client.config, "api_key", lambda: "dummy")
    monkeypatch.setattr(client.time, "sleep", lambda _: None)
    client.NETWORK_CALLS.clear()

    def fake_get(url, headers, params, timeout):
        raise client.requests.exceptions.ConnectionError(
            "An existing connection was forcibly closed by the remote host"
        )

    monkeypatch.setattr(client.requests, "get", fake_get)

    with pytest.raises(RuntimeError, match="Gagal terhubung"):
        client.get_json("/suspensions/", {}, "suspensions/unreachable")

    assert len(client.NETWORK_CALLS) == client.MAX_RETRIES + 1
    assert not (tmp_path / "suspensions" / "unreachable.json").exists()


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
