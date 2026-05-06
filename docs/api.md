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
  "run_type": "tempo",
  "run_time_period": "night",
  "rpe": 8,
  "sleep_hours": 5.8,
  "fatigue_level": 7,
  "soreness_level": 5,
  "avg_hr": 156,
  "diet_preference": "canteen",
  "tomorrow_plan": "intensity",
  "symptoms": []
}
```

### Response

```json
{
  "recovery_id": 1,
  "score": 78,
  "level": "重点恢复",
  "component_scores": {
    "base_load": 10,
    "run_type": 12,
    "rpe": 15,
    "heart_rate": 4,
    "sleep": 10,
    "fatigue": 8,
    "soreness": 5,
    "time": 6,
    "tomorrow_conflict": 5
  },
  "reasons": [
    {
      "factor": "RPE",
      "impact": 15,
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
  "safety_flags": []
}
```
