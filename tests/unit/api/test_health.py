from fastapi.testclient import TestClient

from infinite_interns.api.app import app


def test_health_route() -> None:
    response = TestClient(app).get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
