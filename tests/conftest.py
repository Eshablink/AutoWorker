import os


# Local tests default to SQLite, but CI-provided PostgreSQL/Redis URLs must win.
os.environ.setdefault("AUTOWORKER_ENV", "development")
os.environ.setdefault("DATABASE_URL", "sqlite:///./autoworker-test.db")
os.environ.setdefault("AUTOWORKER_AUTH_SECRET", "test-only-autoworker-auth-secret-not-for-production")
os.environ.setdefault("REDIS_URL", "")
