from fastapi.testclient import TestClient

from sbs_assistant.api.main import app


def test_health_returns_service_status() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "sbs-assistant",
        "environment": "local",
    }
