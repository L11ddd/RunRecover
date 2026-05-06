from __future__ import annotations

from app.schemas import AnalyzeRecoveryRequest, ScoreResult


RUN_TYPE_LOADS = {
    "easy": 4,
    "tempo": 12,
    "interval": 16,
    "long": 14,
    "race": 18,
}


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


def level_for_score(score: int) -> str:
    if score <= 30:
        return "轻度恢复"
    if score <= 60:
        return "中度恢复"
    if score <= 80:
        return "重点恢复"
    return "高负荷提醒"


def calculate_score(run_input: AnalyzeRecoveryRequest) -> ScoreResult:
    component_scores = {
        "base_load": get_base_load(run_input.distance_km),
        "run_type": RUN_TYPE_LOADS[run_input.run_type],
        "rpe": get_rpe_load(run_input.rpe),
        "heart_rate": get_heart_rate_load(run_input.avg_hr, run_input.max_hr),
        "sleep": get_sleep_penalty(run_input.sleep_hours),
        "fatigue": round(run_input.fatigue_level * 1.2),
        "soreness": round(run_input.soreness_level * 1.0),
        "time": get_time_penalty(run_input.run_time_period, run_input.rpe),
        "tomorrow_conflict": 0,
    }

    preliminary = sum(component_scores.values())
    if preliminary >= 60 and run_input.tomorrow_plan in {"intensity", "long"}:
        component_scores["tomorrow_conflict"] = 5

    score = min(max(round(sum(component_scores.values())), 0), 100)
    return ScoreResult(
        score=score,
        level=level_for_score(score),
        component_scores=component_scores,
    )
