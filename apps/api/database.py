from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from apps.api.settings import Settings
from packages.persistence.sqlalchemy import Base, SqlAlchemyTaskRepository
from packages.worker.broker import RedisStreamsTaskBroker


@lru_cache
def get_settings() -> Settings:
    return Settings.from_environment()


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    settings = get_settings()
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    if settings.environment == "development":
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
