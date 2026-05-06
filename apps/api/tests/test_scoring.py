import pytest

from app.schemas import AnalyzeRecoveryRequest
from app.services.reasons import build_reasons
from app.services.safety import evaluate_safety
from app.services.scoring import calculate_score, get_rpe_load


def make_input(**overrides):
    data = {
        "distance_km": 5,
        "duration_min": 32,
        "run_type": "easy",
        "run_time_period": "evening",
        "rpe": 3,
        "sleep_hours": 8,
        "fatigue_level": 2,
        "soreness_level": 2,
        "tomorrow_plan": "easy",
        "symptoms": [],
    }
    data.update(overrides)
    return AnalyzeRecoveryRequest(**data)


@pytest.mark.parametrize(
    ("rpe", "expected"),
    [
        (1, 0),
        (5, 10),
        (8, 15),
        (10, 18),
    ],
)
def test_rpe_load(rpe, expected):
    assert get_rpe_load(rpe) == expected


def test_easy_recovery_case_is_light():
    run_input = make_input(distance_km=5, rpe=3, sleep_hours=8, fatigue_level=2, soreness_level=2)

    result = calculate_score(run_input)

    assert 0 <= result.score <= 100
    assert result.level == "轻度恢复"
    assert result.component_scores["rpe"] == 5


def test_high_intensity_night_run_includes_rpe_sleep_and_conflict_reasons():
    run_input = make_input(
        distance_km=8,
        duration_min=48,
        run_type="tempo",
        run_time_period="night",
        rpe=8,
        sleep_hours=5.8,
        fatigue_level=7,
        soreness_level=5,
        avg_hr=156,
        tomorrow_plan="intensity",
    )

    result = calculate_score(run_input)
    reasons = build_reasons(run_input, result)
    factors = {reason.factor for reason in reasons}

    assert result.level == "重点恢复"
    assert result.component_scores["rpe"] == 15
    assert result.component_scores["tomorrow_conflict"] == 5
    assert {"RPE", "睡眠", "明日计划"}.issubset(factors)


def test_long_high_rpe_case_is_high_load():
    run_input = make_input(
        distance_km=16,
        duration_min=105,
        run_type="long",
        rpe=9,
        sleep_hours=5.8,
        fatigue_level=8,
        soreness_level=7,
        tomorrow_plan="long",
    )

    result = calculate_score(run_input)

    assert result.level == "高负荷提醒"
    assert result.score <= 100


def test_no_device_case_does_not_emit_heart_rate_reason():
    run_input = make_input(distance_km=6, rpe=6, fatigue_level=5, avg_hr=None, max_hr=None)
    result = calculate_score(run_input)
    reasons = build_reasons(run_input, result)

    assert result.level == "中度恢复"
    assert all(reason.factor != "心率" for reason in reasons)


def test_safety_symptom_triggers_flag():
    run_input = make_input(
        rpe=7,
        soreness_level=6,
        symptoms=["joint_pain", "pain_affects_walking"],
    )

    flags = evaluate_safety(run_input)

    assert len(flags) >= 2
    assert any("停止跑步" in flag for flag in flags)
