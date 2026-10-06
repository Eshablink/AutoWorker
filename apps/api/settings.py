import os

from pydantic import BaseModel, Field


class Settings(BaseModel):
    database_url: str = Field(
        default="sqlite:///./autoworker.db",
        min_length=1,
    )
    environment: str = "development"

    @classmethod
    def from_environment(cls) -> "Settings":
        return cls(
            database_url=os.getenv("DATABASE_URL", "sqlite:///./autoworker.db"),
            environment=os.getenv("AUTOWORKER_ENV", "development"),
        )
