from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_prediction_status_fails_closed_without_approved_artifacts(monkeypatch):
    monkeypatch.delenv("LEARNING_PREDICTION_MODEL_PATH", raising=False)
    monkeypatch.delenv("LEARNING_PREDICTION_VALIDATION_REPORT", raising=False)
    response = client.get("/api/v1/learning-prediction/status")
    assert response.status_code == 200
    assert response.json()["status"] == "validation_pending"
    assert response.json()["prediction_serving_enabled"] is False
    assert response.json()["validated_for_deployment"] is False


def test_prediction_endpoint_refuses_unvalidated_serving(monkeypatch):
    monkeypatch.delenv("LEARNING_PREDICTION_MODEL_PATH", raising=False)
    monkeypatch.delenv("LEARNING_PREDICTION_VALIDATION_REPORT", raising=False)
    response = client.post(
        "/api/v1/learning-prediction/predict",
        json={"features": {"pretest_score": 0.7}},
    )
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "VALIDATION_PENDING"
