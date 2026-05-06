from fastapi.testclient import TestClient

from app.main import app


def make_client(tmp_path, monkeypatch):
    monkeypatch.setenv("RUNRECOVER_DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    return TestClient(app)


def valid_payload(**overrides):
    payload = {
        "distance_km": 8.0,
        "duration_min": 48,
        "run_type": "tempo",
        "run_time_period": "night",
        "rpe": 8,
        "sleep_hours": 5.8,
        "fatigue_level": 7,
        "soreness_level": 5,
        "avg_hr": 156,
        "diet_preference": "canteen",
        "tomorrow_plan": "intensity",
        "symptoms": [],
    }
    payload.update(overrides)
    return payload


def test_health(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "runrecover-api"}


def test_analyze_recovery_returns_complete_response(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        response = client.post("/api/recovery/analyze", json=valid_payload())

    body = response.json()

    assert response.status_code == 200
    assert body["recovery_id"] >= 1
    assert body["score"] == 75
    assert body["level"] == "重点恢复"
    assert body["component_scores"]["rpe"] == 15
    assert len(body["reasons"]) >= 3
    assert len(body["timeline"]) >= 5
    assert body["advice"]["diet"]["title"] == "饮食建议"
    assert body["safety_flags"] == []


def test_invalid_rpe_returns_422(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        response = client.post("/api/recovery/analyze", json=valid_payload(rpe=11))

    assert response.status_code == 422


def test_negative_distance_returns_422(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        response = client.post("/api/recovery/analyze", json=valid_payload(distance_km=-1))

    assert response.status_code == 422


def test_safety_response_places_flags(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        response = client.post(
            "/api/recovery/analyze",
            json=valid_payload(
                rpe=7,
                symptoms=["joint_pain", "pain_affects_walking"],
                avg_hr=None,
            ),
        )

    body = response.json()

    assert response.status_code == 200
    assert body["safety_flags"]
    assert "医疗诊断" in body["advice"]["safety_note"]
