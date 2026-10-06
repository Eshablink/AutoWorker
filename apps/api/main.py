from uuid import uuid4

from fastapi import FastAPI, Request
from sqlalchemy import text

from apps.api.database import get_session_factory
from apps.api.routes.approvals import router as approvals_router
from apps.api.routes.events import router as events_router
from apps.api.routes.tasks import router as tasks_router

app = FastAPI(
    title="AutoWorker API",
    version="0.1.0",
    description="API for autonomous AI computer-worker orchestration.",
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
    finally:
        session.close()
    return {"status": "ready", "service": "autoworker-api"}
