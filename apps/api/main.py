from fastapi import FastAPI

from apps.api.routes.tasks import router as tasks_router
from apps.api.routes.events import router as events_router
from apps.api.routes.approvals import router as approvals_router

app = FastAPI(
    title="AutoWorker API",
    version="0.1.0",
    description="API for autonomous AI computer-worker orchestration.",
)

app.include_router(tasks_router)
app.include_router(events_router)
app.include_router(approvals_router)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "autoworker-api"}
