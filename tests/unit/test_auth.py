from fastapi.testclient import TestClient

from apps.api.main import app


def test_auth_is_open_in_development():
    response = TestClient(app).get("/health")
    assert response.status_code == 200


def test_production_requires_bearer_token(monkeypatch):
    from apps.api.settings import Settings

    monkeypatch.setattr(
        "apps.api.auth.get_settings",
        lambda: Settings(environment="production", api_token="secret"),
    )
    response = TestClient(app).get("/tasks")
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_production_rejects_invalid_bearer_token(monkeypatch):
    from apps.api.settings import Settings

    monkeypatch.setattr(
        "apps.api.auth.get_settings",
        lambda: Settings(environment="production", api_token="secret"),
    )
    response = TestClient(app).get(
        "/tasks",
        headers={"Authorization": "Bearer wrong"},
    )
    assert response.status_code == 401


def test_production_accepts_valid_bearer_token(monkeypatch):
    from apps.api.settings import Settings

    monkeypatch.setattr(
        "apps.api.auth.get_settings",
        lambda: Settings(environment="production", api_token="secret"),
    )
    response = TestClient(app).get(
        "/tasks",
        headers={"Authorization": "Bearer secret"},
    )
    assert response.status_code in {200, 503}
