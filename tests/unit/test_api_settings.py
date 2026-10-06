from apps.api.settings import Settings


def test_settings_default_to_local_sqlite(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    settings = Settings.from_environment()
    assert settings.database_url == "sqlite:///./autoworker.db"
