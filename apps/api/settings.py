import os

from pydantic import BaseModel, Field, field_validator


class Settings(BaseModel):
    database_url: str = Field(
        default="sqlite:///./autoworker.db",
        min_length=1,
    )
    environment: str = "development"
    evidence_root: str = "./data/evidence"
    llm_api_key: str | None = None
    llm_model: str | None = None
    cors_origins: list[str] = Field(default_factory=list)

    @field_validator("cors_origins")
    @classmethod
    def validate_cors_origins(cls, origins: list[str]) -> list[str]:
        normalized = [origin.strip().rstrip("/") for origin in origins if origin.strip()]
        if "*" in normalized:
            raise ValueError("CORS origins must be explicit; wildcard '*' is not allowed.")
        return list(dict.fromkeys(normalized))

    @classmethod
    def from_environment(cls) -> "Settings":
        environment = os.getenv("AUTOWORKER_ENV", "development")
        raw_origins = os.getenv("CORS_ORIGINS")
        if raw_origins is None:
            origins = ["http://localhost:5173"] if environment != "production" else []
        else:
            origins = [origin for origin in raw_origins.split(",") if origin.strip()]

        return cls(
            database_url=os.getenv("DATABASE_URL", "sqlite:///./autoworker.db"),
            environment=environment,
            evidence_root=os.getenv("EVIDENCE_ROOT", "./data/evidence"),
            llm_api_key=os.getenv("LLM_API_KEY") or None,
            llm_model=os.getenv("LLM_MODEL") or None,
            cors_origins=origins,
        )
