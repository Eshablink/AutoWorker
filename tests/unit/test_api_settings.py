from apps.api.settings import Settings


def test_settings_default_to_local_sqlite(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    settings = Settings.from_environment()
    assert settings.database_url == "sqlite:///./autoworker.db"


def test_settings_default_to_no_cross_origin_access_in_production(monkeypatch):
    monkeypatch.setenv("AUTOWORKER_ENV", "production")
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    settings = Settings.from_environment()
    assert settings.cors_origins == []


def test_settings_parse_multiple_cors_origins(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", " https://example.com,https://dashboard.example.com/ ")
    settings = Settings.from_environment()
    assert settings.cors_origins == ["https://example.com", "https://dashboard.example.com"]


def test_settings_reject_wildcard_cors_origin(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "*")
    with __import__("pytest").raises(ValueError, match="wildcard"):
        Settings.from_environment()
