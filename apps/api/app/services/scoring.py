from __future__ import annotations

from app.schemas import AnalyzeRecoveryRequest, ScoreResult
from app.services.safety import get_symptom_load


RUN_TYPE_LOADS = {
    "recovery": 2,
    "easy": 4,
    "steady": 8,
    "tempo": 12,
    "interval": 16,
    "long": 14,
    "race": 18,
}

RUN_TYPE_MODIFIER_LOADS = {
    "completed": 0,
    "progressive": 4,
    "fartlek": 3,
    "hills": 5,
    "pace_block": 5,
    "short_intervals": 2,
    "long_intervals": 4,
    "mixed_intervals": 4,
    "near_all_out": 5,
}

RECENT_TRAINING_LOADS = {
    "rest": 0,
    "easy_training": 2,
    "hard_training": 7,
    "race_or_very_hard": 10,
}

HIGH_STIMULUS_PLANS = {"intensity", "long", "race"}
LOW_STIMULUS_PLANS = {"easy", "recovery_easy"}


def get_base_load(distance_km: float) -> int:
    if distance_km < 3:
        return 3
    if distance_km <= 5:
        return 6
    if distance_km <= 10:
        return 10
    if distance_km <= 15:
        return 15
    return 20


def get_rpe_load(rpe: int) -> int:
    if rpe <= 2:
        return 0
    if rpe <= 4:
        return 5
    if rpe <= 6:
        return 10
    if rpe <= 8:
        return 15
    return 18


def get_adjusted_rpe_load(run_type_main: str, rpe: int) -> int:
    load = get_rpe_load(rpe)
    if run_type_main in {"tempo", "interval"} and rpe >= 8:
        load -= 2
    elif run_type_main == "race" and rpe >= 8:
        load -= 3
    elif run_type_main in {"recovery", "easy"} and rpe >= 7:
        load += 2
    return max(load, 0)


def get_duration_load(duration_min: float) -> int:
    if duration_min < 30:
        return 1
    if duration_min <= 60:
        return 4
    if duration_min <= 90:
        return 7
    if duration_min <= 120:
        return 11
    return 14


def get_session_load(rpe: int, duration_min: float) -> float:
    return round(rpe * duration_min, 1)


def get_run_type_modifier_load(modifiers: list[str]) -> int:
    return min(sum(RUN_TYPE_MODIFIER_LOADS.get(modifier, 0) for modifier in modifiers), 8)


def get_recent_training_load(past_48h_training: str) -> int:
    return RECENT_TRAINING_LOADS.get(past_48h_training, 0)


def get_heart_rate_load(avg_hr: int | None, max_hr: int | None) -> int:
    if avg_hr is None and max_hr is None:
        return 0

    avg_load = 0
    if avg_hr is not None:
        if avg_hr >= 175:
            avg_load = 10
        elif avg_hr >= 165:
            avg_load = 8
        elif avg_hr >= 155:
            avg_load = 4

    max_load = 0
    if max_hr is not None:
        if max_hr >= 195:
            max_load = 10
        elif max_hr >= 185:
            max_load = 8
        elif max_hr >= 175:
            max_load = 4

    return max(avg_load, max_load)


def get_sleep_penalty(sleep_hours: float) -> int:
    if sleep_hours >= 7:
        return 0
    if sleep_hours >= 6:
        return 6
    if sleep_hours >= 5:
        return 10
    return 15


def get_time_penalty(run_time_period: str, rpe: int) -> int:
    if run_time_period != "night":
        return 0
    if rpe >= 7:
        return 6
    return 4


def get_tomorrow_conflict_load(preliminary_score: int, tomorrow_plan: str | None) -> int:
    plan = tomorrow_plan or "unknown"
    if plan in {"rest", "unknown"}:
        return 0
    if plan in LOW_STIMULUS_PLANS:
        if preliminary_score >= 81:
            return 4
        if preliminary_score >= 61:
            return 2
        return 0
    if plan == "strength_cross":
        if preliminary_score >= 81:
            return 5
        if preliminary_score >= 61:
            return 3
        return 0
    if plan in HIGH_STIMULUS_PLANS:
        if preliminary_score >= 81:
            return 8
        if preliminary_score >= 61:
            return 6
        if preliminary_score >= 31:
            return 3
    return 0


def level_for_score(score: int) -> str:
    if score <= 30:
        return "轻度恢复"
    if score <= 60:
        return "中度恢复"
    if score <= 80:
        return "重点恢复"
    return "高负荷提醒"


def calculate_score(run_input: AnalyzeRecoveryRequest) -> ScoreResult:
    run_type_main = run_input.run_type_main or run_input.run_type or "easy"
    duration_load = get_duration_load(run_input.duration_min)
    session_load = get_session_load(run_input.rpe, run_input.duration_min)
    component_scores = {
        "base_load": get_base_load(run_input.distance_km),
        "duration_load": duration_load,
        "run_type": RUN_TYPE_LOADS[run_type_main],
        "run_modifier": get_run_type_modifier_load(run_input.run_type_modifier),
        "rpe": get_adjusted_rpe_load(run_type_main, run_input.rpe),
        "heart_rate": get_heart_rate_load(run_input.avg_hr, run_input.max_hr),
        "sleep": get_sleep_penalty(run_input.sleep_hours),
        "fatigue": round(run_input.fatigue_level * 1.2),
        "soreness": round(run_input.soreness_level * 1.0),
        "recent_training": get_recent_training_load(run_input.past_48h_training),
        "symptoms": get_symptom_load(run_input.symptoms),
        "time": get_time_penalty(run_input.run_time_period, run_input.rpe),
        "tomorrow_conflict": 0,
    }

    preliminary = sum(component_scores.values())
    component_scores["tomorrow_conflict"] = get_tomorrow_conflict_load(
        preliminary,
        run_input.tomorrow_plan,
    )

    score = min(max(round(sum(component_scores.values())), 0), 100)
    return ScoreResult(
        score=score,
        level=level_for_score(score),
        component_scores=component_scores,
        derived_metrics={
            "duration_load": float(duration_load),
            "session_load": session_load,
        },
    )
