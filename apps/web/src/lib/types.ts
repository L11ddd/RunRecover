export type RunType = "easy" | "tempo" | "interval" | "long" | "race";
export type RunTypeMain =
  | "recovery"
  | "easy"
  | "steady"
  | "tempo"
  | "interval"
  | "long"
  | "race";
export type RunTypeModifier =
  | "completed"
  | "progressive"
  | "fartlek"
  | "hills"
  | "pace_block"
  | "short_intervals"
  | "long_intervals"
  | "mixed_intervals"
  | "near_all_out";
export type RunTimePeriod = "morning" | "noon" | "evening" | "night";
export type DietPreference =
  | "normal"
  | "fat_loss"
  | "vegetarian"
  | "canteen"
  | "takeout"
  | "light_night";
export type TomorrowPlan =
  | "rest"
  | "easy"
  | "recovery_easy"
  | "intensity"
  | "long"
  | "strength_cross"
  | "race"
  | "unknown";
export type Past48hTraining =
  | "rest"
  | "easy_training"
  | "hard_training"
  | "race_or_very_hard";
export type UserLevel = "beginner" | "regular" | "advanced";

export type UserProfile = {
  user_level?: UserLevel;
  running_years?: number | null;
  weekly_runs?: number | null;
  weekly_mileage_km?: number | null;
  race_goal?: boolean | null;
};

export type AnalyzeRecoveryRequest = {
  distance_km: number;
  duration_min: number;
  user_level: UserLevel;
  user_profile?: UserProfile | null;
  run_type?: RunType | null;
  run_type_main: RunTypeMain;
  run_type_modifier: RunTypeModifier[];
  run_time_period: RunTimePeriod;
  rpe: number;
  sleep_hours: number;
  fatigue_level: number;
  soreness_level: number;
  avg_hr?: number | null;
  max_hr?: number | null;
  diet_preference?: DietPreference;
  tomorrow_plan?: TomorrowPlan;
  past_48h_training: Past48hTraining;
  symptoms: string[];
};

export type Reason = {
  factor: string;
  impact: number;
  text: string;
};

export type AdviceItem = {
  title: string;
  content: string;
};

export type TimelineItem = {
  time: string;
  action: string;
};

export type RecoveryAdvice = {
  summary: string;
  diet: AdviceItem;
  hydration: AdviceItem;
  sleep: AdviceItem;
  relaxation: AdviceItem;
  tomorrow: AdviceItem;
  timeline: TimelineItem[];
  safety_note: string;
};

export type AnalyzeRecoveryResponse = {
  recovery_id: number;
  score: number;
  level: string;
  component_scores: Record<string, number>;
  derived_metrics: Record<string, number>;
  reasons: Reason[];
  advice: RecoveryAdvice;
  timeline: TimelineItem[];
  safety_flags: string[];
  recommendation_meta: RecommendationMeta;
};

export type RecommendationMeta = {
  llm_provider: string;
  llm_model?: string | null;
  prompt_version: string;
  advice_conservativeness?: "safety_first" | "conservative" | "balanced" | "performance_adjusted";
  used_fallback: boolean;
  llm_latency_ms?: number | null;
  validation_passed: boolean;
};

export type FeedbackRequest = {
  helpfulness_rating: "helpful" | "neutral" | "not_helpful";
  next_day_status: "recovered" | "still_tired" | "soreness_worse" | "not_recorded";
  followed_advice: "yes" | "partial" | "no";
};

export type RecoveryHistoryItem = {
  recovery_id: number;
  created_at: string;
  distance_km: number;
  duration_min: number;
  run_type_main: string;
  run_type_modifier: string[];
  rpe: number;
  score: number;
  level: string;
  tomorrow_advice: string;
};

export type DemoCase = {
  id: string;
  name: string;
  summary: string;
  payload: AnalyzeRecoveryRequest;
};
