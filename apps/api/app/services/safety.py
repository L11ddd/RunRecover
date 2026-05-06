from __future__ import annotations

from app.schemas import AnalyzeRecoveryRequest


SYMPTOM_FLAGS = {
    "chest_pain": "出现胸闷或胸痛等异常症状，建议停止高强度训练，必要时及时咨询医生。",
    "dizziness": "出现头晕等异常症状，建议先休息观察，避免继续训练。",
    "breathing_difficulty": "出现呼吸困难等异常症状，建议停止训练并及时寻求专业帮助。",
    "joint_pain": "出现关节疼痛，建议避免跑步和下肢高强度训练。",
    "pain_affects_walking": "疼痛已经影响日常行走，建议停止跑步并咨询专业运动康复人员。",
}


def evaluate_safety(run_input: AnalyzeRecoveryRequest) -> list[str]:
    flags = [
        message
        for symptom, message in SYMPTOM_FLAGS.items()
        if symptom in run_input.symptoms
    ]

    if run_input.rpe >= 9 and run_input.fatigue_level >= 8:
        flags.append("RPE 和疲劳都处于高位，明日建议休息，不安排强度训练。")

    if run_input.soreness_level >= 8:
        flags.append("酸痛程度较高，建议避免下肢高强度训练，选择休息或轻松活动。")

    if run_input.sleep_hours < 5 and run_input.tomorrow_plan == "intensity":
        flags.append("睡眠不足且明日计划强度训练，建议取消或明显降低强度。")

    return flags
