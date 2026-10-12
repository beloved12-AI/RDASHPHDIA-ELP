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


def test_prediction_endpoint_accepts_approved_artifact_bundle(monkeypatch, tmp_path):
    model_path = tmp_path / "learning_prediction_model.joblib"
    report_path = tmp_path / "learning-validation-report-approved.json"
    model_path.write_text(
        '{"feature_columns": ["prior_assessment_score", "course_completions", "practice_activity_count"], "model": {"intercept": -1.0, "coefficients": {"prior_assessment_score": 2.5, "course_completions": 0.6, "practice_activity_count": 0.04}}}',
        encoding="utf-8",
    )
    report_path.write_text(
        '{"status": "approved_external_validation", "validated_for_deployment": true, "target": "competency_achieved_30d", "report_version": "1.0.0"}',
        encoding="utf-8",
    )
    monkeypatch.setenv("LEARNING_PREDICTION_MODEL_PATH", str(model_path))
    monkeypatch.setenv("LEARNING_PREDICTION_VALIDATION_REPORT", str(report_path))

    response = client.get("/api/v1/learning-prediction/status")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert response.json()["prediction_serving_enabled"] is True

    response = client.post(
        "/api/v1/learning-prediction/predict",
        json={
            "features": {
                "prior_assessment_score": 0.8,
                "course_completions": 3,
                "practice_activity_count": 50,
            }
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["target"] == "competency_achieved_30d"
    assert 0.0 <= payload["probability"] <= 1.0
    assert payload["validated_for_deployment"] is True
