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
    assert body["score"] == 78
    assert body["level"] == "重点恢复"
    assert body["component_scores"]["rpe"] == 13
    assert body["component_scores"]["duration_load"] == 4
    assert body["derived_metrics"]["session_load"] == 384
    assert len(body["reasons"]) >= 3
    assert len(body["timeline"]) >= 5
    assert body["advice"]["diet"]["title"] == "饮食建议"
    assert body["recommendation_meta"]["llm_provider"] == "template"
    assert body["recommendation_meta"]["advice_conservativeness"] == "balanced"
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


def test_new_training_fields_are_accepted(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        response = client.post(
            "/api/recovery/analyze",
            json=valid_payload(
                run_type=None,
                run_type_main="interval",
                run_type_modifier=["hills", "long_intervals"],
                past_48h_training="hard_training",
            ),
        )

    body = response.json()

    assert response.status_code == 200
    assert body["component_scores"]["run_modifier"] == 8
    assert body["component_scores"]["recent_training"] == 7
    assert any(reason["factor"] == "训练修饰" for reason in body["reasons"])


def test_user_level_calibrates_advice_without_changing_score(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        beginner_response = client.post(
            "/api/recovery/analyze",
            json=valid_payload(user_level="beginner"),
        )
        advanced_response = client.post(
            "/api/recovery/analyze",
            json=valid_payload(user_level="advanced"),
        )

    beginner_body = beginner_response.json()
    advanced_body = advanced_response.json()

    assert beginner_response.status_code == 200
    assert advanced_response.status_code == 200
    assert beginner_body["score"] == advanced_body["score"]
    assert beginner_body["recommendation_meta"]["advice_conservativeness"] == "conservative"
    assert advanced_body["recommendation_meta"]["advice_conservativeness"] == "performance_adjusted"
    assert "取消强度" in beginner_body["advice"]["tomorrow"]["content"]
    assert "Z1/Z2" in advanced_body["advice"]["tomorrow"]["content"]


def test_safety_flags_override_advanced_profile(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        response = client.post(
            "/api/recovery/analyze",
            json=valid_payload(
                user_level="advanced",
                symptoms=["chest_pain", "pain_affects_walking"],
            ),
        )

    body = response.json()

    assert response.status_code == 200
    assert body["safety_flags"]
    assert body["recommendation_meta"]["advice_conservativeness"] == "safety_first"
    assert "暂停跑步" in body["advice"]["tomorrow"]["content"]


def test_feedback_and_history_endpoints(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        analyze_response = client.post("/api/recovery/analyze", json=valid_payload())
        recovery_id = analyze_response.json()["recovery_id"]

        feedback_response = client.post(
            f"/api/recovery/{recovery_id}/feedback",
            json={
                "helpfulness_rating": "helpful",
                "next_day_status": "recovered",
                "followed_advice": "partial",
            },
        )
        history_response = client.get("/api/recovery/history?limit=7")

    assert feedback_response.status_code == 200
    assert feedback_response.json()["recovery_id"] == recovery_id
    assert history_response.status_code == 200
    assert history_response.json()[0]["recovery_id"] == recovery_id
