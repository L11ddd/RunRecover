from __future__ import annotations

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


RunType = Literal["easy", "tempo", "interval", "long", "race"]
RunTimePeriod = Literal["morning", "noon", "evening", "night"]
DietPreference = Literal[
    "normal", "fat_loss", "vegetarian", "canteen", "takeout", "light_night"
]
TomorrowPlan = Literal["rest", "easy", "intensity", "long", "unknown"]


class AnalyzeRecoveryRequest(BaseModel):
    distance_km: float = Field(..., ge=0.5, le=60)
    duration_min: float = Field(..., ge=5, le=360)
    run_type: RunType
    run_time_period: RunTimePeriod
    rpe: int = Field(..., ge=1, le=10)
    sleep_hours: float = Field(..., ge=0, le=14)
    fatigue_level: int = Field(..., ge=1, le=10)
    soreness_level: int = Field(..., ge=1, le=10)
    avg_hr: Optional[int] = Field(default=None, ge=40, le=230)
    max_hr: Optional[int] = Field(default=None, ge=40, le=230)
    diet_preference: Optional[DietPreference] = "normal"
    tomorrow_plan: Optional[TomorrowPlan] = "unknown"
    symptoms: List[str] = Field(default_factory=list)

    @field_validator("symptoms")
    @classmethod
    def normalize_symptoms(cls, symptoms: List[str]) -> List[str]:
        return sorted({symptom.strip().lower() for symptom in symptoms if symptom})


class HealthResponse(BaseModel):
    status: str
    service: str


class Reason(BaseModel):
    factor: str
    impact: int
    text: str


class AdviceItem(BaseModel):
    title: str
    content: str


class TimelineItem(BaseModel):
    time: str
    action: str


class RecoveryAdvice(BaseModel):
    summary: str
    diet: AdviceItem
    hydration: AdviceItem
    sleep: AdviceItem
    relaxation: AdviceItem
    tomorrow: AdviceItem
    timeline: List[TimelineItem]
    safety_note: str


class ScoreResult(BaseModel):
    score: int
    level: str
    component_scores: Dict[str, int]


class AnalyzeRecoveryResponse(BaseModel):
    recovery_id: int
    score: int
    level: str
    component_scores: Dict[str, int]
    reasons: List[Reason]
    advice: RecoveryAdvice
    timeline: List[TimelineItem]
    safety_flags: List[str]
