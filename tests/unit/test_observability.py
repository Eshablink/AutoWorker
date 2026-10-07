from packages.observability.metrics import (
    AUTH_FAILURES,
    BROKER_OPERATIONS,
    DISPATCH_QUEUE_DEPTH,
    WORKER_RUN_DURATION,
    WORKER_RUNS,
    render_metrics,
)


def test_metrics_render_contains_worker_and_broker_metrics():
    WORKER_RUNS.labels("test", "COMPLETED", "progressed").inc()
    WORKER_RUN_DURATION.labels("test").observe(0.01)
    BROKER_OPERATIONS.labels("test", "success").inc()
    DISPATCH_QUEUE_DEPTH.set(3)
    AUTH_FAILURES.labels("invalid_token").inc()

    payload, content_type = render_metrics()
    text = payload.decode()

    assert content_type
    assert "autoworker_worker_runs_total" in text
    assert "autoworker_worker_run_duration_seconds" in text
    assert "autoworker_broker_operations_total" in text
    assert "autoworker_dispatch_queue_depth" in text
    assert "autoworker_auth_failures_total" in text
