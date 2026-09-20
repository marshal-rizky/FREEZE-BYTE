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
