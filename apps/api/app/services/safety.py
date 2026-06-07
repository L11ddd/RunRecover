from __future__ import annotations

from app.schemas import AnalyzeRecoveryRequest


SYMPTOM_DETAILS = {
    "chest_pain": {
        "label": "胸闷/胸痛",
        "load": 12,
        "message": "出现胸闷或胸痛等异常症状，建议停止高强度训练，必要时及时咨询医生。",
    },
    "dizziness": {
        "label": "头晕",
        "load": 8,
        "message": "出现头晕等异常症状，建议先休息观察，避免继续训练。",
    },
    "breathing_difficulty": {
        "label": "呼吸困难",
        "load": 12,
        "message": "出现呼吸困难等异常症状，建议停止训练并及时寻求专业帮助。",
    },
    "palpitations": {
        "label": "异常心悸",
        "load": 12,
        "message": "出现异常心悸或心跳不规则感，建议停止训练并观察是否持续，必要时及时咨询医生。",
    },
    "fainting": {
        "label": "昏厥/眼前发黑",
        "load": 14,
        "message": "出现昏厥、眼前发黑或接近晕倒的情况，建议停止运动并及时寻求专业帮助。",
    },
    "nausea_vomiting": {
        "label": "恶心/呕吐",
        "load": 8,
        "message": "出现明显恶心或呕吐，建议暂停训练、少量补水并观察是否缓解。",
    },
    "joint_pain": {
        "label": "关节疼痛",
        "load": 8,
        "message": "出现关节疼痛，建议避免跑步和下肢高强度训练。",
    },
    "pain_affects_walking": {
        "label": "疼痛影响走路",
        "load": 12,
        "message": "疼痛已经影响日常行走，建议停止跑步并咨询专业运动康复人员。",
    },
    "swelling": {
        "label": "异常肿胀",
        "load": 8,
        "message": "出现异常肿胀，建议减少负重和冲击，观察肿胀变化，必要时咨询运动康复人员。",
    },
    "numbness_tingling": {
        "label": "麻木/刺痛",
        "load": 8,
        "message": "出现麻木或刺痛感，建议停止刺激性训练，避免继续用跑步测试不适。",
    },
    "one_sided_calf_pain": {
        "label": "单侧小腿痛/肿胀",
        "load": 12,
        "message": "出现单侧小腿疼痛或肿胀，建议停止跑步并尽快咨询专业人员。",
    },
    "fever_infection": {
        "label": "发热/感染感",
        "load": 10,
        "message": "有发热、感染感或明显不适时，建议暂停训练，把恢复和观察放在第一位。",
    },
    "dark_urine": {
        "label": "尿色很深",
        "load": 10,
        "message": "跑后尿色很深可能提示补水不足或身体压力偏高，建议补水观察，若持续异常请咨询专业人员。",
    },
}

SYMPTOM_FLAGS = {
    symptom: details["message"]
    for symptom, details in SYMPTOM_DETAILS.items()
}

SYMPTOM_LABELS = {
    symptom: details["label"]
    for symptom, details in SYMPTOM_DETAILS.items()
}


def get_symptom_load(symptoms: list[str]) -> int:
    load = sum(SYMPTOM_DETAILS.get(symptom, {}).get("load", 0) for symptom in symptoms)
    return min(load, 18)


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

    if run_input.sleep_hours < 5 and run_input.tomorrow_plan in {"intensity", "long", "race"}:
        flags.append("睡眠不足且明日计划高刺激训练，建议取消或明显降低强度。")

    if (
        run_input.past_48h_training in {"hard_training", "race_or_very_hard"}
        and run_input.rpe >= 8
        and run_input.tomorrow_plan in {"intensity", "long", "race"}
    ):
        flags.append("近 48 小时已有明显负荷叠加，且明日仍计划高刺激训练，建议优先恢复。")

    return flags
