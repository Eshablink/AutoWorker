from fastapi.testclient import TestClient

from apps.api.main import app


def test_two_users_are_isolated_for_documents_and_tasks():
    with TestClient(app) as client:
        suffix = __import__("uuid").uuid4().hex
        user_a = client.post("/auth/register", json={"email": f"a-{suffix}@example.com", "password": "correct-horse-1"})
        user_b = client.post("/auth/register", json={"email": f"b-{suffix}@example.com", "password": "correct-horse-2"})
        assert user_a.status_code == 201
        assert user_b.status_code == 201
        token_a = user_a.json()["access_token"]
        token_b = user_b.json()["access_token"]

        document = client.post(
            "/documents",
            headers={"Authorization": f"Bearer {token_a}"},
            files={"file": ("invoice.txt", b"Invoice INV-42 total 250 INR", "text/plain")},
        )
        assert document.status_code == 201
        document_id = document.json()["document_id"]

        own_docs = client.get("/documents", headers={"Authorization": f"Bearer {token_a}"})
        other_docs = client.get("/documents", headers={"Authorization": f"Bearer {token_b}"})
        assert own_docs.status_code == 200
        assert len(own_docs.json()) == 1
        assert other_docs.status_code == 200
        assert other_docs.json() == []

        task = client.post(
            "/tasks",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"goal": "Process my uploaded invoice", "document_id": document_id},
        )
        assert task.status_code == 201
        task_id = task.json()["task_id"]

        assert client.get(f"/tasks/{task_id}", headers={"Authorization": f"Bearer {token_a}"}).status_code == 200
        assert client.get(f"/tasks/{task_id}", headers={"Authorization": f"Bearer {token_b}"}).status_code == 404
        assert client.get(f"/documents/{document_id}", headers={"Authorization": f"Bearer {token_b}"}).status_code == 404
        content_response = client.get(
            f"/documents/{document_id}/content",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert content_response.status_code == 404
