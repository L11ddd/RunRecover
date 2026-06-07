import { useEffect, useMemo, useState, type FormEvent, type ReactNode } from "react";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  CalendarClock,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  ClipboardList,
  Clock3,
  Droplets,
  FileImage,
  HeartPulse,
  History,
  Keyboard,
  ListChecks,
  Loader2,
  Moon,
  RotateCcw,
  ShieldAlert,
  SlidersHorizontal,
  Utensils,
  Zap,
  type LucideIcon,
} from "lucide-react";

import { analyzeRecovery, extractRunScreenshot, fetchRecoveryHistory, submitFeedback } from "./lib/api";
import { demoCases } from "./lib/demoCases";
import type {
  AdviceItem,
  AnalyzeRecoveryRequest,
  AnalyzeRecoveryResponse,
  DemoCase,
  DietPreference,
  FeedbackRequest,
  Past48hTraining,
  RecoveryHistoryItem,
  RunScreenshotExtractResponse,
  RunTimePeriod,
  RunTypeMain,
  RunTypeModifier,
  TimelineItem,
  TomorrowPlan,
  UserLevel,
} from "./lib/types";

const defaultPayload: AnalyzeRecoveryRequest = {
  distance_km: 8,
  duration_min: 48,
  user_level: "regular",
  run_type_main: "tempo",
  run_type_modifier: [],
  run_type: "tempo",
  run_time_period: "night",
  rpe: 5,
  sleep_hours: 7,
  fatigue_level: 5,
  soreness_level: 4,
  avg_hr: null,
  max_hr: null,
  diet_preference: "normal",
  tomorrow_plan: "unknown",
  past_48h_training: "rest",
  symptoms: [],
};

const runTypeOptions: Array<{ value: RunTypeMain; label: string }> = [
  { value: "recovery", label: "恢复跑" },
  { value: "easy", label: "轻松跑" },
  { value: "steady", label: "稳态跑" },
  { value: "tempo", label: "节奏跑" },
  { value: "interval", label: "间歇跑" },
  { value: "long", label: "长距离跑" },
  { value: "race", label: "比赛" },
];

const legacyRunTypes = new Set<RunTypeMain>(["easy", "tempo", "interval", "long", "race"]);

const runTypeModifierOptions: Array<{
  value: RunTypeModifier;
  label: string;
  visibleFor?: RunTypeMain[];
}> = [
  { value: "completed", label: "连续完成" },
  { value: "progressive", label: "渐进加速", visibleFor: ["easy", "steady", "tempo", "long"] },
  { value: "fartlek", label: "变速/Fartlek", visibleFor: ["steady", "tempo", "interval"] },
  { value: "hills", label: "坡跑", visibleFor: ["easy", "steady", "tempo", "interval", "long"] },
  { value: "pace_block", label: "目标配速段", visibleFor: ["tempo", "long", "race"] },
  { value: "short_intervals", label: "短间歇", visibleFor: ["interval"] },
  { value: "long_intervals", label: "长间歇", visibleFor: ["interval"] },
  { value: "mixed_intervals", label: "混合间歇", visibleFor: ["interval"] },
  { value: "near_all_out", label: "接近全力", visibleFor: ["race"] },
];

const runTimeOptions: Array<{ value: RunTimePeriod; label: string }> = [
  { value: "morning", label: "早晨" },
  { value: "noon", label: "中午" },
  { value: "evening", label: "傍晚" },
  { value: "night", label: "夜跑" },
];

const dietOptions: Array<{ value: DietPreference; label: string }> = [
  { value: "normal", label: "正常饮食" },
  { value: "fat_loss", label: "减脂" },
  { value: "vegetarian", label: "素食" },
  { value: "canteen", label: "食堂" },
  { value: "takeout", label: "外卖" },
  { value: "light_night", label: "夜间轻食" },
];

const tomorrowOptions: Array<{ value: TomorrowPlan; label: string }> = [
  { value: "unknown", label: "未确定" },
  { value: "rest", label: "休息" },
  { value: "recovery_easy", label: "恢复/轻松跑" },
  { value: "easy", label: "轻松跑" },
  { value: "intensity", label: "强度跑" },
  { value: "long", label: "长距离" },
  { value: "strength_cross", label: "力量/交叉训练" },
  { value: "race", label: "比赛" },
];

const past48hOptions: Array<{ value: Past48hTraining; label: string }> = [
  { value: "rest", label: "基本休息" },
  { value: "easy_training", label: "轻松训练" },
  { value: "hard_training", label: "强度训练" },
  { value: "race_or_very_hard", label: "比赛/极高负荷" },
];

const userLevelOptions: Array<{
  value: UserLevel;
  label: string;
  description: string;
}> = [
  {
    value: "beginner",
    label: "跑步新手",
    description: "更保守，强调基础恢复和安全",
  },
  {
    value: "regular",
    label: "规律跑者",
    description: "平衡恢复和训练连续性",
  },
  {
    value: "advanced",
    label: "进阶跑者",
    description: "更多使用降级和训练调整表达",
  },
];

const symptomOptions = [
  { value: "chest_pain", label: "胸闷/胸痛" },
  { value: "dizziness", label: "头晕" },
  { value: "breathing_difficulty", label: "呼吸困难" },
  { value: "joint_pain", label: "关节疼痛" },
  { value: "pain_affects_walking", label: "疼痛影响走路" },
];

const componentLabels: Record<string, string> = {
  base_load: "跑量",
  duration_load: "时长",
  run_type: "类型",
  run_modifier: "修饰",
  rpe: "RPE",
  heart_rate: "心率",
  sleep: "睡眠",
  fatigue: "疲劳",
  soreness: "酸痛",
  recent_training: "近 48h",
  time: "时间",
  tomorrow_conflict: "明日冲突",
};

const defaultFeedback: FeedbackRequest = {
  helpfulness_rating: "helpful",
  next_day_status: "not_recorded",
  followed_advice: "partial",
};

const screenshotFieldLabels: Record<string, string> = {
  distance_km: "距离",
  duration_min: "时长",
  pace: "配速",
  run_type_guess: "跑步类型",
  run_time_period_guess: "跑步时间",
  avg_hr: "平均心率",
  max_hr: "最大心率",
  calories: "热量",
  elevation_gain: "爬升",
  source_app_guess: "来源 App",
};

type ScreenshotStatus = "idle" | "extracting" | "success" | "error";
const isScreenshotUploadEnabled = import.meta.env.VITE_ENABLE_SCREENSHOT_UPLOAD === "true";

type AppView = "input" | "analyzing" | "result";
type InputStepId = "method" | "load" | "body" | "context" | "confirm";
type ResultTabId = "summary" | "plan" | "details";

const inputSteps: Array<{
  id: InputStepId;
  label: string;
  title: string;
  icon: LucideIcon;
}> = [
  { id: "method", label: "输入方式", title: "选择输入方式", icon: Keyboard },
  { id: "load", label: "跑步负荷", title: "跑步负荷", icon: Activity },
  { id: "body", label: "身体状态", title: "身体状态", icon: HeartPulse },
  { id: "context", label: "恢复约束", title: "恢复约束", icon: CalendarClock },
  { id: "confirm", label: "确认分析", title: "确认分析", icon: ListChecks },
];

const resultTabs: Array<{
  id: ResultTabId;
  label: string;
  icon: LucideIcon;
}> = [
  { id: "summary", label: "结论", icon: BarChart3 },
  { id: "plan", label: "恢复计划", icon: CalendarClock },
  { id: "details", label: "原因详情", icon: SlidersHorizontal },
];

type EditableAnalyzeRecoveryRequest = Omit<
  AnalyzeRecoveryRequest,
  "distance_km" | "duration_min" | "sleep_hours" | "avg_hr" | "max_hr"
> & {
  distance_km: number | null;
  duration_min: number | null;
  sleep_hours: number | null;
  avg_hr: number | null;
  max_hr: number | null;
};

function toEditableForm(payload: AnalyzeRecoveryRequest): EditableAnalyzeRecoveryRequest {
  return {
    ...payload,
    avg_hr: payload.avg_hr ?? null,
    max_hr: payload.max_hr ?? null,
  };
}

function buildAnalyzePayload(
  form: EditableAnalyzeRecoveryRequest,
): AnalyzeRecoveryRequest | null {
  if (form.distance_km === null || form.duration_min === null || form.sleep_hours === null) {
    return null;
  }

  return {
    ...form,
    distance_km: form.distance_km,
    duration_min: form.duration_min,
    sleep_hours: form.sleep_hours,
    avg_hr: form.avg_hr,
    max_hr: form.max_hr,
  };
}

function isRunTypeMain(value: string | null): value is RunTypeMain {
  return runTypeOptions.some((option) => option.value === value);
}

function isRunTimePeriod(value: string | null): value is RunTimePeriod {
  return runTimeOptions.some((option) => option.value === value);
}

function normalizeRunTypeGuess(value: string | null): RunTypeMain | null {
  if (!value) {
    return null;
  }
  const normalized = value.trim().toLowerCase().replace(/\s+/g, "_");
  if (isRunTypeMain(normalized)) {
    return normalized;
  }

  const aliases: Record<string, RunTypeMain> = {
    recovery_run: "recovery",
    easy_run: "easy",
    steady_run: "steady",
    tempo_run: "tempo",
    interval_run: "interval",
    intervals: "interval",
    long_run: "long",
    race_run: "race",
    morning_run: "easy",
    night_run: "easy",
  };
  return aliases[normalized] ?? null;
}

function normalizeRunTimeGuess(value: string | null): RunTimePeriod | null {
  if (!value) {
    return null;
  }
  const normalized = value.trim().toLowerCase().replace(/\s+/g, "_");
  if (isRunTimePeriod(normalized)) {
    return normalized;
  }
  const aliases: Record<string, RunTimePeriod> = {
    dawn: "morning",
    am: "morning",
    morning_run: "morning",
    lunch: "noon",
    afternoon: "evening",
    dusk: "evening",
    pm: "evening",
    evening_run: "evening",
    night_run: "night",
  };
  return aliases[normalized] ?? null;
}

function normalizeApiError(message: string) {
  try {
    const parsed = JSON.parse(message);
    if (typeof parsed.detail === "string") {
      return parsed.detail;
    }
  } catch {
    // Keep original text below.
  }
  return message || "未能可靠识别截图内容，请手动填写跑步数据。";
}

function formatScreenshotValue(field: string, value: string | number | null) {
  if (value === null || value === "") {
    return "未识别";
  }
  if (typeof value === "number") {
    if (field === "distance_km") {
      return `${formatCompactNumber(value)} km`;
    }
    if (field === "duration_min") {
      return `${formatCompactNumber(value)} min`;
    }
    if (field === "avg_hr" || field === "max_hr") {
      return `${Math.round(value)} bpm`;
    }
    if (field === "calories") {
      return `${Math.round(value)} kcal`;
    }
    if (field === "elevation_gain") {
      return `${Math.round(value)} m`;
    }
    return formatCompactNumber(value);
  }
  if (field === "run_type_guess") {
    return runTypeOptions.find((option) => option.value === normalizeRunTypeGuess(value))?.label ?? value;
  }
  if (field === "run_time_period_guess") {
    return runTimeOptions.find((option) => option.value === normalizeRunTimeGuess(value))?.label ?? value;
  }
  return value;
}

function App() {
  const [form, setForm] = useState<EditableAnalyzeRecoveryRequest>(() =>
    toEditableForm(defaultPayload),
  );
  const [result, setResult] = useState<AnalyzeRecoveryResponse | null>(null);
  const [appView, setAppView] = useState<AppView>("input");
  const [inputStep, setInputStep] = useState<InputStepId>("method");
  const [resultTab, setResultTab] = useState<ResultTabId>("summary");
  const [activeCaseId, setActiveCaseId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<RecoveryHistoryItem[]>([]);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [feedbackForm, setFeedbackForm] = useState<FeedbackRequest>(defaultFeedback);
  const [feedbackStatus, setFeedbackStatus] = useState<"idle" | "submitting" | "sent" | "error">(
    "idle",
  );
  const [screenshotStatus, setScreenshotStatus] = useState<ScreenshotStatus>("idle");
  const [screenshotPreviewUrl, setScreenshotPreviewUrl] = useState<string | null>(null);
  const [screenshotResult, setScreenshotResult] = useState<RunScreenshotExtractResponse | null>(
    null,
  );
  const [screenshotError, setScreenshotError] = useState<string | null>(null);
  const [screenshotTouchedFields, setScreenshotTouchedFields] = useState<string[]>([]);
  const [isScreenshotConfirmed, setIsScreenshotConfirmed] = useState(false);

  const visibleModifierOptions = useMemo(
    () =>
      runTypeModifierOptions.filter(
        (option) => !option.visibleFor || option.visibleFor.includes(form.run_type_main),
      ),
    [form.run_type_main],
  );
  const currentStepIndex = inputSteps.findIndex((step) => step.id === inputStep);
  const activeInputStep = inputSteps[currentStepIndex] ?? inputSteps[0];

  const loadHistory = async () => {
    try {
      const records = await fetchRecoveryHistory(7);
      setHistory(records);
      setHistoryError(null);
    } catch (requestError) {
      setHistoryError(requestError instanceof Error ? requestError.message : "历史记录加载失败");
    }
  };

  useEffect(() => {
    void loadHistory();
  }, []);

  useEffect(() => {
    return () => {
      if (screenshotPreviewUrl) {
        URL.revokeObjectURL(screenshotPreviewUrl);
      }
    };
  }, [screenshotPreviewUrl]);

  const updateField = <K extends keyof EditableAnalyzeRecoveryRequest>(
    field: K,
    value: EditableAnalyzeRecoveryRequest[K],
  ) => {
    setForm((current) => ({ ...current, [field]: value }));
    setScreenshotTouchedFields((current) => current.filter((item) => item !== field));
    setActiveCaseId(null);
  };

  const updateRunTypeMain = (value: RunTypeMain) => {
    setForm((current) => ({
      ...current,
      run_type_main: value,
      run_type: legacyRunTypes.has(value) ? (value as AnalyzeRecoveryRequest["run_type"]) : null,
      run_type_modifier: current.run_type_modifier.filter((modifier) => {
        const option = runTypeModifierOptions.find((item) => item.value === modifier);
        return !option?.visibleFor || option.visibleFor.includes(value);
      }),
    }));
    setScreenshotTouchedFields((current) => current.filter((item) => item !== "run_type_main"));
    setActiveCaseId(null);
  };

  const toggleModifier = (modifier: RunTypeModifier) => {
    setForm((current) => {
      const run_type_modifier = current.run_type_modifier.includes(modifier)
        ? current.run_type_modifier.filter((item) => item !== modifier)
        : [...current.run_type_modifier, modifier];
      return { ...current, run_type_modifier };
    });
    setActiveCaseId(null);
  };

  const resetInput = () => {
    if (screenshotPreviewUrl) {
      URL.revokeObjectURL(screenshotPreviewUrl);
    }
    setForm(toEditableForm(defaultPayload));
    setResult(null);
    setError(null);
    setActiveCaseId(null);
    setScreenshotPreviewUrl(null);
    setScreenshotResult(null);
    setScreenshotStatus("idle");
    setScreenshotError(null);
    setScreenshotTouchedFields([]);
    setIsScreenshotConfirmed(false);
    setFeedbackForm(defaultFeedback);
    setFeedbackStatus("idle");
    setInputStep("method");
    setResultTab("summary");
    setAppView("input");
  };

  const validateStep = (step: InputStepId) => {
    if (step === "load") {
      if (form.distance_km === null || form.distance_km <= 0) {
        return "请填写有效的跑步距离。";
      }
      if (form.duration_min === null || form.duration_min <= 0) {
        return "请填写有效的跑步时长。";
      }
    }

    if (step === "body") {
      if (form.sleep_hours === null || form.sleep_hours < 0) {
        return "请填写有效的睡眠时间。";
      }
      if (form.avg_hr !== null && form.avg_hr <= 0) {
        return "平均心率需要大于 0，或留空。";
      }
      if (form.max_hr !== null && form.max_hr <= 0) {
        return "最大心率需要大于 0，或留空。";
      }
    }

    if (step === "confirm") {
      if (!buildAnalyzePayload(form)) {
        return "请先填写距离、时长和睡眠时间。";
      }
    }

    return null;
  };

  const goToInputStep = (step: InputStepId) => {
    const nextIndex = inputSteps.findIndex((item) => item.id === step);
    if (nextIndex <= currentStepIndex) {
      setInputStep(step);
      setError(null);
    }
  };

  const goToNextInputStep = () => {
    const validationMessage = validateStep(inputStep);
    if (validationMessage) {
      setError(validationMessage);
      return;
    }
    setError(null);

    if (currentStepIndex >= inputSteps.length - 1) {
      const payload = buildAnalyzePayload(form);
      if (payload) {
        void runAnalyze(payload);
      }
      return;
    }

    setInputStep(inputSteps[currentStepIndex + 1].id);
  };

  const goToPreviousInputStep = () => {
    if (currentStepIndex === 0) {
      return;
    }
    setInputStep(inputSteps[currentStepIndex - 1].id);
    setError(null);
  };

  const applyScreenshotResult = (extraction: RunScreenshotExtractResponse) => {
    const recognizedFields: string[] = [];
    const runTypeGuess = normalizeRunTypeGuess(extraction.run_type_guess);
    const runTimeGuess = normalizeRunTimeGuess(extraction.run_time_period_guess);

    setForm((current) => {
      const next = { ...current };

      if (extraction.distance_km !== null) {
        next.distance_km = extraction.distance_km;
        recognizedFields.push("distance_km");
      }
      if (extraction.duration_min !== null) {
        next.duration_min = extraction.duration_min;
        recognizedFields.push("duration_min");
      }
      if (runTypeGuess) {
        next.run_type_main = runTypeGuess;
        next.run_type = legacyRunTypes.has(runTypeGuess)
          ? (runTypeGuess as AnalyzeRecoveryRequest["run_type"])
          : null;
        next.run_type_modifier = current.run_type_modifier.filter((modifier) => {
          const option = runTypeModifierOptions.find((item) => item.value === modifier);
          return !option?.visibleFor || option.visibleFor.includes(runTypeGuess);
        });
        recognizedFields.push("run_type_main");
      }
      if (runTimeGuess) {
        next.run_time_period = runTimeGuess;
        recognizedFields.push("run_time_period");
      }
      if (extraction.avg_hr !== null) {
        next.avg_hr = extraction.avg_hr;
        recognizedFields.push("avg_hr");
      }
      if (extraction.max_hr !== null) {
        next.max_hr = extraction.max_hr;
        recognizedFields.push("max_hr");
      }

      return next;
    });

    setScreenshotTouchedFields(recognizedFields);
    setIsScreenshotConfirmed(false);
    setActiveCaseId(null);
  };

  const handleScreenshotFile = async (file: File | null) => {
    if (!file) {
      return;
    }

    if (!["image/png", "image/jpeg", "image/webp"].includes(file.type)) {
      setScreenshotStatus("error");
      setScreenshotError("仅支持 png、jpg、jpeg、webp 图片。");
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      setScreenshotStatus("error");
      setScreenshotError("图片过大，最大支持 5MB。");
      return;
    }

    if (screenshotPreviewUrl) {
      URL.revokeObjectURL(screenshotPreviewUrl);
    }
    setScreenshotPreviewUrl(URL.createObjectURL(file));
    setScreenshotStatus("extracting");
    setScreenshotError(null);
    setScreenshotResult(null);
    setScreenshotTouchedFields([]);
    setIsScreenshotConfirmed(false);

    try {
      const extraction = await extractRunScreenshot(file);
      setScreenshotResult(extraction);
      applyScreenshotResult(extraction);
      setScreenshotStatus("success");
    } catch (requestError) {
      setScreenshotStatus("error");
      setScreenshotError(
        requestError instanceof Error
          ? normalizeApiError(requestError.message)
          : "未能可靠识别截图内容，请手动填写跑步数据。",
      );
    }
  };

  const runAnalyze = async (payload: AnalyzeRecoveryRequest) => {
    setIsLoading(true);
    setError(null);
    setAppView("analyzing");
    try {
      const response = await analyzeRecovery(payload);
      setResult(response);
      setResultTab("summary");
      setAppView("result");
      setFeedbackForm(defaultFeedback);
      setFeedbackStatus("idle");
      void loadHistory();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "分析请求失败");
      setInputStep("confirm");
      setAppView("input");
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    goToNextInputStep();
  };

  const handleDemoCase = (demoCase: DemoCase) => {
    setForm(toEditableForm(demoCase.payload));
    setActiveCaseId(demoCase.id);
    setInputStep("confirm");
    void runAnalyze(demoCase.payload);
  };

  const toggleSymptom = (symptom: string) => {
    setForm((current) => {
      const symptoms = current.symptoms.includes(symptom)
        ? current.symptoms.filter((item) => item !== symptom)
        : [...current.symptoms, symptom];
      return { ...current, symptoms };
    });
    setActiveCaseId(null);
  };

  const handleFeedbackSubmit = async () => {
    if (!result) {
      return;
    }
    setFeedbackStatus("submitting");
    try {
      await submitFeedback(result.recovery_id, feedbackForm);
      setFeedbackStatus("sent");
    } catch {
      setFeedbackStatus("error");
    }
  };

  const handleModifyInput = () => {
    setAppView("input");
    setInputStep("load");
    setError(null);
  };

  const handleReanalyze = () => {
    const payload = buildAnalyzePayload(form);
    if (!payload) {
      setError("请先填写距离、时长和睡眠时间。");
      setAppView("input");
      setInputStep("confirm");
      return;
    }
    void runAnalyze(payload);
  };

  const pace = useMemo(() => {
    if (!form.distance_km || !form.duration_min) {
      return "0:00";
    }
    const totalSeconds = Math.round((form.duration_min * 60) / form.distance_km);
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = String(totalSeconds % 60).padStart(2, "0");
    return `${minutes}:${seconds}`;
  }, [form.distance_km, form.duration_min]);

  const headerMetrics: HeaderMetricProps[] = [
    { label: "配速", value: `${pace}/km`, icon: Clock3 },
    { label: "RPE", value: `${form.rpe}/10`, icon: Zap },
    {
      label: "睡眠",
      value: form.sleep_hours === null ? "未填" : `${formatCompactNumber(form.sleep_hours)}h`,
      icon: Moon,
    },
    {
      label: "明日",
      value: tomorrowOptions.find((option) => option.value === form.tomorrow_plan)?.label ?? "未确定",
      icon: CalendarClock,
    },
  ];

  const inputStepContent = (() => {
    switch (inputStep) {
      case "method":
        return (
          <div className="wizard-step">
            <div className="method-grid">
              <MethodCard
                icon={Keyboard}
                title="手动填写"
                description="逐步补全跑步负荷、身体状态和恢复约束。"
                actionLabel="开始填写"
                onClick={() => {
                  setError(null);
                  setInputStep("load");
                }}
              />
              <MethodCard
                icon={FileImage}
                title="上传运动截图"
                description={
                  isScreenshotUploadEnabled
                    ? "识别截图中的距离、时长和心率，再回填表单。"
                    : "当前大模型不支持图片识别，入口暂时预留。"
                }
                actionLabel={isScreenshotUploadEnabled ? "下方上传" : "暂未启用"}
                disabled={!isScreenshotUploadEnabled}
                passive={isScreenshotUploadEnabled}
              />
              <MethodCard
                icon={CheckCircle2}
                title="使用演示案例"
                description="点击下方案例可直接填充表单并开始分析。"
                actionLabel="下方选择"
                passive
              />
            </div>

            {isScreenshotUploadEnabled ? (
              <ScreenshotUploadPanel
                status={screenshotStatus}
                previewUrl={screenshotPreviewUrl}
                result={screenshotResult}
                error={screenshotError}
                touchedFields={screenshotTouchedFields}
                confirmed={isScreenshotConfirmed}
                onFileSelect={handleScreenshotFile}
                onConfirm={() => setIsScreenshotConfirmed(true)}
              />
            ) : null}

            <DemoCaseBar
              cases={demoCases}
              activeCaseId={activeCaseId}
              onSelect={handleDemoCase}
              disabled={isLoading}
            />
          </div>
        );
      case "load":
        return (
          <div className="wizard-step">
            <FormSection eyebrow="Load" title="跑步负荷" icon={Activity}>
              <div className="field-grid two-columns">
                <NumberField
                  label="距离 km"
                  min={0.5}
                  max={60}
                  step={0.1}
                  value={form.distance_km}
                  source={screenshotTouchedFields.includes("distance_km") ? "已从截图识别，可修改" : undefined}
                  onChange={(value) => updateField("distance_km", value)}
                />
                <NumberField
                  label="时长 min"
                  min={5}
                  max={360}
                  step={1}
                  value={form.duration_min}
                  source={screenshotTouchedFields.includes("duration_min") ? "已从截图识别，可修改" : undefined}
                  onChange={(value) => updateField("duration_min", value)}
                />
              </div>

              <div className="field-grid two-columns">
                <SelectField
                  label="跑步类型"
                  value={form.run_type_main}
                  options={runTypeOptions}
                  source={screenshotTouchedFields.includes("run_type_main") ? "已从截图识别，可修改" : undefined}
                  onChange={(value) => updateRunTypeMain(value as RunTypeMain)}
                />
                <SelectField
                  label="跑步时间"
                  value={form.run_time_period}
                  options={runTimeOptions}
                  source={screenshotTouchedFields.includes("run_time_period") ? "已从截图识别，可修改" : undefined}
                  onChange={(value) => updateField("run_time_period", value as RunTimePeriod)}
                />
              </div>

              <ModifierFieldset
                options={visibleModifierOptions}
                selected={form.run_type_modifier}
                onToggle={toggleModifier}
              />
            </FormSection>
          </div>
        );
      case "body":
        return (
          <div className="wizard-step">
            <FormSection eyebrow="Body" title="身体状态" icon={HeartPulse}>
              <RpeSlider value={form.rpe} onChange={(value) => updateField("rpe", value)} />

              <div className="field-grid three-columns">
                <NumberField
                  label="睡眠 h"
                  min={0}
                  max={14}
                  step={0.1}
                  value={form.sleep_hours}
                  onChange={(value) => updateField("sleep_hours", value)}
                />
                <RangeField
                  label="疲劳"
                  value={form.fatigue_level}
                  hint={getFatigueLabel(form.fatigue_level)}
                  onChange={(value) => updateField("fatigue_level", value)}
                />
                <RangeField
                  label="酸痛"
                  value={form.soreness_level}
                  hint={getSorenessLabel(form.soreness_level)}
                  onChange={(value) => updateField("soreness_level", value)}
                />
              </div>

              <div className="field-grid two-columns">
                <NumberField
                  label="平均心率"
                  min={40}
                  max={230}
                  step={1}
                  value={form.avg_hr}
                  optional
                  source={screenshotTouchedFields.includes("avg_hr") ? "已从截图识别，可修改" : undefined}
                  onChange={(value) => updateField("avg_hr", value)}
                />
                <NumberField
                  label="最大心率"
                  min={40}
                  max={230}
                  step={1}
                  value={form.max_hr}
                  optional
                  source={screenshotTouchedFields.includes("max_hr") ? "已从截图识别，可修改" : undefined}
                  onChange={(value) => updateField("max_hr", value)}
                />
              </div>
            </FormSection>
          </div>
        );
      case "context":
        return (
          <div className="wizard-step">
            <FormSection eyebrow="Context" title="恢复约束" icon={CalendarClock}>
              <UserLevelField
                value={form.user_level}
                onChange={(value) => updateField("user_level", value)}
              />

              <div className="field-grid two-columns">
                <SelectField
                  label="饮食场景"
                  value={form.diet_preference ?? "normal"}
                  options={dietOptions}
                  onChange={(value) => updateField("diet_preference", value as DietPreference)}
                />
                <SelectField
                  label="明日计划"
                  value={form.tomorrow_plan ?? "unknown"}
                  options={tomorrowOptions}
                  onChange={(value) => updateField("tomorrow_plan", value as TomorrowPlan)}
                />
              </div>

              <SelectField
                label="近 48 小时训练"
                value={form.past_48h_training}
                options={past48hOptions}
                onChange={(value) => updateField("past_48h_training", value as Past48hTraining)}
              />
            </FormSection>

            <FormSection eyebrow="Safety" title="异常信号" icon={ShieldAlert}>
              <fieldset className="symptom-fieldset">
                <legend>异常信号</legend>
                <div className="symptom-grid">
                  {symptomOptions.map((symptom) => (
                    <label className="checkbox-pill" key={symptom.value}>
                      <input
                        type="checkbox"
                        checked={form.symptoms.includes(symptom.value)}
                        onChange={() => toggleSymptom(symptom.value)}
                      />
                      <span>{symptom.label}</span>
                    </label>
                  ))}
                </div>
              </fieldset>
            </FormSection>
          </div>
        );
      case "confirm":
        return (
          <div className="wizard-step">
            <FormSection eyebrow="Review" title="输入摘要" icon={ClipboardList}>
              <InputSummary form={form} pace={pace} />
            </FormSection>
          </div>
        );
      default:
        return null;
    }
  })();
  const ActiveStepIcon = activeInputStep.icon;

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand-block">
          <p className="eyebrow">Post-run recovery intelligence</p>
          <h1>RunRecover</h1>
          <p>AI 跑后恢复助手 · 跑后 24 小时恢复决策</p>
        </div>
        <div className="topbar-metrics" aria-label="当前输入摘要">
          {headerMetrics.map((metric) => (
            <HeaderMetric
              key={metric.label}
              label={metric.label}
              value={metric.value}
              icon={metric.icon}
            />
          ))}
        </div>
      </header>

      <main className={appView === "result" ? "workspace result-workspace" : "workspace"}>
        {appView === "input" ? (
          <section className="input-panel wizard-panel" aria-labelledby="input-title">
            <div className="section-heading wizard-heading">
              <div className="wizard-title-block">
                <div className="form-section-icon">
                  <ActiveStepIcon size={18} aria-hidden="true" />
                </div>
                <div>
                  <p className="eyebrow">
                    Step {currentStepIndex + 1} / {inputSteps.length}
                  </p>
                  <h2 id="input-title">{activeInputStep.title}</h2>
                </div>
              </div>
              <div className="pace-badge">
                <Clock3 size={16} aria-hidden="true" />
                <span>{pace}/km</span>
              </div>
            </div>

            <InputStepper
              steps={inputSteps}
              currentStep={inputStep}
              currentIndex={currentStepIndex}
              onSelect={goToInputStep}
            />

            <form className="input-form" onSubmit={handleSubmit}>
              {inputStepContent}

              {error ? (
                <div className="error-banner" role="alert">
                  <AlertTriangle size={18} aria-hidden="true" />
                  <span>{error}</span>
                </div>
              ) : null}

              <div className="wizard-actions">
                <button
                  className="secondary-button"
                  type="button"
                  onClick={goToPreviousInputStep}
                  disabled={currentStepIndex === 0}
                >
                  <ChevronLeft size={18} aria-hidden="true" />
                  上一步
                </button>
                <button className="secondary-button" type="button" onClick={resetInput}>
                  <RotateCcw size={18} aria-hidden="true" />
                  重置
                </button>
                <button className="primary-button" type="submit" disabled={isLoading}>
                  {isLoading ? (
                    <Loader2 className="spin" size={18} aria-hidden="true" />
                  ) : inputStep === "confirm" ? (
                    <Zap size={18} aria-hidden="true" />
                  ) : (
                    <ChevronRight size={18} aria-hidden="true" />
                  )}
                  {inputStep === "confirm" ? "开始分析" : "下一步"}
                </button>
              </div>
            </form>
          </section>
        ) : null}

        {appView === "analyzing" ? (
          <section className="result-panel analyzing-panel" aria-live="polite">
            <div className="loading-card">
              <Loader2 className="spin" size={28} aria-hidden="true" />
              <div>
                <p className="eyebrow">Analyzing</p>
                <h2>正在生成恢复建议</h2>
                <p>系统正在计算恢复压力并生成 24 小时计划。</p>
              </div>
            </div>
          </section>
        ) : null}

        {appView === "result" && result ? (
          <section className="result-panel result-page" aria-labelledby="result-title">
            <div className="section-heading result-page-heading">
              <div>
                <p className="eyebrow">Output</p>
                <h2 id="result-title">恢复结果</h2>
              </div>
              <div className="result-heading-actions">
                <span className="record-id">#{result.recovery_id}</span>
                <button className="secondary-button compact" type="button" onClick={handleModifyInput}>
                  <ClipboardList size={16} aria-hidden="true" />
                  修改输入
                </button>
                <button className="primary-button compact" type="button" onClick={handleReanalyze} disabled={isLoading}>
                  <Zap size={16} aria-hidden="true" />
                  重新分析
                </button>
              </div>
            </div>

            <ResultTabs activeTab={resultTab} onChange={setResultTab} />

            <ResultView
              result={result}
              activeTab={resultTab}
              feedback={feedbackForm}
              feedbackStatus={feedbackStatus}
              onFeedbackChange={(nextFeedback) => {
                setFeedbackForm(nextFeedback);
                setFeedbackStatus("idle");
              }}
              onFeedbackSubmit={handleFeedbackSubmit}
            />

            <details className="history-disclosure">
              <summary className="history-summary">
                <History size={18} aria-hidden="true" />
                最近 7 次记录
              </summary>
              <HistoryPanel items={history} error={historyError} />
            </details>
          </section>
        ) : null}
      </main>
    </div>
  );
}

type InputStepperProps = {
  steps: typeof inputSteps;
  currentStep: InputStepId;
  currentIndex: number;
  onSelect: (step: InputStepId) => void;
};

function InputStepper({ steps, currentStep, currentIndex, onSelect }: InputStepperProps) {
  return (
    <nav className="input-stepper" aria-label="输入步骤">
      {steps.map((step, index) => {
        const Icon = step.icon;
        const isActive = step.id === currentStep;
        const isDone = index < currentIndex;
        return (
          <button
            className={isActive ? "step-button active" : isDone ? "step-button done" : "step-button"}
            key={step.id}
            type="button"
            onClick={() => onSelect(step.id)}
            disabled={index > currentIndex}
          >
            <Icon size={16} aria-hidden="true" />
            <span>{step.label}</span>
          </button>
        );
      })}
    </nav>
  );
}

type MethodCardProps = {
  icon: LucideIcon;
  title: string;
  description: string;
  actionLabel: string;
  disabled?: boolean;
  passive?: boolean;
  onClick?: () => void;
};

function MethodCard({
  icon: Icon,
  title,
  description,
  actionLabel,
  disabled,
  passive,
  onClick,
}: MethodCardProps) {
  const content = (
    <>
      <Icon size={20} aria-hidden="true" />
      <span>{title}</span>
      <small>{description}</small>
      <strong>{actionLabel}</strong>
    </>
  );

  if (passive) {
    return <article className="method-card passive">{content}</article>;
  }

  return (
    <button
      className={disabled ? "method-card disabled" : "method-card"}
      type="button"
      onClick={onClick}
      disabled={disabled}
    >
      {content}
    </button>
  );
}

function InputSummary({ form, pace }: { form: EditableAnalyzeRecoveryRequest; pace: string }) {
  const summaryGroups: Array<{
    title: string;
    items: Array<{ label: string; value: string }>;
  }> = [
    {
      title: "跑步负荷",
      items: [
        { label: "距离", value: `${formatCompactNumber(form.distance_km)} km` },
        { label: "时长", value: `${formatCompactNumber(form.duration_min)} min` },
        { label: "配速", value: `${pace}/km` },
        { label: "类型", value: runTypeLabel(form.run_type_main) },
        { label: "时间", value: runTimeLabel(form.run_time_period) },
        {
          label: "修饰",
          value:
            form.run_type_modifier.length > 0
              ? form.run_type_modifier.map(runModifierLabel).join("、")
              : "无",
        },
      ],
    },
    {
      title: "身体状态",
      items: [
        { label: "RPE", value: `${form.rpe}/10` },
        { label: "睡眠", value: `${formatCompactNumber(form.sleep_hours)} h` },
        { label: "疲劳", value: `${form.fatigue_level}/10` },
        { label: "酸痛", value: `${form.soreness_level}/10` },
        { label: "平均心率", value: form.avg_hr === null ? "未填" : `${Math.round(form.avg_hr)} bpm` },
        { label: "最大心率", value: form.max_hr === null ? "未填" : `${Math.round(form.max_hr)} bpm` },
      ],
    },
    {
      title: "恢复约束",
      items: [
        { label: "跑步水平", value: userLevelLabel(form.user_level) },
        {
          label: "饮食场景",
          value: dietOptions.find((option) => option.value === form.diet_preference)?.label ?? "正常饮食",
        },
        {
          label: "明日计划",
          value: tomorrowOptions.find((option) => option.value === form.tomorrow_plan)?.label ?? "未确定",
        },
        {
          label: "近 48h",
          value:
            past48hOptions.find((option) => option.value === form.past_48h_training)?.label ??
            form.past_48h_training,
        },
        {
          label: "异常信号",
          value:
            form.symptoms.length > 0
              ? form.symptoms.map(symptomLabel).join("、")
              : "无",
        },
      ],
    },
  ];

  return (
    <div className="input-summary-grid">
      {summaryGroups.map((group) => (
        <article className="summary-card" key={group.title}>
          <h3>{group.title}</h3>
          <dl className="summary-list">
            {group.items.map((item) => (
              <div className="summary-row" key={`${group.title}-${item.label}`}>
                <dt>{item.label}</dt>
                <dd>{item.value}</dd>
              </div>
            ))}
          </dl>
        </article>
      ))}
    </div>
  );
}

function ResultTabs({
  activeTab,
  onChange,
}: {
  activeTab: ResultTabId;
  onChange: (tab: ResultTabId) => void;
}) {
  return (
    <nav className="result-tabs" aria-label="结果模块">
      {resultTabs.map((tab) => {
        const Icon = tab.icon;
        return (
          <button
            className={tab.id === activeTab ? "tab-button active" : "tab-button"}
            key={tab.id}
            type="button"
            onClick={() => onChange(tab.id)}
          >
            <Icon size={16} aria-hidden="true" />
            <span>{tab.label}</span>
          </button>
        );
      })}
    </nav>
  );
}

type DemoCaseBarProps = {
  cases: DemoCase[];
  activeCaseId: string | null;
  onSelect: (demoCase: DemoCase) => void;
  disabled: boolean;
};

function DemoCaseBar({ cases, activeCaseId, onSelect, disabled }: DemoCaseBarProps) {
  return (
    <div className="demo-case-grid" aria-label="演示案例">
      {cases.map((demoCase) => (
        <button
          className={demoCase.id === activeCaseId ? "demo-case active" : "demo-case"}
          key={demoCase.id}
          type="button"
          onClick={() => onSelect(demoCase)}
          disabled={disabled}
        >
          <CheckCircle2 size={18} aria-hidden="true" />
          <span>{demoCase.name}</span>
          <small>{demoCase.summary}</small>
        </button>
      ))}
    </div>
  );
}

type ScreenshotUploadPanelProps = {
  status: ScreenshotStatus;
  previewUrl: string | null;
  result: RunScreenshotExtractResponse | null;
  error: string | null;
  touchedFields: string[];
  confirmed: boolean;
  onFileSelect: (file: File | null) => void;
  onConfirm: () => void;
};

function ScreenshotUploadPanel({
  status,
  previewUrl,
  result,
  error,
  touchedFields,
  confirmed,
  onFileSelect,
  onConfirm,
}: ScreenshotUploadPanelProps) {
  const extractedEntries = result
    ? Object.entries({
        distance_km: result.distance_km,
        duration_min: result.duration_min,
        pace: result.pace,
        run_type_guess: result.run_type_guess,
        run_time_period_guess: result.run_time_period_guess,
        avg_hr: result.avg_hr,
        max_hr: result.max_hr,
        calories: result.calories,
        elevation_gain: result.elevation_gain,
        source_app_guess: result.source_app_guess,
      }).filter(([, value]) => value !== null && value !== "")
    : [];
  const missingCount = result?.missing_fields.length ?? 0;

  return (
    <section className="screenshot-panel" aria-labelledby="screenshot-title">
      <div className="screenshot-copy">
        <div>
          <p className="eyebrow">Screenshot</p>
          <h3 id="screenshot-title">上传运动截图辅助填写</h3>
        </div>
        <p>自动识别距离、时长、心率等客观数据；RPE、疲劳、酸痛和明日计划仍需手动确认。</p>
      </div>

      <label className="screenshot-dropzone">
        <input
          type="file"
          accept="image/png,image/jpeg,image/webp"
          onChange={(event) => {
            onFileSelect(event.target.files?.[0] ?? null);
            event.target.value = "";
          }}
        />
        <Activity size={18} aria-hidden="true" />
        <span>{status === "extracting" ? "识别中..." : "选择 png / jpg / webp 截图"}</span>
      </label>

      {previewUrl ? (
        <div className="screenshot-preview">
          <img src={previewUrl} alt="运动截图预览" />
        </div>
      ) : null}

      <div className={`screenshot-status ${status}`}>
        {status === "idle" ? "未上传截图，可继续手动填写。" : null}
        {status === "extracting" ? (
          <>
            <Loader2 className="spin" size={16} aria-hidden="true" />
            <span>正在识别截图内容...</span>
          </>
        ) : null}
        {status === "success" ? (
          <>
            <CheckCircle2 size={16} aria-hidden="true" />
            <span>
              已回填 {touchedFields.length} 项客观字段
              {missingCount > 0 ? `，还有 ${missingCount} 项需要手动补充` : "，请检查后继续补全主观状态"}
            </span>
          </>
        ) : null}
        {status === "error" ? (
          <>
            <AlertTriangle size={16} aria-hidden="true" />
            <span>{error ?? "未能可靠识别截图内容，请手动填写跑步数据。"}</span>
          </>
        ) : null}
      </div>

      {result && extractedEntries.length > 0 ? (
        <div className="screenshot-result">
          {extractedEntries.map(([field, value]) => (
            <div key={field}>
              <span>{screenshotFieldLabels[field] ?? field}</span>
              <strong>{formatScreenshotValue(field, value)}</strong>
              <small>{Math.round((result.confidence[field] ?? 0) * 100)}%</small>
            </div>
          ))}
        </div>
      ) : null}

      {result && result.warnings.length > 0 ? (
        <ul className="screenshot-warnings">
          {result.warnings.map((warning) => (
            <li key={warning}>{warning}</li>
          ))}
        </ul>
      ) : null}

      {result ? (
        <div className="screenshot-actions">
          <button className="secondary-button compact" type="button" onClick={onConfirm}>
            <CheckCircle2 size={16} aria-hidden="true" />
            {confirmed ? "已确认，可继续分析" : "确认识别结果"}
          </button>
        </div>
      ) : null}
    </section>
  );
}

type HeaderMetricProps = {
  label: string;
  value: string;
  icon: LucideIcon;
};

function HeaderMetric({ label, value, icon: Icon }: HeaderMetricProps) {
  return (
    <div className="header-metric">
      <Icon size={16} aria-hidden="true" />
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

type FormSectionProps = {
  eyebrow: string;
  title: string;
  icon: LucideIcon;
  children: ReactNode;
};

function FormSection({ eyebrow, title, icon: Icon, children }: FormSectionProps) {
  return (
    <section className="form-section">
      <div className="form-section-heading">
        <div className="form-section-icon">
          <Icon size={18} aria-hidden="true" />
        </div>
        <div>
          <p className="eyebrow">{eyebrow}</p>
          <h3>{title}</h3>
        </div>
      </div>
      <div className="form-section-body">{children}</div>
    </section>
  );
}

type UserLevelFieldProps = {
  value: UserLevel;
  onChange: (value: UserLevel) => void;
};

function UserLevelField({ value, onChange }: UserLevelFieldProps) {
  return (
    <fieldset className="user-level-fieldset">
      <legend>跑步水平</legend>
      <div className="user-level-grid">
        {userLevelOptions.map((option) => (
          <button
            className={value === option.value ? "user-level-card active" : "user-level-card"}
            key={option.value}
            type="button"
            onClick={() => onChange(option.value)}
          >
            <span>{option.label}</span>
            <small>{option.description}</small>
          </button>
        ))}
      </div>
    </fieldset>
  );
}

type ModifierFieldsetProps = {
  options: Array<{ value: RunTypeModifier; label: string }>;
  selected: RunTypeModifier[];
  onToggle: (modifier: RunTypeModifier) => void;
};

function ModifierFieldset({ options, selected, onToggle }: ModifierFieldsetProps) {
  return (
    <fieldset className="symptom-fieldset">
      <legend>训练修饰</legend>
      <div className="symptom-grid modifier-grid">
        {options.map((modifier) => (
          <label className="checkbox-pill" key={modifier.value}>
            <input
              type="checkbox"
              checked={selected.includes(modifier.value)}
              onChange={() => onToggle(modifier.value)}
            />
            <span>{modifier.label}</span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}

type NumberFieldProps = {
  label: string;
  min: number;
  max: number;
  step: number;
  value: number | null;
  optional?: boolean;
  source?: string;
  onChange: (value: number | null) => void;
};

function NumberField({ label, min, max, step, value, optional, source, onChange }: NumberFieldProps) {
  return (
    <label className="field">
      <span>{label}</span>
      <input
        type="number"
        min={min}
        max={max}
        step={step}
        value={value ?? ""}
        placeholder={optional ? "选填" : undefined}
        required={!optional}
        inputMode={step < 1 ? "decimal" : "numeric"}
        onChange={(event) => {
          const nextValue = event.target.value;
          onChange(nextValue === "" ? null : Number(nextValue));
        }}
      />
      {source ? <small className="field-source">{source}</small> : null}
    </label>
  );
}

type SelectFieldProps = {
  label: string;
  value: string;
  options: Array<{ value: string; label: string }>;
  source?: string;
  onChange: (value: string) => void;
};

function SelectField({ label, value, options, source, onChange }: SelectFieldProps) {
  return (
    <label className="field">
      <span>{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      {source ? <small className="field-source">{source}</small> : null}
    </label>
  );
}

type RangeFieldProps = {
  label: string;
  value: number;
  hint?: string;
  onChange: (value: number) => void;
};

function RangeField({ label, value, hint, onChange }: RangeFieldProps) {
  return (
    <label className="range-field">
      <span>
        {label}
        <strong>{value}</strong>
      </span>
      <input
        type="range"
        min={1}
        max={10}
        step={1}
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
      />
      {hint ? <small>{hint}</small> : null}
    </label>
  );
}

type RpeSliderProps = {
  value: number;
  onChange: (value: number) => void;
};

function RpeSlider({ value, onChange }: RpeSliderProps) {
  const label = getRpeLabel(value);
  return (
    <div className="rpe-block">
      <div className="rpe-header">
        <div>
          <span>RPE 主观用力</span>
          <strong>{value}/10</strong>
          <small>核心输入 · 用身体反馈校准恢复压力</small>
        </div>
        <p>{label}</p>
      </div>
      <input
        aria-label="RPE 主观用力"
        type="range"
        min={1}
        max={10}
        step={1}
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
      />
      <div className="scale-row" aria-hidden="true">
        <span>轻松</span>
        <span>中等</span>
        <span>很吃力</span>
      </div>
    </div>
  );
}

type ResultViewProps = {
  result: AnalyzeRecoveryResponse;
  activeTab: ResultTabId;
  feedback: FeedbackRequest;
  feedbackStatus: "idle" | "submitting" | "sent" | "error";
  onFeedbackChange: (feedback: FeedbackRequest) => void;
  onFeedbackSubmit: () => void;
};

function ResultView({
  result,
  activeTab,
  feedback,
  feedbackStatus,
  onFeedbackChange,
  onFeedbackSubmit,
}: ResultViewProps) {
  const adviceItems: Array<{
    key: "diet" | "hydration" | "sleep" | "relaxation" | "tomorrow";
    icon: LucideIcon;
    tone: string;
  }> = [
    { key: "diet", icon: Utensils, tone: "diet" },
    { key: "hydration", icon: Droplets, tone: "hydration" },
    { key: "sleep", icon: Moon, tone: "sleep" },
    { key: "relaxation", icon: HeartPulse, tone: "relaxation" },
    { key: "tomorrow", icon: CalendarClock, tone: "tomorrow" },
  ];

  return (
    <div className="result-content">
      {activeTab === "summary" ? <ResultSummary result={result} /> : null}
      {activeTab === "plan" ? <ResultPlan result={result} adviceItems={adviceItems} /> : null}
      {activeTab === "details" ? <ResultDetails result={result} /> : null}

      <div className="result-footer">
        <FeedbackPanel
          feedback={feedback}
          status={feedbackStatus}
          onChange={onFeedbackChange}
          onSubmit={onFeedbackSubmit}
        />
        <p className="safety-note">{result.advice.safety_note}</p>
      </div>
    </div>
  );
}

function ResultSummary({ result }: { result: AnalyzeRecoveryResponse }) {
  const scoreColor = getScoreColor(result.score);
  const headline = getRecoveryHeadline(result.score);

  return (
    <div className="result-tab-panel">
      <TomorrowDecisionCard result={result} />

      <section className="result-hero" aria-label="恢复压力概览">
        <div className="score-gauge-card">
          <ScoreRing score={result.score} level={result.level} />
          <span>Recovery pressure</span>
        </div>
        <div className="result-hero-copy">
          <span className="risk-badge" style={{ borderColor: scoreColor, color: scoreColor }}>
            {result.level}
          </span>
          <h3>{headline}</h3>
          <p>{result.advice.summary}</p>
          <div className="result-stat-grid">
            <div>
              <span>关键原因</span>
              <strong>{result.reasons.length} 项</strong>
            </div>
            <div>
              <span>Session load</span>
              <strong>{result.derived_metrics.session_load ?? 0}</strong>
            </div>
            <div>
              <span>建议状态</span>
              <strong>{result.recommendation_meta.used_fallback ? "模板兜底" : "已校验"}</strong>
            </div>
          </div>
        </div>
      </section>

      {result.safety_flags.length > 0 ? <SafetyBanner flags={result.safety_flags} /> : null}
    </div>
  );
}

function ResultPlan({
  result,
  adviceItems,
}: {
  result: AnalyzeRecoveryResponse;
  adviceItems: Array<{
    key: "diet" | "hydration" | "sleep" | "relaxation" | "tomorrow";
    icon: LucideIcon;
    tone: string;
  }>;
}) {
  return (
    <div className="result-tab-panel">
      <RecoveryTimeline items={result.timeline} />

      <section className="content-block" aria-labelledby="advice-title">
        <div className="block-heading">
          <div>
            <p className="eyebrow">Recovery</p>
            <h3 id="advice-title">恢复建议</h3>
          </div>
        </div>
        <div className="advice-grid">
          {adviceItems.map(({ key, icon: Icon, tone }) => {
            const item = result.advice[key] as AdviceItem;
            return (
              <AdviceCard
                key={key}
                icon={Icon}
                tone={tone}
                title={item.title}
                content={item.content}
              />
            );
          })}
        </div>
      </section>
    </div>
  );
}

function ResultDetails({ result }: { result: AnalyzeRecoveryResponse }) {
  return (
    <div className="result-tab-panel">
      <section className="content-block" aria-labelledby="reasons-title">
        <div className="block-heading">
          <div>
            <p className="eyebrow">Drivers</p>
            <h3 id="reasons-title">主要原因</h3>
          </div>
        </div>
        <div className="reason-grid">
          {result.reasons.map((reason, index) => (
            <article className="reason-item" key={`${reason.factor}-${reason.impact}`}>
              <div className="reason-topline">
                <span className="reason-rank">{String(index + 1).padStart(2, "0")}</span>
                <span>{reason.factor}</span>
                <strong>+{reason.impact}</strong>
              </div>
              <p>{reason.text}</p>
            </article>
          ))}
        </div>
      </section>

      <ComponentBreakdown componentScores={result.component_scores} />

      <div className="details-grid">
        <DetailList title="Derived metrics" entries={result.derived_metrics} />
        <DetailList title="Recommendation meta" entries={{ ...result.recommendation_meta }} />
      </div>
    </div>
  );
}

function DetailList({ title, entries }: { title: string; entries: Record<string, unknown> }) {
  return (
    <section className="detail-card">
      <div className="minor-heading">{title}</div>
      <dl className="detail-list">
        {Object.entries(entries).map(([key, value]) => (
          <div className="detail-row" key={key}>
            <dt>{key}</dt>
            <dd>{formatDetailValue(value)}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

function TomorrowDecisionCard({ result }: { result: AnalyzeRecoveryResponse }) {
  const color = getScoreColor(result.score);
  return (
    <section className="tomorrow-decision-card" aria-labelledby="tomorrow-decision-title">
      <div className="decision-icon" style={{ color }}>
        <CalendarClock size={22} aria-hidden="true" />
      </div>
      <div>
        <p className="eyebrow">Tomorrow decision</p>
        <h3 id="tomorrow-decision-title">{result.advice.tomorrow.title}</h3>
        <p>{result.advice.tomorrow.content}</p>
      </div>
      <span className="decision-level" style={{ borderColor: color, color }}>
        {result.level}
      </span>
    </section>
  );
}

function ScoreRing({ score, level }: { score: number; level: string }) {
  const color = getScoreColor(score);
  return (
    <div
      className="score-ring"
      style={{ background: `conic-gradient(${color} ${score * 3.6}deg, #dbe3e9 0deg)` }}
      aria-label={`恢复压力 ${score} 分，${level}`}
    >
      <div className="score-ring-inner">
        <strong>{score}</strong>
        <span>/100</span>
      </div>
    </div>
  );
}

function getScoreColor(score: number) {
  if (score >= 81) {
    return "#c43127";
  }
  if (score >= 61) {
    return "#c66a11";
  }
  if (score >= 31) {
    return "#286a99";
  }
  return "#16805e";
}

function getRecoveryHeadline(score: number) {
  if (score >= 81) {
    return "高负荷，优先降载恢复";
  }
  if (score >= 61) {
    return "恢复优先，明日训练需保守";
  }
  if (score >= 31) {
    return "适度恢复，保留低强度活动";
  }
  return "恢复压力较低，可以常规调整";
}

function SafetyBanner({ flags }: { flags: string[] }) {
  return (
    <div className="safety-banner" role="alert">
      <ShieldAlert size={20} aria-hidden="true" />
      <div>
        <strong>安全提示</strong>
        {flags.map((flag) => (
          <p key={flag}>{flag}</p>
        ))}
      </div>
    </div>
  );
}

function ComponentBreakdown({ componentScores }: { componentScores: Record<string, number> }) {
  const entries = Object.entries(componentScores).filter(([, value]) => value > 0);
  const maxValue = Math.max(...entries.map(([, value]) => value), 1);

  if (entries.length === 0) {
    return null;
  }

  return (
    <section className="content-block breakdown" aria-labelledby="breakdown-title">
      <div className="block-heading compact">
        <div>
          <p className="eyebrow">Breakdown</p>
          <h3 id="breakdown-title">分项贡献</h3>
        </div>
      </div>
      <div className="breakdown-list">
        {entries.map(([key, value]) => (
          <div className="breakdown-item" key={key}>
            <span>{componentLabels[key] ?? key}</span>
            <div className="bar-track" aria-hidden="true">
              <div className="bar-fill" style={{ width: `${(value / maxValue) * 100}%` }} />
            </div>
            <strong>{value}</strong>
          </div>
        ))}
      </div>
    </section>
  );
}

type AdviceCardProps = {
  icon: LucideIcon;
  tone: string;
  title: string;
  content: string;
};

function AdviceCard({ icon: Icon, tone, title, content }: AdviceCardProps) {
  return (
    <article className={`advice-card advice-card-${tone}`}>
      <div className="advice-icon">
        <Icon size={20} aria-hidden="true" />
      </div>
      <div>
        <h3>{title}</h3>
        <p>{content}</p>
      </div>
    </article>
  );
}

function RecoveryTimeline({ items }: { items: TimelineItem[] }) {
  return (
    <section className="content-block timeline-block" aria-labelledby="timeline-title">
      <div className="block-heading">
        <div>
          <p className="eyebrow">Next 24h</p>
          <h3 id="timeline-title">24 小时时间轴</h3>
        </div>
      </div>
      <ol className="timeline">
        {items.map((item) => (
          <li className="timeline-item" key={`${item.time}-${item.action}`}>
            <time>{item.time}</time>
            <span className="timeline-dot" aria-hidden="true" />
            <p>{item.action}</p>
          </li>
        ))}
      </ol>
    </section>
  );
}

type FeedbackPanelProps = {
  feedback: FeedbackRequest;
  status: "idle" | "submitting" | "sent" | "error";
  onChange: (feedback: FeedbackRequest) => void;
  onSubmit: () => void;
};

function FeedbackPanel({ feedback, status, onChange, onSubmit }: FeedbackPanelProps) {
  return (
    <section className="feedback-panel" aria-labelledby="feedback-title">
      <div className="minor-heading" id="feedback-title">
        建议反馈
      </div>
      <ChoiceGroup
        label="帮助度"
        value={feedback.helpfulness_rating}
        options={[
          { value: "helpful", label: "有帮助" },
          { value: "neutral", label: "一般" },
          { value: "not_helpful", label: "没帮助" },
        ]}
        onChange={(value) =>
          onChange({ ...feedback, helpfulness_rating: value as FeedbackRequest["helpfulness_rating"] })
        }
      />
      <ChoiceGroup
        label="次日状态"
        value={feedback.next_day_status}
        options={[
          { value: "not_recorded", label: "未记录" },
          { value: "recovered", label: "恢复良好" },
          { value: "still_tired", label: "仍疲劳" },
          { value: "soreness_worse", label: "酸痛加重" },
        ]}
        onChange={(value) =>
          onChange({ ...feedback, next_day_status: value as FeedbackRequest["next_day_status"] })
        }
      />
      <ChoiceGroup
        label="是否执行"
        value={feedback.followed_advice}
        options={[
          { value: "partial", label: "部分执行" },
          { value: "yes", label: "是" },
          { value: "no", label: "否" },
        ]}
        onChange={(value) =>
          onChange({ ...feedback, followed_advice: value as FeedbackRequest["followed_advice"] })
        }
      />
      <div className="feedback-actions">
        <button
          className="secondary-button"
          type="button"
          onClick={onSubmit}
          disabled={status === "submitting" || status === "sent"}
        >
          <CheckCircle2 size={18} aria-hidden="true" />
          {status === "submitting" ? "提交中" : status === "sent" ? "已提交" : "提交反馈"}
        </button>
        {status === "error" ? <span role="alert">反馈提交失败</span> : null}
      </div>
    </section>
  );
}

type ChoiceGroupProps = {
  label: string;
  value: string;
  options: Array<{ value: string; label: string }>;
  onChange: (value: string) => void;
};

function ChoiceGroup({ label, value, options, onChange }: ChoiceGroupProps) {
  return (
    <div className="choice-group">
      <span>{label}</span>
      <div>
        {options.map((option) => (
          <button
            className={value === option.value ? "choice-button active" : "choice-button"}
            key={option.value}
            type="button"
            onClick={() => onChange(option.value)}
          >
            {option.label}
          </button>
        ))}
      </div>
    </div>
  );
}

function HistoryPanel({ items, error }: { items: RecoveryHistoryItem[]; error: string | null }) {
  const trendItems = [...items].reverse();

  return (
    <section className="history-panel" aria-labelledby="history-title">
      <div className="history-heading">
        <div>
          <div className="minor-heading" id="history-title">
            最近 7 次记录
          </div>
          <p>恢复压力走势</p>
        </div>
        {trendItems.length > 0 ? (
          <div className="history-trend" aria-label="最近恢复压力走势">
            {trendItems.map((item) => (
              <span
                key={item.recovery_id}
                title={`${formatHistoryDate(item.created_at)} · ${item.score}`}
                style={{
                  height: `${Math.max(16, item.score)}%`,
                  background: getScoreColor(item.score),
                }}
              />
            ))}
          </div>
        ) : null}
      </div>
      {error ? <p className="history-error">历史记录加载失败：{error}</p> : null}
      {!error && items.length === 0 ? <p className="history-empty">暂无记录</p> : null}
      <div className="history-list">
        {items.map((item) => (
          <article className="history-item" key={item.recovery_id}>
            <div className="history-score" style={{ color: getScoreColor(item.score) }}>
              <strong>{item.score}</strong>
              <span>{item.level}</span>
            </div>
            <div>
              <time>{formatHistoryDate(item.created_at)}</time>
              <p>
                {runTypeLabel(item.run_type_main)}
                {item.run_type_modifier.length > 0
                  ? ` · ${item.run_type_modifier.map(runModifierLabel).join("、")}`
                  : ""}{" "}
                · RPE {item.rpe} · {formatCompactNumber(item.distance_km)}km /{" "}
                {formatCompactNumber(item.duration_min)}min
              </p>
              <small>{item.tomorrow_advice}</small>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function getRpeLabel(value: number) {
  if (value <= 2) {
    return "非常轻松，可以完整聊天";
  }
  if (value <= 4) {
    return "轻松到中等，呼吸略快";
  }
  if (value <= 6) {
    return "有一定吃力，需要专注维持";
  }
  if (value <= 8) {
    return "明显吃力，说话困难";
  }
  return "接近极限或拼尽全力";
}

function getFatigueLabel(value: number) {
  if (value <= 3) {
    return "几乎不累";
  }
  if (value <= 7) {
    return "有明显疲劳，但不影响正常活动";
  }
  return "只想休息，不适合继续训练";
}

function getSorenessLabel(value: number) {
  if (value <= 3) {
    return "无明显酸痛";
  }
  if (value <= 7) {
    return "能感受到，但不影响正常走路";
  }
  return "影响上下楼或正常步态";
}

function runTypeLabel(value: string) {
  return (
    runTypeOptions.find((option) => option.value === value)?.label ??
    value
  );
}

function runTimeLabel(value: string) {
  return runTimeOptions.find((option) => option.value === value)?.label ?? value;
}

function userLevelLabel(value: string) {
  return userLevelOptions.find((option) => option.value === value)?.label ?? value;
}

function runModifierLabel(value: string) {
  return (
    runTypeModifierOptions.find((option) => option.value === value)?.label ??
    value
  );
}

function symptomLabel(value: string) {
  return symptomOptions.find((option) => option.value === value)?.label ?? value;
}

function formatDetailValue(value: unknown) {
  if (value === null || value === undefined) {
    return "null";
  }
  if (typeof value === "boolean") {
    return value ? "true" : "false";
  }
  if (typeof value === "number") {
    return formatCompactNumber(value);
  }
  return String(value);
}

function formatHistoryDate(value: string) {
  return value.slice(0, 16).replace("T", " ");
}

function formatCompactNumber(value: number | null) {
  if (value === null) {
    return "--";
  }
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}

export default App;
