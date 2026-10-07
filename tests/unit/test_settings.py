from apps.api.settings import Settings


def test_redis_operational_defaults():
    settings = Settings()
    assert settings.redis_stream_name == "autoworker:tasks"
    assert settings.redis_group_name == "autoworkers"
    assert settings.redis_stale_idle_ms == 60_000
    assert settings.redis_maxlen == 10_000
    assert settings.redis_block_ms == 1_000


def test_production_cors_remains_explicit():
    settings = Settings(environment="production")
    assert settings.cors_origins == []
