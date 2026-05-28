from __future__ import annotations

from app.schemas import (
    AdviceConservativeness,
    AdviceItem,
    AnalyzeRecoveryRequest,
    RecoveryAdvice,
    Reason,
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
    reasons: list[Reason] | None = None,
) -> RecoveryAdvice:
    conservative = (
        score_result.score >= 61
        or bool(safety_flags)
        or (run_input.user_level == "beginner" and score_result.score >= 31)
    )
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


def get_advice_conservativeness(
    run_input: AnalyzeRecoveryRequest,
    score_result: ScoreResult,
    safety_flags: list[str],
) -> AdviceConservativeness:
    if safety_flags:
        return "safety_first"
    if run_input.user_level == "beginner":
        return "conservative"
    if run_input.user_level == "advanced":
        return "performance_adjusted"
    return "balanced"


def validate_recommendation_content(
    advice: RecoveryAdvice,
    run_input: AnalyzeRecoveryRequest,
    score_result: ScoreResult,
    safety_flags: list[str],
) -> tuple[bool, list[str]]:
    issues: list[str] = []
    joined = " ".join(
        [
            advice.summary,
            advice.diet.content,
            advice.hydration.content,
            advice.sleep.content,
            advice.relaxation.content,
            advice.tomorrow.content,
            " ".join(item.action for item in advice.timeline),
        ]
    )

    unsafe_phrases = ["继续高强度", "坚持原计划", "正常冲量", "照常冲量", "按原计划强度"]
    if safety_flags and any(phrase in joined for phrase in unsafe_phrases):
        issues.append("safety_flags 场景中出现鼓励继续高刺激训练的表述")

    conservative_terms = ["保守", "暂停", "避免", "降低", "降级", "休息", "观察"]
    safety_text = f"{advice.summary} {advice.tomorrow.content}"
    if safety_flags and not any(term in safety_text for term in conservative_terms):
        issues.append("safety_flags 场景的 summary/tomorrow 未体现保守处理")

    if "pain_affects_walking" in run_input.symptoms:
        risky_tomorrow_terms = ["轻松跑", "恢复跑", "跑步训练", "继续跑", "推荐跑步", "跳跃", "强拉伸"]
        if any(term in advice.tomorrow.content for term in risky_tomorrow_terms):
            issues.append("疼痛影响走路时，明日建议不得推荐跑步、跳跃或强拉伸")

    hard_plan = (run_input.tomorrow_plan or "unknown") in {"intensity", "long", "race"}
    if run_input.sleep_hours < 5 and hard_plan:
        if not any(term in advice.tomorrow.content for term in ["取消", "降低", "降级", "避免", "休息"]):
            issues.append("睡眠严重不足且明日高刺激计划时，明日建议必须取消或明显降级")

    if score_result.score >= 81 and hard_plan:
        if not any(term in advice.tomorrow.content for term in ["不安排", "避免", "取消", "降级", "休息", "暂停"]):
            issues.append("高负荷提醒且明日高刺激计划时，明日建议必须偏保守")

    return len(issues) == 0, issues


def build_summary(
    run_input: AnalyzeRecoveryRequest,
    score_result: ScoreResult,
    safety_flags: list[str],
) -> str:
    if safety_flags:
        return "当前存在需要保守处理的风险信号，建议先把安全和恢复放在训练目标前面。"
    if run_input.user_level == "beginner":
        if score_result.score >= 61:
            return "这次恢复压力偏高，先用更保守的恢复安排把身体状态稳住，不急着追训练量。"
        if score_result.score >= 31:
            return "这次恢复压力中等，建议用简单、稳妥的补水、进食和睡眠把基础恢复做好。"
        return "这次恢复压力较低，按基础恢复流程做即可，明日训练继续以轻松和稳定为主。"
    if run_input.user_level == "advanced":
        if score_result.score >= 81:
            return "本次训练刺激和恢复压力都偏高，明日应把质量课降级或移除，优先吸收训练。"
        if score_result.score >= 61:
            return "本次恢复压力较高，建议通过降载、补能和睡眠把训练刺激转化为适应。"
        if score_result.score >= 31:
            return "本次恢复压力中等，可保留低强度活动，但避免在疲劳未消退前叠加质量课。"
        return "本次恢复压力较低，可按计划推进，但仍以晨起状态作为明日训练校准依据。"
    if run_input.past_48h_training in {"hard_training", "race_or_very_hard"} and score_result.score >= 61:
        return "今天恢复压力较高，且近期已有明显训练负荷，明日安排应优先避免连续叠加强刺激。"
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
    elif run_input.user_level == "beginner":
        content += " 先把这一餐吃完整，比精确计算营养更重要。"
    elif run_input.user_level == "advanced":
        content += " 可把这餐视为补糖原和蛋白质摄入窗口，帮助后续训练恢复。"

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
    elif run_input.user_level == "advanced" and run_input.sleep_hours >= 7:
        content += " 若明日仍有训练，可用晨起精神、静息状态和腿部反馈再做负荷微调。"

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
    hard_plan = (run_input.tomorrow_plan or "unknown") in {"intensity", "long", "race"}
    cross_plan = run_input.tomorrow_plan == "strength_cross"
    user_level = run_input.user_level

    if safety_flags:
        content = "明日先暂停跑步或下肢高强度训练，观察不适变化；如果症状持续或影响日常活动，请咨询专业人士。"
    elif user_level == "beginner":
        if score_result.score >= 81:
            content = "明日建议休息或散步，不安排跑步训练；等疲劳和酸痛明显下降后，再从短时间轻松跑开始。"
        elif score_result.score >= 61:
            if hard_plan or cross_plan:
                content = "明日建议取消强度、长距离或下肢力量安排，改为休息、散步或很轻松的活动。"
            else:
                content = "明日建议休息或很轻松的活动，不用为了完成计划硬撑。"
        elif score_result.score >= 31:
            if hard_plan:
                content = "明日先不要做强度或长距离，建议降级为短时间轻松跑、走跑结合或休息。"
            else:
                content = "明日可做轻松活动，但如果醒来仍累或酸痛上升，就直接休息。"
        else:
            content = "明日可安排轻松跑或恢复跑，过程中能顺畅说话即可，不追配速。"
    elif user_level == "advanced":
        if score_result.score >= 81:
            if hard_plan:
                content = "明日建议取消原定质量课或长距离，降级为休息、散步、灵活性或极轻松有氧，不做间歇、节奏跑或比赛刺激。"
            else:
                content = "明日建议以休息、灵活性或极轻松有氧为主，不安排质量课或长距离，把重点放在吸收训练。"
        elif score_result.score >= 61:
            if hard_plan:
                content = "明日原计划建议明显降级：取消质量段，改为短时 Z1/Z2 有氧、技术放松或休息，并保留随时停止的空间。"
            elif cross_plan:
                content = "明日交叉或力量训练建议降低下肢负荷，保留核心、上肢或灵活性内容，不做大重量腿部刺激。"
            else:
                content = "明日可保留低强度恢复性训练，但训练目标从推进表现改为降载和恢复。"
        elif score_result.score >= 31:
            if hard_plan:
                content = "明日可先用热身反馈决定是否保留主课；若 RPE、酸痛或步态异常，主动降级为轻松跑或休息。"
            else:
                content = "明日可安排轻松有氧或技术放松，避免连续叠加高神经肌肉刺激。"
        else:
            content = "明日可按计划推进，但仍以热身状态为准；若疲劳上升，主动降低强度。"
    elif score_result.score >= 81:
        if hard_plan:
            content = "明日建议取消原定高刺激训练，改为休息、散步或非常轻松的活动，不安排间歇、节奏跑、比赛或长距离。"
        else:
            content = "明日建议休息、散步或非常轻松的活动，不安排间歇、节奏跑或长距离。"
    elif score_result.score >= 61:
        if hard_plan:
            content = "明日建议休息或低强度活动；原计划的强度跑、比赛或长距离建议取消，或明显降级为短时间轻松活动。"
        elif cross_plan:
            content = "明日力量或交叉训练建议降低下肢刺激，优先选择轻量核心、上肢或灵活性内容。"
        else:
            content = "明日建议休息或低强度活动，训练中保留随时降级的空间。"
    elif score_result.score >= 31:
        if hard_plan:
            content = "明日可先按状态评估原计划，但不建议硬顶强度；热身后若疲劳或酸痛明显，应降级为轻松跑或休息。"
        else:
            content = "明日可根据状态安排轻松活动，暂时避免连续高强度。"
    else:
        if hard_plan:
            content = "明日可按计划准备，但仍建议以热身状态为准；若醒来疲劳或酸痛上升，主动降低强度。"
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
