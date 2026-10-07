from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from apps.api.database import get_session_factory, get_settings
from apps.api.routes.approvals import router as approvals_router
from apps.api.routes.events import router as events_router
from apps.api.routes.tasks import router as tasks_router

settings = get_settings()

app = FastAPI(
    title="AutoWorker API",
    version="0.1.0",
    description="API for autonomous AI computer-worker orchestration.",
)

if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "X-Request-ID"],
    )

app.include_router(tasks_router)
app.include_router(events_router)
app.include_router(approvals_router)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "autoworker-api"}


@app.get("/ready", tags=["system"])
def ready() -> dict[str, str]:
    session = get_session_factory()()
    try:
        session.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is unavailable.",
        ) from exc
    finally:
        session.close()
    return {"status": "ready", "service": "autoworker-api"}
