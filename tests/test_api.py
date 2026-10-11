from fastapi.testclient import TestClient

from app.api.routes import learning
from app.main import app


client = TestClient(app)
PAGES_ORIGIN = "https://beloved12-ai.github.io"


def setup_function():
    # The prototype service stores data in process memory; isolate each test.
    learning.learners.clear()
    learning.courses.clear()
    learning.events.clear()


def create_learner():
    response = client.post(
        "/api/v1/learners",
        json={
            "learner_id": "learner-test",
            "role": "analyst",
            "skills": {"data-analysis": 0.2},
            "required_skills": {"data-analysis": 0.8, "communication": 0.6},
        },
    )
    assert response.status_code == 201
    return response.json()


def create_course():
    response = client.post(
        "/api/v1/courses",
        json={
            "course_id": "analysis-foundations",
            "title": "Analysis Foundations",
            "skills": ["data-analysis"],
            "mandatory_for_all": True,
            "mandatory_for_roles": [],
        },
    )
    assert response.status_code == 201
    return response.json()


def test_health_and_courses_contract():
    assert client.get("/health").json() == {"status": "ok"}
    response = client.get("/api/v1/courses")
    assert response.status_code == 200
    assert response.json() == []


def test_pages_cors_preflight_allows_get_and_content_type():
    response = client.options(
        "/api/v1/courses",
        headers={
            "Origin": PAGES_ORIGIN,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "accept,content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == PAGES_ORIGIN
    assert "GET" in response.headers["access-control-allow-methods"]
    assert "content-type" in response.headers["access-control-allow-headers"].lower()


def test_learner_profile_gaps_recommendations_and_compliance():
    create_learner()
    create_course()

    profile = client.get("/api/v1/learners/learner-test")
    assert profile.status_code == 200
    assert profile.json()["learner_id"] == "learner-test"

    gaps = client.get("/api/v1/learners/learner-test/skill-gaps")
    assert gaps.status_code == 200
    assert {item["skill_id"]: item["gap"] for item in gaps.json()["gaps"]} == {
        "communication": 0.6,
        "data-analysis": 0.6,
    }

    recommendations = client.get(
        "/api/v1/learners/learner-test/recommendations?limit=3"
    )
    assert recommendations.status_code == 200
    assert recommendations.json()["consensus"]["selected_course"] == "analysis-foundations"

    compliance = client.get("/api/v1/learners/learner-test/compliance")
    assert compliance.status_code == 200
    assert compliance.json()["outstanding"] == ["analysis-foundations"]
    assert compliance.json()["completion_rate"] == 0.0


def test_course_completion_updates_profile_and_compliance():
    create_learner()
    create_course()
    event = {
        "event_id": "event-test-1",
        "learner_id": "learner-test",
        "event_type": "course_completed",
        "course_id": "analysis-foundations",
        "skill_scores": {"data-analysis": 0.75},
    }

    response = client.post("/api/v1/events", json=event)
    assert response.status_code == 200
    assert response.json()["duplicate"] is False

    repeated = client.post("/api/v1/events", json=event)
    assert repeated.status_code == 200
    assert repeated.json()["duplicate"] is True

    profile = client.get("/api/v1/learners/learner-test").json()
    assert profile["skills"]["data-analysis"] == 0.75
    assert profile["completed_courses"] == ["analysis-foundations"]
    assert client.get("/api/v1/learners/learner-test/compliance").json()["completion_rate"] == 1.0


def test_unknown_learner_returns_404():
    response = client.get("/api/v1/learners/does-not-exist/skill-gaps")
    assert response.status_code == 404


def test_biomedical_simulation_is_synthetic_and_marks_disagreement():
    scenarios = client.get("/api/v1/biomedical/scenarios")
    assert scenarios.status_code == 200
    assert scenarios.json()["research_only"] is True

    response = client.post(
        "/api/v1/biomedical/simulate",
        json={
            "scenario": "biosensor_diagnostics",
            "signals": {"optical_readout": 0.8, "electrochemical_readout": 0.3},
            "threshold": 0.5,
        },
    )
    assert response.status_code == 200
    assert response.json()["readout_consistency"] == "readouts_disagree"
    assert response.json()["manual_review_suggested"] is True
    assert response.json()["clinical_conclusion"] is None


def test_static_frontend_calls_live_learner_endpoints_and_labels_demo_metrics():
    from pathlib import Path

    html = Path(__file__).resolve().parents[1].joinpath(
        "rdashphdia-elp-visual-simulation.html"
    ).read_text(encoding="utf-8")
    for endpoint in (
        "'/health'",
        "'/api/v1/courses'",
        "+'/skill-gaps'",
        "+'/recommendations'",
        "+'/compliance'",
    ):
        assert endpoint in html
    assert "metrics above remain illustrative" in html
    assert "Promise.all(liveRequests.map" in html
    assert "function renderLiveRecommendations(data)" in html
    assert "LIVE API OUTPUT" in html
