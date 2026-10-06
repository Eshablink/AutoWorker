import os

from pydantic import BaseModel, Field


class Settings(BaseModel):
    database_url: str = Field(
        default="sqlite:///./autoworker.db",
        min_length=1,
    )
    environment: str = "development"
    evidence_root: str = "./data/evidence"
    llm_api_key: str | None = None
    llm_model: str | None = None

    @classmethod
    def from_environment(cls) -> "Settings":
        return cls(
            database_url=os.getenv("DATABASE_URL", "sqlite:///./autoworker.db"),
            environment=os.getenv("AUTOWORKER_ENV", "development"),
            evidence_root=os.getenv("EVIDENCE_ROOT", "./data/evidence"),
            llm_api_key=os.getenv("LLM_API_KEY") or None,
            llm_model=os.getenv("LLM_MODEL") or None,
        )
