from __future__ import annotations

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


LegacyRunType = Literal["easy", "tempo", "interval", "long", "race"]
RunTypeMain = Literal["recovery", "easy", "steady", "tempo", "interval", "long", "race"]
RunTypeModifier = Literal[
    "completed",
    "progressive",
    "fartlek",
    "hills",
    "pace_block",
    "short_intervals",
    "long_intervals",
    "mixed_intervals",
    "near_all_out",
]
RunTimePeriod = Literal["morning", "noon", "evening", "night"]
DietPreference = Literal[
    "normal", "fat_loss", "vegetarian", "canteen", "takeout", "light_night"
]
TomorrowPlan = Literal[
    "rest",
    "easy",
    "recovery_easy",
    "intensity",
    "long",
    "strength_cross",
    "race",
    "unknown",
]
Past48hTraining = Literal["rest", "easy_training", "hard_training", "race_or_very_hard"]
UserLevel = Literal["beginner", "regular", "advanced"]
AdviceConservativeness = Literal[
    "safety_first",
    "conservative",
    "balanced",
    "performance_adjusted",
]
FeedbackHelpfulness = Literal["helpful", "neutral", "not_helpful"]
FeedbackNextDayStatus = Literal["recovered", "still_tired", "soreness_worse", "not_recorded"]
FeedbackFollowedAdvice = Literal["yes", "partial", "no"]


class UserProfile(BaseModel):
    user_level: Optional[UserLevel] = None
    running_years: Optional[float] = Field(default=None, ge=0, le=80)
    weekly_runs: Optional[int] = Field(default=None, ge=0, le=14)
    weekly_mileage_km: Optional[float] = Field(default=None, ge=0, le=300)
    race_goal: Optional[bool] = None


def infer_user_level_from_profile(profile: UserProfile | None) -> UserLevel:
    if profile is None:
        return "regular"
    if profile.user_level is not None:
        return profile.user_level

    weekly_runs = profile.weekly_runs
    weekly_mileage_km = profile.weekly_mileage_km
    running_years = profile.running_years

    beginner_signals = [
        running_years is not None and running_years < 0.5,
        weekly_runs is not None and weekly_runs <= 2,
        weekly_mileage_km is not None and weekly_mileage_km < 15,
    ]
    advanced_signals = [
        running_years is not None and running_years >= 2,
        weekly_runs is not None and weekly_runs >= 4,
        weekly_mileage_km is not None and weekly_mileage_km >= 35,
        profile.race_goal is True,
    ]

    if any(beginner_signals):
        return "beginner"
    if sum(1 for signal in advanced_signals if signal) >= 2:
        return "advanced"
    return "regular"


class AnalyzeRecoveryRequest(BaseModel):
    distance_km: float = Field(..., ge=0.5, le=60)
    duration_min: float = Field(..., ge=5, le=360)
    user_level: UserLevel = "regular"
    user_profile: Optional[UserProfile] = None
    run_type_main: Optional[RunTypeMain] = None
    run_type_modifier: List[RunTypeModifier] = Field(default_factory=list)
    run_type: Optional[LegacyRunType] = None
    run_time_period: RunTimePeriod
    rpe: int = Field(..., ge=1, le=10)
    sleep_hours: float = Field(..., ge=0, le=14)
    fatigue_level: int = Field(..., ge=1, le=10)
    soreness_level: int = Field(..., ge=1, le=10)
    avg_hr: Optional[int] = Field(default=None, ge=40, le=230)
    max_hr: Optional[int] = Field(default=None, ge=40, le=230)
    diet_preference: Optional[DietPreference] = "normal"
    tomorrow_plan: Optional[TomorrowPlan] = "unknown"
    past_48h_training: Past48hTraining = "rest"
    symptoms: List[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def normalize_training_type(self) -> "AnalyzeRecoveryRequest":
        if self.run_type_main is None and self.run_type is None:
            raise ValueError("Either run_type_main or run_type is required.")
        if self.run_type_main is None:
            self.run_type_main = self.run_type
        if self.run_type is None and self.run_type_main in {"easy", "tempo", "interval", "long", "race"}:
            self.run_type = self.run_type_main  # compatibility for old consumers and storage
        if "user_level" not in self.model_fields_set:
            self.user_level = infer_user_level_from_profile(self.user_profile)
        return self

    @field_validator("symptoms")
    @classmethod
    def normalize_symptoms(cls, symptoms: List[str]) -> List[str]:
        return sorted({symptom.strip().lower() for symptom in symptoms if symptom})

    @field_validator("run_type_modifier")
    @classmethod
    def normalize_modifiers(cls, modifiers: List[str]) -> List[str]:
        return sorted({modifier.strip().lower() for modifier in modifiers if modifier})


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
    derived_metrics: Dict[str, float] = Field(default_factory=dict)
    model_version: str = "scoring_v0.3"


class RecommendationMeta(BaseModel):
    llm_provider: str
    llm_model: Optional[str] = None
    prompt_version: str
    advice_conservativeness: AdviceConservativeness = "balanced"
    used_fallback: bool = False
    llm_latency_ms: Optional[int] = None
    validation_passed: bool = True


class AnalyzeRecoveryResponse(BaseModel):
    recovery_id: int
    score: int
    level: str
    component_scores: Dict[str, int]
    derived_metrics: Dict[str, float]
    reasons: List[Reason]
    advice: RecoveryAdvice
    timeline: List[TimelineItem]
    safety_flags: List[str]
    recommendation_meta: RecommendationMeta


class FeedbackRequest(BaseModel):
    helpfulness_rating: FeedbackHelpfulness
    next_day_status: FeedbackNextDayStatus = "not_recorded"
    followed_advice: FeedbackFollowedAdvice = "partial"


class FeedbackResponse(BaseModel):
    feedback_id: int
    recovery_id: int


class RecoveryHistoryItem(BaseModel):
    recovery_id: int
    created_at: str
    distance_km: float
    duration_min: float
    run_type_main: str
    run_type_modifier: List[str]
    rpe: int
    score: int
    level: str
    tomorrow_advice: str


class RunScreenshotExtractResponse(BaseModel):
    distance_km: Optional[float] = Field(default=None, ge=0)
    duration_min: Optional[float] = Field(default=None, ge=0)
    pace: Optional[str] = None
    run_type_guess: Optional[str] = None
    run_time_period_guess: Optional[str] = None
    avg_hr: Optional[int] = Field(default=None, ge=1)
    max_hr: Optional[int] = Field(default=None, ge=1)
    calories: Optional[float] = Field(default=None, ge=0)
    elevation_gain: Optional[float] = Field(default=None)
    source_app_guess: Optional[str] = None
    confidence: Dict[str, float] = Field(default_factory=dict)
    missing_fields: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

    @field_validator("confidence")
    @classmethod
    def normalize_confidence(cls, confidence: Dict[str, float]) -> Dict[str, float]:
        normalized: Dict[str, float] = {}
        for key, value in confidence.items():
            try:
                numeric = float(value)
            except (TypeError, ValueError):
                numeric = 0.0
            normalized[key] = max(0.0, min(1.0, numeric))
        return normalized

    @field_validator("missing_fields", "warnings")
    @classmethod
    def normalize_string_list(cls, values: List[str]) -> List[str]:
        return [value.strip() for value in values if value and value.strip()]
