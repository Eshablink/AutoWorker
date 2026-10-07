"""Prometheus metrics for AutoWorker control-plane and worker operations."""

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

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


def render_metrics() -> tuple[bytes, str]:
    return generate_latest(), CONTENT_TYPE_LATEST
