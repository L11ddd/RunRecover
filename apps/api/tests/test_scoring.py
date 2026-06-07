import pytest

from app.schemas import AnalyzeRecoveryRequest
from app.services.reasons import build_reasons
from app.services.safety import evaluate_safety
from app.services.scoring import calculate_score, get_duration_load, get_rpe_load


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


@pytest.mark.parametrize(
    ("duration_min", "expected"),
    [
        (25, 1),
        (45, 4),
        (75, 7),
        (105, 11),
        (130, 14),
    ],
)
def test_duration_load(duration_min, expected):
    assert get_duration_load(duration_min) == expected


def test_easy_recovery_case_is_light():
    run_input = make_input(distance_km=5, rpe=3, sleep_hours=8, fatigue_level=2, soreness_level=2)

    result = calculate_score(run_input)

    assert 0 <= result.score <= 100
    assert result.level == "轻度恢复"
    assert result.component_scores["rpe"] == 5
    assert result.component_scores["duration_load"] == 4


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
    assert result.component_scores["rpe"] == 13
    assert result.component_scores["tomorrow_conflict"] == 6
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


def test_modifiers_and_recent_training_affect_reasons():
    run_input = make_input(
        duration_min=75,
        run_type=None,
        run_type_main="interval",
        run_type_modifier=["long_intervals", "hills"],
        rpe=8,
        past_48h_training="hard_training",
        tomorrow_plan="intensity",
    )

    result = calculate_score(run_input)
    reasons = build_reasons(run_input, result)
    factors = {reason.factor for reason in reasons}

    assert result.component_scores["duration_load"] == 7
    assert result.component_scores["run_modifier"] == 8
    assert result.component_scores["recent_training"] == 7
    assert "训练修饰" in factors
    assert "近 48 小时" in factors


def test_safety_symptom_triggers_flag():
    run_input = make_input(
        rpe=7,
        soreness_level=6,
        symptoms=["joint_pain", "pain_affects_walking"],
    )

    flags = evaluate_safety(run_input)

    assert len(flags) >= 2
    assert any("停止跑步" in flag for flag in flags)


def test_new_symptoms_affect_score_and_reasons():
    run_input = make_input(
        symptoms=["palpitations", "one_sided_calf_pain", "dark_urine"],
    )

    result = calculate_score(run_input)
    reasons = build_reasons(run_input, result)

    assert result.component_scores["symptoms"] == 18
    assert any(reason.factor == "异常信号" for reason in reasons)
    assert any("异常心悸" in reason.text for reason in reasons)


def test_new_symptoms_trigger_safety_flags():
    run_input = make_input(
        symptoms=["fainting", "nausea_vomiting", "fever_infection"],
    )

    flags = evaluate_safety(run_input)

    assert len(flags) >= 3
    assert any("昏厥" in flag for flag in flags)
    assert any("发热" in flag for flag in flags)


def test_recent_hard_training_with_tomorrow_intensity_triggers_safety_flag():
    run_input = make_input(
        rpe=8,
        past_48h_training="hard_training",
        tomorrow_plan="intensity",
    )

    flags = evaluate_safety(run_input)

    assert any("近 48 小时" in flag for flag in flags)


def test_user_profile_can_infer_user_level_when_not_provided():
    beginner_input = make_input(
        user_profile={
            "running_years": 0.2,
            "weekly_runs": 1,
            "weekly_mileage_km": 8,
        }
    )
    advanced_input = make_input(
        user_profile={
            "running_years": 3,
            "weekly_runs": 5,
            "weekly_mileage_km": 45,
            "race_goal": True,
        }
    )
    explicit_regular = make_input(
        user_level="regular",
        user_profile={
            "running_years": 3,
            "weekly_runs": 5,
            "weekly_mileage_km": 45,
        },
    )

    assert beginner_input.user_level == "beginner"
    assert advanced_input.user_level == "advanced"
    assert explicit_regular.user_level == "regular"


def test_user_level_does_not_change_score():
    beginner_input = make_input(user_level="beginner")
    advanced_input = make_input(user_level="advanced")

    assert calculate_score(beginner_input).score == calculate_score(advanced_input).score
