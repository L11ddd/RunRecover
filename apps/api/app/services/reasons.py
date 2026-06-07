from __future__ import annotations

from typing import List

from app.schemas import AnalyzeRecoveryRequest, Reason, ScoreResult


def build_reasons(run_input: AnalyzeRecoveryRequest, score_result: ScoreResult) -> List[Reason]:
    component_scores = score_result.component_scores
    candidates: list[Reason] = []
    run_type_main = run_input.run_type_main or run_input.run_type or "easy"
    user_level = run_input.user_level

    rpe_load = component_scores["rpe"]
    if rpe_load >= 10:
        rpe_context = "主观用力感较强，建议提高跑后恢复优先级。"
        if run_type_main in {"recovery", "easy"} and run_input.rpe >= 7:
            rpe_context = "轻量训练却感觉明显吃力，可能提示当前恢复能力偏弱。"
        elif user_level == "beginner":
            rpe_context = "主观用力感已经不低，先按身体反馈做保守恢复。"
        elif user_level == "advanced":
            rpe_context = "这代表本次训练刺激较明确，需要通过降载、补能和睡眠来吸收训练。"
        candidates.append(
            Reason(
                factor="RPE",
                impact=rpe_load,
                text=f"本次 RPE 为 {run_input.rpe}/10，{rpe_context}",
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
            text=build_run_type_reason_text(run_type_main, user_level),
        )
    )

    modifier_load = component_scores.get("run_modifier", 0)
    if modifier_load > 0:
        modifier_text = "、".join(run_type_modifier_label(modifier) for modifier in run_input.run_type_modifier)
        candidates.append(
            Reason(
                factor="训练修饰",
                impact=modifier_load,
                text=f"本次训练包含 {modifier_text}，会让恢复侧重点更偏向肌肉和神经系统放松。",
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

    duration_load = component_scores.get("duration_load", 0)
    if duration_load >= 7:
        candidates.append(
            Reason(
                factor="时长",
                impact=duration_load,
                text=f"本次持续运动约 {run_input.duration_min:g} 分钟，训练时长本身会增加恢复压力。",
            )
        )

    fatigue_load = component_scores["fatigue"]
    if run_input.fatigue_level >= 5:
        fatigue_text = f"当前疲劳为 {run_input.fatigue_level}/10，说明跑后状态需要更谨慎恢复。"
        if user_level == "beginner":
            fatigue_text = f"当前疲劳为 {run_input.fatigue_level}/10，建议先把休息做好，不用急着补训练。"
        elif user_level == "advanced":
            fatigue_text = f"当前疲劳为 {run_input.fatigue_level}/10，提示后续训练应做负荷微调。"
        candidates.append(
            Reason(
                factor="疲劳",
                impact=fatigue_load,
                text=fatigue_text,
            )
        )

    soreness_load = component_scores["soreness"]
    if run_input.soreness_level >= 5:
        soreness_text = f"腿部酸痛为 {run_input.soreness_level}/10，明日训练建议适当保守。"
        if user_level == "beginner":
            soreness_text = f"腿部酸痛为 {run_input.soreness_level}/10，明日先避免勉强跑快或跑远。"
        elif user_level == "advanced":
            soreness_text = f"腿部酸痛为 {run_input.soreness_level}/10，建议降低下肢冲击和神经肌肉刺激。"
        candidates.append(
            Reason(
                factor="酸痛",
                impact=soreness_load,
                text=soreness_text,
            )
        )

    recent_training_load = component_scores.get("recent_training", 0)
    if recent_training_load > 0:
        candidates.append(
            Reason(
                factor="近 48 小时",
                impact=recent_training_load,
                text=(
                    f"近 48 小时状态为 {past_48h_label(run_input.past_48h_training)}，"
                    "需要考虑连续负荷叠加。"
                ),
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
                text=(
                    f"当前恢复压力与明日计划“{tomorrow_plan_label(run_input.tomorrow_plan or 'unknown')}”存在冲突，"
                    "建议降低训练刺激或改为恢复安排。"
                ),
            )
        )

    sorted_reasons = sorted(candidates, key=lambda reason: reason.impact, reverse=True)
    selected = sorted_reasons[:5]
    for factor in ["明日计划", "近 48 小时", "训练修饰"]:
        selected = include_reason_factor(selected, sorted_reasons, factor)

    return selected


def include_reason_factor(
    selected: list[Reason],
    sorted_reasons: list[Reason],
    factor: str,
) -> list[Reason]:
    if any(reason.factor == factor for reason in selected):
        return selected

    reason_to_include = next(
        (reason for reason in sorted_reasons if reason.factor == factor),
        None,
    )
    if reason_to_include is None:
        return selected

    protected_factors = {"明日计划", "近 48 小时", "训练修饰"}
    if len(selected) < 5:
        selected.append(reason_to_include)
    else:
        replaceable_indexes = [
            index
            for index, reason in enumerate(selected)
            if reason.factor not in protected_factors
        ]
        if not replaceable_indexes:
            replaceable_indexes = list(range(len(selected)))
        replace_index = min(
            replaceable_indexes,
            key=lambda index: selected[index].impact,
        )
        selected[replace_index] = reason_to_include

    return sorted(selected, key=lambda reason: reason.impact, reverse=True)


def run_type_label(run_type: str) -> str:
    labels = {
        "recovery": "恢复跑",
        "easy": "轻松跑",
        "steady": "稳态跑",
        "tempo": "节奏跑",
        "interval": "间歇跑",
        "long": "长距离跑",
        "race": "比赛",
    }
    return labels.get(run_type, run_type)


def build_run_type_reason_text(run_type_main: str, user_level: str) -> str:
    label = run_type_label(run_type_main)
    if user_level == "beginner":
        return f"本次训练类型为 {label}，建议用更简单保守的恢复安排承接这次负荷。"
    if user_level == "advanced":
        return f"本次训练类型为 {label}，可视为训练刺激来源之一，明日安排应围绕降载和吸收训练调整。"
    return f"本次训练类型为 {label}，会增加本次恢复压力。"


def run_type_modifier_label(modifier: str) -> str:
    labels = {
        "completed": "连续完成",
        "progressive": "渐进加速",
        "fartlek": "变速/Fartlek",
        "hills": "坡跑",
        "pace_block": "目标配速段",
        "short_intervals": "短间歇",
        "long_intervals": "长间歇",
        "mixed_intervals": "混合间歇",
        "near_all_out": "接近全力",
    }
    return labels.get(modifier, modifier)


def tomorrow_plan_label(plan: str) -> str:
    labels = {
        "rest": "休息",
        "easy": "轻松跑",
        "recovery_easy": "恢复/轻松跑",
        "intensity": "强度跑",
        "long": "长距离",
        "strength_cross": "力量/交叉训练",
        "race": "比赛",
        "unknown": "未确定",
    }
    return labels.get(plan, plan)


def past_48h_label(value: str) -> str:
    labels = {
        "rest": "基本休息",
        "easy_training": "轻松训练",
        "hard_training": "强度训练",
        "race_or_very_hard": "比赛或极高负荷训练",
    }
    return labels.get(value, value)
