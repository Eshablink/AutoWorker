import logging
import os
import time
from contextlib import asynccontextmanager
from threading import Event, Thread
from uuid import uuid4

from alembic import command
from alembic.config import Config
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from apps.api.database import get_session_factory, get_settings
from apps.api.routes.approvals import router as approvals_router
from apps.api.routes.auth import router as auth_router
from apps.api.routes.documents import router as documents_router
from apps.api.routes.events import router as events_router
from apps.api.routes.tasks import router as tasks_router
from packages.observability.logging import JsonFormatter
from packages.observability.metrics import HTTP_LATENCY, HTTP_REQUESTS, render_metrics

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if os.getenv("AUTOWORKER_AUTO_MIGRATE", "").lower() in {"1", "true", "yes"}:
        command.upgrade(Config("alembic.ini"), "head")
        logging.getLogger("autoworker").info("database_migrations_applied")

    worker_thread = None
    stop_event = Event()
    if os.getenv("AUTOWORKER_WORKER_ENABLED", "").lower() in {"1", "true", "yes"}:
        from apps.worker.main import run_worker

        worker_thread = Thread(
            target=run_worker,
            args=(stop_event,),
            name="autoworker-embedded-worker",
            daemon=True,
        )
        worker_thread.start()
        logger = logging.getLogger("autoworker")
        logger.info("embedded_worker_started")
    try:
        yield
    finally:
        stop_event.set()
        if worker_thread is not None:
            worker_thread.join(timeout=10)
            logging.getLogger("autoworker").info(
                "embedded_worker_stopped",
                extra={"alive": worker_thread.is_alive()},
            )


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
    lifespan=lifespan,
)

if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-Request-ID"],
    )

app.include_router(auth_router)
app.include_router(documents_router)
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


@app.api_route("/", methods=["GET", "HEAD"], tags=["system"])
def root() -> dict[str, str]:
    return {"service": "autoworker-api", "status": "online", "health": "/health", "ready": "/ready"}


@app.api_route("/health", methods=["GET", "HEAD"], tags=["system"])
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

    if settings.redis_url:
        try:
            from redis import Redis
            client = Redis.from_url(settings.redis_url)
            client.ping()
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Redis is unavailable.",
            ) from exc
        finally:
            try:
                client.close()
            except UnboundLocalError:
                pass

    return {"status": "ready", "service": "autoworker-api"}


@app.get("/system/status", tags=["system"])
def system_status() -> dict[str, object]:
    worker_enabled = os.getenv("AUTOWORKER_WORKER_ENABLED", "").lower() in {"1", "true", "yes"}
    worker_mode = "embedded" if worker_enabled else ("external" if settings.redis_url else "disabled")
    database = "PostgreSQL" if settings.database_url.lower().startswith(("postgresql://", "postgresql+")) else "SQLite"
    return {
        "database": database,
        "redis_configured": bool(settings.redis_url),
        "worker_mode": worker_mode,
        "execution": "enabled" if worker_enabled or settings.redis_url else "disabled",
    }


@app.get("/metrics", tags=["system"])
def metrics() -> Response:
    payload, content_type = render_metrics()
    return Response(content=payload, media_type=content_type)
