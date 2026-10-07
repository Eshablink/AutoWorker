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

def test_settings_parse_redis_transport_controls(monkeypatch):
    monkeypatch.setenv("REDIS_URL", "rediss://:secret@example.com:6380/4")
    monkeypatch.setenv("REDIS_STREAM_NAME", "prod:autoworker")
    monkeypatch.setenv("REDIS_GROUP_NAME", "prod-workers")
    monkeypatch.setenv("REDIS_STALE_IDLE_MS", "90000")
    monkeypatch.setenv("REDIS_MAXLEN", "25000")
    monkeypatch.setenv("REDIS_BLOCK_MS", "2500")

    settings = Settings.from_environment()

    assert settings.redis_url == "rediss://:secret@example.com:6380/4"
    assert settings.redis_stream_name == "prod:autoworker"
    assert settings.redis_group_name == "prod-workers"
    assert settings.redis_stale_idle_ms == 90000
    assert settings.redis_maxlen == 25000
    assert settings.redis_block_ms == 2500


def test_settings_reject_invalid_redis_controls(monkeypatch):
    monkeypatch.setenv("REDIS_STALE_IDLE_MS", "999")
    with __import__("pytest").raises(ValueError):
        Settings.from_environment()
