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
