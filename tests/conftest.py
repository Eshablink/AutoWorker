import os


# Unit tests exercise the local SQLite demo configuration explicitly. This must
# run before application modules are imported during test collection.
os.environ["AUTOWORKER_ENV"] = "development"
os.environ["DATABASE_URL"] = "sqlite:///./autoworker-test.db"
os.environ.pop("REDIS_URL", None)
