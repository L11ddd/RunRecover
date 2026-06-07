# API

Base URL for local development: `http://127.0.0.1:8000`.

## `GET /api/health`

Returns service status.

```json
{
  "status": "ok",
  "service": "runrecover-api"
}
```

## `POST /api/recovery/analyze`

Analyzes one post-run recovery input and persists the result to SQLite.

### Request

```json
{
  "distance_km": 8,
  "duration_min": 48,
  "user_level": "regular",
  "user_profile": null,
  "run_type_main": "tempo",
  "run_type_modifier": ["progressive"],
  "run_type": "tempo",
  "run_time_period": "night",
  "rpe": 8,
  "sleep_hours": 5.8,
  "fatigue_level": 7,
  "soreness_level": 5,
  "avg_hr": 156,
  "diet_preference": "canteen",
  "tomorrow_plan": "intensity",
  "past_48h_training": "hard_training",
  "symptoms": []
}
```

`run_type` is still accepted for backward compatibility. New clients should send `run_type_main`; use `run_type_modifier` for progressive runs, hills, target-pace blocks, and interval subtypes.

`user_level` is optional and defaults to `regular`. Supported values are `beginner`, `regular`, and `advanced`. It is used as a lightweight advice-calibration layer for wording, conservativeness, and tomorrow guidance; it should not materially change the recovery score. Clients may also send `user_profile` with `running_years`, `weekly_runs`, `weekly_mileage_km`, `race_goal`, or nested `user_level`; when top-level `user_level` is omitted, the backend can infer a simple level from that profile.

`symptoms` accepts an array of abnormal-signal identifiers: `chest_pain`, `dizziness`, `breathing_difficulty`, `palpitations`, `fainting`, `nausea_vomiting`, `joint_pain`, `pain_affects_walking`, `swelling`, `numbness_tingling`, `one_sided_calf_pain`, `fever_infection`, and `dark_urine`.

### Response

```json
{
  "recovery_id": 1,
  "score": 91,
  "level": "高负荷提醒",
  "component_scores": {
    "base_load": 10,
    "duration_load": 4,
    "run_type": 12,
    "run_modifier": 4,
    "rpe": 13,
    "heart_rate": 4,
    "sleep": 10,
    "fatigue": 8,
    "soreness": 5,
    "recent_training": 7,
    "symptoms": 0,
    "time": 6,
    "tomorrow_conflict": 8
  },
  "derived_metrics": {
    "duration_load": 4,
    "session_load": 384
  },
  "reasons": [
    {
      "factor": "RPE",
      "impact": 13,
      "text": "本次 RPE 为 8/10，主观用力感较强，建议提高跑后恢复优先级。"
    }
  ],
  "advice": {
    "summary": "今天恢复压力较高，建议把恢复放在明日训练前面。",
    "diet": {"title": "饮食建议", "content": "跑后 1-2 小时内安排包含主食、蛋白质和蔬菜的恢复餐。"},
    "hydration": {"title": "补水建议", "content": "接下来 2-3 小时少量多次补水。"},
    "sleep": {"title": "睡眠建议", "content": "减少屏幕刺激，尽量保证 7 小时以上睡眠。"},
    "relaxation": {"title": "放松建议", "content": "进行 8-10 分钟慢走或低强度拉伸。"},
    "tomorrow": {"title": "明日安排", "content": "建议休息或轻松活动，避免连续高强度。"},
    "timeline": [
      {"time": "跑后 0-15 分钟", "action": "慢走冷身，少量补水。"}
    ],
    "safety_note": "本建议仅作为一般运动恢复参考，不构成医疗诊断或治疗建议。"
  },
  "timeline": [
    {"time": "跑后 0-15 分钟", "action": "慢走冷身，少量补水。"}
  ],
  "safety_flags": [
    "近 48 小时已有明显负荷叠加，且明日仍计划高刺激训练，建议优先恢复。"
  ],
  "recommendation_meta": {
    "llm_provider": "template",
    "llm_model": null,
    "prompt_version": "recovery_reasons_v0.4",
    "advice_conservativeness": "balanced",
    "used_fallback": false,
    "llm_latency_ms": 0,
    "validation_passed": true
  }
}
```

## `GET /api/recovery/history`

Returns the most recent recovery records. The default and recommended limit is 7.

```json
[
  {
    "recovery_id": 1,
    "created_at": "2026-05-20 18:30:00",
    "distance_km": 8,
    "duration_min": 48,
    "run_type_main": "tempo",
    "run_type_modifier": ["progressive"],
    "rpe": 8,
    "score": 91,
    "level": "高负荷提醒",
    "tomorrow_advice": "明日建议休息或低强度活动..."
  }
]
```

## `POST /api/recovery/{recovery_id}/feedback`

Stores lightweight feedback for a completed recovery analysis.

```json
{
  "helpfulness_rating": "helpful",
  "next_day_status": "recovered",
  "followed_advice": "partial"
}
```
