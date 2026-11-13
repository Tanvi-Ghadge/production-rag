from fastapi.testclient import TestClient

from app.main import app


def test_health_is_public() -> None:
    response = TestClient(app).get("/v1/health")
    assert response.status_code == 200
    assert response.json()["chunks"] in (5029, 5256)


def test_feedback_requires_key() -> None:
    response = TestClient(app).post(
        "/v1/feedback",
        json={"trace_id": "t", "rating": "up"},
    )
    assert response.status_code == 401
