from fastapi.testclient import TestClient

from apps.api.main import app


def test_health_endpoint():
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "autoworker-api"}


def test_health_returns_request_correlation_id():
    response = TestClient(app).get("/health", headers={"X-Request-ID": "test-request-1"})
    assert response.headers["X-Request-ID"] == "test-request-1"


def test_health_generates_request_correlation_id():
    response = TestClient(app).get("/health")
    assert response.headers["X-Request-ID"]
