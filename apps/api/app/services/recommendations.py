from __future__ import annotations

from app.schemas import (
    AdviceItem,
    AnalyzeRecoveryRequest,
    RecoveryAdvice,
    ScoreResult,
    TimelineItem,
)


SAFETY_NOTE = (
    "RunRecover 提供的是一般运动恢复参考，不构成医疗诊断或治疗建议。"
    "如出现胸闷、头晕、呼吸困难、持续疼痛或疼痛影响日常活动，请及时咨询医生或专业运动康复人员。"
)


def build_template_recommendation(
    run_input: AnalyzeRecoveryRequest,
    score_result: ScoreResult,
    safety_flags: list[str],
) -> RecoveryAdvice:
    conservative = score_result.score >= 61 or bool(safety_flags)
    high_load = score_result.score >= 81 or bool(safety_flags)

    summary = build_summary(run_input, score_result, safety_flags)
    diet = build_diet_advice(run_input, high_load)
    hydration = build_hydration_advice(run_input, high_load)
    sleep = build_sleep_advice(run_input, conservative)
    relaxation = build_relaxation_advice(run_input, high_load)
    tomorrow = build_tomorrow_advice(run_input, score_result, safety_flags)
    timeline = build_timeline(run_input, score_result, safety_flags)

    return RecoveryAdvice(
        summary=summary,
        diet=diet,
        hydration=hydration,
        sleep=sleep,
        relaxation=relaxation,
        tomorrow=tomorrow,
        timeline=timeline,
        safety_note=SAFETY_NOTE,
    )


def build_summary(
    run_input: AnalyzeRecoveryRequest,
    score_result: ScoreResult,
    safety_flags: list[str],
) -> str:
    if safety_flags:
        return "当前存在需要保守处理的身体信号，建议先把安全和恢复放在训练目标前面。"
    if score_result.score >= 81:
        return "今天恢复压力很高，主要与较高运动负荷、RPE 或身体状态有关，明日应避免连续高强度。"
    if score_result.score >= 61:
        return "今天恢复压力较高，建议把饮食、补水、睡眠和明日训练调整作为优先事项。"
    if score_result.score >= 31:
        return "今天恢复压力中等，正常恢复即可，但不建议在疲劳未缓解前叠加强度训练。"
    return "今天恢复压力较低，保持正常补水、饮食和睡眠，明日可按状态安排轻松活动。"


def build_diet_advice(run_input: AnalyzeRecoveryRequest, high_load: bool) -> AdviceItem:
    if run_input.diet_preference == "fat_loss":
        content = "跑后不要用极端节食抵消训练。安排一餐有主食、优质蛋白和蔬菜的恢复餐，份量保持清爽即可。"
    elif run_input.diet_preference == "vegetarian":
        content = "跑后 1-2 小时内补充主食、豆制品或蛋奶类蛋白，再搭配蔬菜，帮助恢复能量和肌肉状态。"
    elif run_input.diet_preference == "canteen":
        content = "食堂场景可选米饭或面食、鸡蛋/鱼肉/豆腐和蔬菜，避免只喝饮料或只吃零食。"
    elif run_input.diet_preference == "takeout":
        content = "外卖优先选主食、蛋白质和蔬菜组合，少选重油重辣，避免影响睡眠和胃肠负担。"
    elif run_input.diet_preference == "light_night" or run_input.run_time_period == "night":
        content = "夜跑后如果接近睡觉，选择温和易消化的小餐，如酸奶、香蕉、鸡蛋或少量主食。"
    else:
        content = "跑后 1-2 小时内安排包含主食、蛋白质和蔬菜的恢复餐，不需要追求精确克数。"

    if high_load:
        content += " 今天负荷偏高，不建议跑后长时间空腹。"

    return AdviceItem(title="饮食建议", content=content)


def build_hydration_advice(run_input: AnalyzeRecoveryRequest, high_load: bool) -> AdviceItem:
    if high_load or run_input.duration_min >= 75:
        content = "接下来 2-3 小时少量多次补水；如果出汗多，可搭配正常餐食补充电解质。"
    else:
        content = "跑后先少量补水，再根据口渴和尿色在接下来几小时继续补充，不需要一次喝太多。"
    return AdviceItem(title="补水建议", content=content)


def build_sleep_advice(run_input: AnalyzeRecoveryRequest, conservative: bool) -> AdviceItem:
    if run_input.run_time_period == "night":
        content = "夜跑后减少屏幕刺激和高强度拉伸，给身体 20-30 分钟安静降温，尽量保证 7 小时以上睡眠。"
    elif run_input.sleep_hours < 6:
        content = "昨晚睡眠不足，今晚优先提前入睡。恢复压力没有下降前，不建议用高强度训练硬顶。"
    else:
        content = "保持规律睡眠即可。若晚上仍感觉疲劳，优先提前休息而不是追加训练。"

    if conservative and run_input.sleep_hours < 7:
        content += " 睡眠是今天最值得补上的恢复资源。"

    return AdviceItem(title="睡眠建议", content=content)


def build_relaxation_advice(run_input: AnalyzeRecoveryRequest, high_load: bool) -> AdviceItem:
    if high_load or run_input.soreness_level >= 7:
        content = "做 8-10 分钟慢走、呼吸放松或轻柔活动即可，避免用强刺激拉伸处理明显酸痛。"
    else:
        content = "安排 8-10 分钟低强度拉伸、慢走或泡沫轴轻放松，让呼吸和心率逐步降下来。"
    return AdviceItem(title="放松建议", content=content)


def build_tomorrow_advice(
    run_input: AnalyzeRecoveryRequest,
    score_result: ScoreResult,
    safety_flags: list[str],
) -> AdviceItem:
    if safety_flags:
        content = "明日先暂停跑步或下肢高强度训练，观察不适变化；如果症状持续或影响日常活动，请咨询专业人士。"
    elif score_result.score >= 81:
        content = "明日建议休息、散步或非常轻松的活动，不安排间歇、节奏跑或长距离。"
    elif score_result.score >= 61:
        content = "明日建议休息或低强度活动。如果原计划是强度课或长距离，建议取消或降级为轻松跑。"
    elif score_result.score >= 31:
        content = "明日可根据状态安排轻松活动，暂时避免连续高强度。"
    else:
        content = "明日可按原计划进行轻松训练；如果醒来仍疲劳，则主动降低强度。"

    return AdviceItem(title="明日安排", content=content)


def build_timeline(
    run_input: AnalyzeRecoveryRequest,
    score_result: ScoreResult,
    safety_flags: list[str],
) -> list[TimelineItem]:
    if safety_flags:
        first_action = "停止追加训练，先补水、坐下休息，观察异常症状是否缓解。"
    else:
        first_action = "慢走冷身，少量补水，让呼吸和心率逐步降下来。"

    meal_action = "安排包含主食、蛋白质和蔬菜的恢复餐。"
    if run_input.diet_preference == "fat_loss":
        meal_action = "安排清爽但完整的恢复餐，不用极端节食。"
    elif run_input.run_time_period == "night":
        meal_action = "如果接近睡前，选择温和易消化的小餐并少量补水。"

    tomorrow_action = build_tomorrow_advice(run_input, score_result, safety_flags).content

    return [
        TimelineItem(time="跑后 0-15 分钟", action=first_action),
        TimelineItem(time="跑后 15-45 分钟", action="换下湿衣物，继续少量多次补水，避免马上洗过热的澡。"),
        TimelineItem(time="跑后 1-2 小时", action=meal_action),
        TimelineItem(time="睡前", action="做轻柔放松，减少屏幕刺激，把睡眠作为今天的重点恢复动作。"),
        TimelineItem(time="明早", action="起床后观察疲劳、酸痛和精神状态，再决定是否降级训练。"),
        TimelineItem(time="明日训练", action=tomorrow_action),
    ]
