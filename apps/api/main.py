import logging
import time
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from apps.api.database import get_session_factory, get_settings
from apps.api.routes.approvals import router as approvals_router
from apps.api.routes.events import router as events_router
from apps.api.routes.tasks import router as tasks_router
from packages.observability.logging import JsonFormatter
from packages.observability.metrics import HTTP_LATENCY, HTTP_REQUESTS, render_metrics

settings = get_settings()


def _configure_logging() -> logging.Logger:
    logger = logging.getLogger("autoworker")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger


logger = _configure_logging()

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
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        logger.exception(
            "http_request_failed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status": 500,
                "duration_ms": duration_ms,
            },
        )
        raise

    duration_ms = round((time.perf_counter() - started) * 1000, 2)
    route = request.scope.get("route")
    metric_path = getattr(route, "path", request.url.path)
    HTTP_REQUESTS.labels(request.method, metric_path, str(response.status_code)).inc()
    HTTP_LATENCY.labels(request.method, metric_path).observe(duration_ms / 1000)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time-Ms"] = str(duration_ms)
    logger.info(
        "http_request",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": metric_path,
            "status": response.status_code,
            "duration_ms": duration_ms,
        },
    )
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


@app.get("/metrics", tags=["system"])
def metrics() -> Response:
    payload, content_type = render_metrics()
    return Response(content=payload, media_type=content_type)
