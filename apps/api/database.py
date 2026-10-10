from functools import lru_cache
from threading import Lock

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from apps.api.settings import Settings
from packages.persistence.sqlalchemy import Base, SqlAlchemyTaskRepository
from packages.worker.broker import RedisStreamsTaskBroker


_schema_init_lock = Lock()


@lru_cache
def get_settings() -> Settings:
    return Settings.from_environment()


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    settings = get_settings()
    connect_args = {"timeout": 30, "check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
    engine = create_engine(settings.database_url, pool_pre_ping=True, connect_args=connect_args)
    if settings.database_url.startswith("sqlite"):
        # WAL lets API reads proceed while the embedded demo worker writes task state.
        # It is especially important for the single-process SQLite demo deployment.
        with engine.connect() as connection:
            connection.exec_driver_sql("PRAGMA journal_mode=WAL")
            connection.exec_driver_sql("PRAGMA synchronous=NORMAL")
    if settings.environment == "development":
        with _schema_init_lock:
            Base.metadata.create_all(engine)
    return sessionmaker(engine, expire_on_commit=False)


@lru_cache
def get_task_broker() -> RedisStreamsTaskBroker | None:
    settings = get_settings()
    if not settings.redis_url:
        return None
    return RedisStreamsTaskBroker.from_url(
        settings.redis_url,
        stream_name=settings.redis_stream_name,
        group_name=settings.redis_group_name,
        stale_idle_ms=settings.redis_stale_idle_ms,
        maxlen=settings.redis_maxlen,
    )


def get_task_repository() -> SqlAlchemyTaskRepository:
    session = get_session_factory()()
    try:
        yield SqlAlchemyTaskRepository(session)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
