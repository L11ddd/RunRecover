from __future__ import annotations

from typing import List

from app.schemas import AnalyzeRecoveryRequest, Reason, ScoreResult


def build_reasons(run_input: AnalyzeRecoveryRequest, score_result: ScoreResult) -> List[Reason]:
    component_scores = score_result.component_scores
    candidates: list[Reason] = []

    rpe_load = component_scores["rpe"]
    if rpe_load >= 10:
        candidates.append(
            Reason(
                factor="RPE",
                impact=rpe_load,
                text=(
                    f"本次 RPE 为 {run_input.rpe}/10，主观用力感较强，"
                    "建议提高跑后恢复优先级。"
                ),
            )
        )

    sleep_load = component_scores["sleep"]
    if sleep_load > 0:
        candidates.append(
            Reason(
                factor="睡眠",
                impact=sleep_load,
                text=(
                    f"昨晚睡眠约 {run_input.sleep_hours:g} 小时，"
                    "恢复条件偏弱，建议优先补足睡眠。"
                ),
            )
        )

    run_type_load = component_scores["run_type"]
    candidates.append(
        Reason(
            factor="跑步类型",
            impact=run_type_load,
            text=f"本次训练类型为 {run_type_label(run_input.run_type)}，会增加本次恢复压力。",
        )
    )

    base_load = component_scores["base_load"]
    if base_load >= 10:
        candidates.append(
            Reason(
                factor="跑量",
                impact=base_load,
                text=f"本次跑步距离为 {run_input.distance_km:g} km，基础跑量负荷需要纳入恢复安排。",
            )
        )

    fatigue_load = component_scores["fatigue"]
    if run_input.fatigue_level >= 5:
        candidates.append(
            Reason(
                factor="疲劳",
                impact=fatigue_load,
                text=f"当前疲劳为 {run_input.fatigue_level}/10，说明跑后状态需要更谨慎恢复。",
            )
        )

    soreness_load = component_scores["soreness"]
    if run_input.soreness_level >= 5:
        candidates.append(
            Reason(
                factor="酸痛",
                impact=soreness_load,
                text=f"腿部酸痛为 {run_input.soreness_level}/10，明日训练建议适当保守。",
            )
        )

    heart_rate_load = component_scores["heart_rate"]
    if heart_rate_load > 0:
        candidates.append(
            Reason(
                factor="心率",
                impact=heart_rate_load,
                text="本次心率输入显示强度偏高，可作为 RPE 之外的辅助判断。",
            )
        )

    time_load = component_scores["time"]
    if time_load > 0:
        candidates.append(
            Reason(
                factor="夜跑",
                impact=time_load,
                text="夜跑可能影响睡眠准备，建议把冷身和睡前放松安排得更温和。",
            )
        )

    conflict_load = component_scores["tomorrow_conflict"]
    if conflict_load > 0:
        candidates.append(
            Reason(
                factor="明日计划",
                impact=conflict_load,
                text="当前恢复压力较高，且明日仍有强度或长距离计划，建议降低训练强度。",
            )
        )

    sorted_reasons = sorted(candidates, key=lambda reason: reason.impact, reverse=True)
    selected = sorted_reasons[:5]

    conflict_reason = next(
        (reason for reason in sorted_reasons if reason.factor == "明日计划"), None
    )
    if conflict_reason is not None and all(reason.factor != "明日计划" for reason in selected):
        selected[-1] = conflict_reason
        selected = sorted(selected, key=lambda reason: reason.impact, reverse=True)

    return selected


def run_type_label(run_type: str) -> str:
    labels = {
        "easy": "轻松跑",
        "tempo": "节奏跑",
        "interval": "间歇跑",
        "long": "长距离跑",
        "race": "比赛",
    }
    return labels.get(run_type, run_type)
