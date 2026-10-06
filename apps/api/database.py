from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from apps.api.settings import Settings
from packages.persistence.sqlalchemy import Base, SqlAlchemyTaskRepository


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
