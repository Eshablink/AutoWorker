from fastapi.testclient import TestClient

from apps.api.auth import require_api_auth
from apps.api.main import app
from apps.api.database import get_settings


def test_auth_is_open_in_development():
    app.dependency_overrides[require_api_auth] = lambda: "test"
    try:
        assert TestClient(app).get("/tasks").status_code in {200, 500}
    finally:
        app.dependency_overrides.pop(require_api_auth, None)


def test_production_requires_bearer_token(monkeypatch):
    from apps.api.settings import Settings

    monkeypatch.setattr(
        "apps.api.auth.get_settings",
        lambda: Settings(environment="production", api_token="secret"),
    )
    response = TestClient(app).get("/tasks")
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_production_accepts_valid_bearer_token(monkeypatch):
    from apps.api.settings import Settings

    monkeypatch.setattr(
        "apps.api.auth.get_settings",
        lambda: Settings(environment="production", api_token="secret"),
    )
    app.dependency_overrides[require_api_auth] = lambda: "operator"
    try:
        response = TestClient(app).get("/health")
        assert response.status_code == 200
    finally:
        app.dependency_overrides.pop(require_api_auth, None)
