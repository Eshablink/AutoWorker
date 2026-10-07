from fastapi.testclient import TestClient

from apps.api.main import app

client = TestClient(app)


def test_create_and_get_task():
    created = client.post("/tasks", json={"goal": "Process an invoice"})
    assert created.status_code == 201

    payload = created.json()
    assert payload["status"] == "CREATED"
    assert payload["version"] == 1

    fetched = client.get(f"/tasks/{payload['task_id']}")
    assert fetched.status_code == 200
    assert fetched.json()["task_id"] == payload["task_id"]


def test_create_task_rejects_short_goal():
    response = client.post("/tasks", json={"goal": "abc"})
    assert response.status_code == 422


def test_get_missing_task_returns_404():
    response = client.get("/tasks/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


def test_list_tasks_returns_created_tasks():
    first = client.post("/tasks", json={"goal": "First operational task"}).json()
    second = client.post("/tasks", json={"goal": "Second operational task"}).json()

    response = client.get("/tasks?limit=10")
    assert response.status_code == 200
    ids = {item["task_id"] for item in response.json()}
    assert first["task_id"] in ids
    assert second["task_id"] in ids


def test_task_creation_is_recorded_in_audit_history():
    created = client.post("/tasks", json={"goal": "Audit this operational task"}).json()

    response = client.get(f"/tasks/{created['task_id']}/events")
    assert response.status_code == 200
    payload = response.json()
    assert payload["task_id"] == created["task_id"]
    assert payload["events"][0]["event_type"] == "TASK_CREATED"
    assert payload["events"][0]["actor"] == "API"


def test_event_history_respects_limit():
    created = client.post("/tasks", json={"goal": "Bound event history results"}).json()
    response = client.get(f"/tasks/{created['task_id']}/events?limit=1")
    assert response.status_code == 200
    assert len(response.json()["events"]) == 1
