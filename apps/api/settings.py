import os

from pydantic import BaseModel, Field, field_validator


class Settings(BaseModel):
    redis_url: str | None = None
    redis_stream_name: str = Field(default="autoworker:tasks", min_length=1)
    redis_group_name: str = Field(default="autoworkers", min_length=1)
    redis_stale_idle_ms: int = Field(default=60_000, ge=1_000)
    redis_maxlen: int = Field(default=10_000, ge=100)
    redis_block_ms: int = Field(default=1_000, ge=1, le=60_000)
    api_token: str | None = None
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
            redis_url=os.getenv("REDIS_URL") or None,
            redis_stream_name=os.getenv("REDIS_STREAM_NAME", "autoworker:tasks"),
            redis_group_name=os.getenv("REDIS_GROUP_NAME", "autoworkers"),
            redis_stale_idle_ms=int(os.getenv("REDIS_STALE_IDLE_MS", "60000")),
            redis_maxlen=int(os.getenv("REDIS_MAXLEN", "10000")),
            redis_block_ms=int(os.getenv("REDIS_BLOCK_MS", "1000")),
            api_token=os.getenv("AUTOWORKER_API_TOKEN") or None,
            database_url=os.getenv("DATABASE_URL", "sqlite:///./autoworker.db"),
            environment=environment,
            evidence_root=os.getenv("EVIDENCE_ROOT", "./data/evidence"),
            llm_api_key=os.getenv("LLM_API_KEY") or None,
            llm_model=os.getenv("LLM_MODEL") or None,
            cors_origins=origins,
        )
