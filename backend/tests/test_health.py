from fastapi.testclient import TestClient
from app.main import app


def test_health() -> None:
    response = TestClient(app).get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_validation_errors_are_localized() -> None:
    response = TestClient(app).post("/api/v1/auth/login", json={})
    assert response.status_code == 422
    assert response.json() == {
        "detail": {
            "code": "invalid_request",
            "message": "輸入內容有誤，請檢查後再試。",
        }
    }
