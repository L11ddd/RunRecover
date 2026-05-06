export type RunType = "easy" | "tempo" | "interval" | "long" | "race";
export type RunTimePeriod = "morning" | "noon" | "evening" | "night";
export type DietPreference =
  | "normal"
  | "fat_loss"
  | "vegetarian"
  | "canteen"
  | "takeout"
  | "light_night";
export type TomorrowPlan = "rest" | "easy" | "intensity" | "long" | "unknown";

export type AnalyzeRecoveryRequest = {
  distance_km: number;
  duration_min: number;
  run_type: RunType;
  run_time_period: RunTimePeriod;
  rpe: number;
  sleep_hours: number;
  fatigue_level: number;
  soreness_level: number;
  avg_hr?: number | null;
  max_hr?: number | null;
  diet_preference?: DietPreference;
  tomorrow_plan?: TomorrowPlan;
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
  reasons: Reason[];
  advice: RecoveryAdvice;
  timeline: TimelineItem[];
  safety_flags: string[];
};

export type DemoCase = {
  id: string;
  name: string;
  summary: string;
  payload: AnalyzeRecoveryRequest;
};
