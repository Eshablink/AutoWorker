"""Prometheus metrics for AutoWorker API, queue, broker, and worker operations."""

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

HTTP_REQUESTS = Counter(
    "autoworker_http_requests_total",
    "HTTP requests handled by the AutoWorker API.",
    labelnames=("method", "path", "status"),
)
HTTP_LATENCY = Histogram(
    "autoworker_http_request_duration_seconds",
    "HTTP request duration in seconds.",
    labelnames=("method", "path"),
)
TASKS_CREATED = Counter(
    "autoworker_tasks_created_total",
    "Tasks accepted by the control plane.",
)
APPROVAL_DECISIONS = Counter(
    "autoworker_approval_decisions_total",
    "Human approval decisions recorded.",
    labelnames=("status",),
)
APPROVAL_LATENCY = Histogram(
    "autoworker_approval_decision_latency_seconds",
    "Time from approval creation to a recorded decision.",
    labelnames=("status",),
)
AUTH_FAILURES = Counter(
    "autoworker_auth_failures_total",
    "Rejected or unavailable production authentication attempts.",
    labelnames=("reason",),
)
WORKER_RUNS = Counter(
    "autoworker_worker_runs_total",
    "Worker runtime attempts grouped by lifecycle stage and outcome.",
    labelnames=("stage", "status", "outcome"),
)
WORKER_RUN_DURATION = Histogram(
    "autoworker_worker_run_duration_seconds",
    "Worker runtime duration in seconds.",
    labelnames=("stage",),
)
WORKER_QUEUE_CLAIMS = Counter(
    "autoworker_worker_queue_claims_total",
    "Durable dispatch queue claim outcomes.",
    labelnames=("outcome",),
)
DISPATCH_QUEUE_DEPTH = Gauge(
    "autoworker_dispatch_queue_depth",
    "Number of dispatch queue records currently READY.",
)
BROKER_OPERATIONS = Counter(
    "autoworker_broker_operations_total",
    "Redis or external-broker operation outcomes.",
    labelnames=("operation", "outcome"),
)


def render_metrics() -> tuple[bytes, str]:
    return generate_latest(), CONTENT_TYPE_LATEST
