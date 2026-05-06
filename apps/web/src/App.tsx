import { useMemo, useState, type FormEvent } from "react";
import {
  Activity,
  AlertTriangle,
  CalendarClock,
  CheckCircle2,
  Clock3,
  Droplets,
  HeartPulse,
  Loader2,
  Moon,
  RotateCcw,
  ShieldAlert,
  Utensils,
  Zap,
  type LucideIcon,
} from "lucide-react";

import { analyzeRecovery } from "./lib/api";
import { demoCases } from "./lib/demoCases";
import type {
  AdviceItem,
  AnalyzeRecoveryRequest,
  AnalyzeRecoveryResponse,
  DemoCase,
  DietPreference,
  RunTimePeriod,
  RunType,
  TimelineItem,
  TomorrowPlan,
} from "./lib/types";

const defaultPayload: AnalyzeRecoveryRequest = {
  distance_km: 8,
  duration_min: 48,
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
  symptoms: [],
};

const runTypeOptions: Array<{ value: RunType; label: string }> = [
  { value: "easy", label: "轻松跑" },
  { value: "tempo", label: "节奏跑" },
  { value: "interval", label: "间歇跑" },
  { value: "long", label: "长距离跑" },
  { value: "race", label: "比赛" },
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
  { value: "easy", label: "轻松跑" },
  { value: "intensity", label: "强度课" },
  { value: "long", label: "长距离" },
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
  run_type: "类型",
  rpe: "RPE",
  heart_rate: "心率",
  sleep: "睡眠",
  fatigue: "疲劳",
  soreness: "酸痛",
  time: "时间",
  tomorrow_conflict: "明日冲突",
};

function App() {
  const [form, setForm] = useState<AnalyzeRecoveryRequest>(defaultPayload);
  const [result, setResult] = useState<AnalyzeRecoveryResponse | null>(null);
  const [activeCaseId, setActiveCaseId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const updateField = <K extends keyof AnalyzeRecoveryRequest>(
    field: K,
    value: AnalyzeRecoveryRequest[K],
  ) => {
    setForm((current) => ({ ...current, [field]: value }));
    setActiveCaseId(null);
  };

  const runAnalyze = async (payload: AnalyzeRecoveryRequest) => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await analyzeRecovery(payload);
      setResult(response);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "分析请求失败");
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    void runAnalyze(form);
  };

  const handleDemoCase = (demoCase: DemoCase) => {
    setForm(demoCase.payload);
    setActiveCaseId(demoCase.id);
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

  const pace = useMemo(() => {
    if (!form.distance_km) {
      return "0:00";
    }
    const totalSeconds = Math.round((form.duration_min * 60) / form.distance_km);
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = String(totalSeconds % 60).padStart(2, "0");
    return `${minutes}:${seconds}`;
  }, [form.distance_km, form.duration_min]);

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">RunRecover MVP</p>
          <h1>跑后恢复分析</h1>
        </div>
        <div className="status-pill">
          <Activity size={18} aria-hidden="true" />
          <span>RPE v0.2</span>
        </div>
      </header>

      <main className="workspace">
        <section className="input-panel" aria-labelledby="input-title">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Input</p>
              <h2 id="input-title">本次跑步</h2>
            </div>
            <div className="pace-badge">
              <Clock3 size={16} aria-hidden="true" />
              <span>{pace}/km</span>
            </div>
          </div>

          <DemoCaseBar
            cases={demoCases}
            activeCaseId={activeCaseId}
            onSelect={handleDemoCase}
            disabled={isLoading}
          />

          <form className="input-form" onSubmit={handleSubmit}>
            <div className="field-grid two-columns">
              <NumberField
                label="距离 km"
                min={0.5}
                max={60}
                step={0.1}
                value={form.distance_km}
                onChange={(value) => updateField("distance_km", value ?? 0.5)}
              />
              <NumberField
                label="时长 min"
                min={5}
                max={360}
                step={1}
                value={form.duration_min}
                onChange={(value) => updateField("duration_min", value ?? 5)}
              />
            </div>

            <div className="field-grid two-columns">
              <SelectField
                label="跑步类型"
                value={form.run_type}
                options={runTypeOptions}
                onChange={(value) => updateField("run_type", value as RunType)}
              />
              <SelectField
                label="跑步时间"
                value={form.run_time_period}
                options={runTimeOptions}
                onChange={(value) => updateField("run_time_period", value as RunTimePeriod)}
              />
            </div>

            <RpeSlider value={form.rpe} onChange={(value) => updateField("rpe", value)} />

            <div className="field-grid three-columns">
              <NumberField
                label="睡眠 h"
                min={0}
                max={14}
                step={0.1}
                value={form.sleep_hours}
                onChange={(value) => updateField("sleep_hours", value ?? 0)}
              />
              <RangeField
                label="疲劳"
                value={form.fatigue_level}
                onChange={(value) => updateField("fatigue_level", value)}
              />
              <RangeField
                label="酸痛"
                value={form.soreness_level}
                onChange={(value) => updateField("soreness_level", value)}
              />
            </div>

            <div className="field-grid two-columns">
              <NumberField
                label="平均心率"
                min={40}
                max={230}
                step={1}
                value={form.avg_hr ?? ""}
                optional
                onChange={(value) => updateField("avg_hr", value)}
              />
              <NumberField
                label="最大心率"
                min={40}
                max={230}
                step={1}
                value={form.max_hr ?? ""}
                optional
                onChange={(value) => updateField("max_hr", value)}
              />
            </div>

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

            {error ? (
              <div className="error-banner" role="alert">
                <AlertTriangle size={18} aria-hidden="true" />
                <span>后端请求失败：{error}</span>
              </div>
            ) : null}

            <div className="form-actions">
              <button
                className="secondary-button"
                type="button"
                onClick={() => {
                  setForm(defaultPayload);
                  setResult(null);
                  setError(null);
                  setActiveCaseId(null);
                }}
              >
                <RotateCcw size={18} aria-hidden="true" />
                重置
              </button>
              <button className="primary-button" type="submit" disabled={isLoading}>
                {isLoading ? (
                  <Loader2 className="spin" size={18} aria-hidden="true" />
                ) : (
                  <Zap size={18} aria-hidden="true" />
                )}
                开始分析
              </button>
            </div>
          </form>
        </section>

        <section className="result-panel" aria-labelledby="result-title">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Output</p>
              <h2 id="result-title">恢复结果</h2>
            </div>
            {result ? <span className="record-id">#{result.recovery_id}</span> : null}
          </div>

          {result ? <ResultView result={result} /> : <EmptyResult />}
        </section>
      </main>
    </div>
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

type NumberFieldProps = {
  label: string;
  min: number;
  max: number;
  step: number;
  value: number | "";
  optional?: boolean;
  onChange: (value: number | null) => void;
};

function NumberField({ label, min, max, step, value, optional, onChange }: NumberFieldProps) {
  return (
    <label className="field">
      <span>{label}</span>
      <input
        type="number"
        min={min}
        max={max}
        step={step}
        value={value}
        placeholder={optional ? "选填" : undefined}
        required={!optional}
        onChange={(event) => {
          const nextValue = event.target.value;
          onChange(nextValue === "" ? null : Number(nextValue));
        }}
      />
    </label>
  );
}

type SelectFieldProps = {
  label: string;
  value: string;
  options: Array<{ value: string; label: string }>;
  onChange: (value: string) => void;
};

function SelectField({ label, value, options, onChange }: SelectFieldProps) {
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
    </label>
  );
}

type RangeFieldProps = {
  label: string;
  value: number;
  onChange: (value: number) => void;
};

function RangeField({ label, value, onChange }: RangeFieldProps) {
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

function ResultView({ result }: { result: AnalyzeRecoveryResponse }) {
  const adviceItems: Array<{
    key: "diet" | "hydration" | "sleep" | "relaxation" | "tomorrow";
    icon: LucideIcon;
  }> = [
    { key: "diet", icon: Utensils },
    { key: "hydration", icon: Droplets },
    { key: "sleep", icon: Moon },
    { key: "relaxation", icon: HeartPulse },
    { key: "tomorrow", icon: CalendarClock },
  ];

  return (
    <div className="result-content">
      <div className="score-row">
        <ScoreRing score={result.score} level={result.level} />
        <div className="summary-block">
          <p>{result.advice.summary}</p>
          <div className="level-tags">
            <span>{result.level}</span>
            <span>{result.reasons.length} 个主要原因</span>
          </div>
        </div>
      </div>

      {result.safety_flags.length > 0 ? <SafetyBanner flags={result.safety_flags} /> : null}

      <div className="reason-grid">
        {result.reasons.map((reason) => (
          <article className="reason-item" key={`${reason.factor}-${reason.impact}`}>
            <div>
              <span>{reason.factor}</span>
              <strong>+{reason.impact}</strong>
            </div>
            <p>{reason.text}</p>
          </article>
        ))}
      </div>

      <ComponentBreakdown componentScores={result.component_scores} />

      <div className="advice-grid">
        {adviceItems.map(({ key, icon: Icon }) => {
          const item = result.advice[key] as AdviceItem;
          return (
            <AdviceCard key={key} icon={Icon} title={item.title} content={item.content} />
          );
        })}
      </div>

      <RecoveryTimeline items={result.timeline} />

      <p className="safety-note">{result.advice.safety_note}</p>
    </div>
  );
}

function ScoreRing({ score, level }: { score: number; level: string }) {
  const color = score >= 81 ? "#b42318" : score >= 61 ? "#b35a00" : score >= 31 ? "#2f5f90" : "#1f7a58";
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

  return (
    <div className="breakdown">
      <div className="minor-heading">分项贡献</div>
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
    </div>
  );
}

type AdviceCardProps = {
  icon: LucideIcon;
  title: string;
  content: string;
};

function AdviceCard({ icon: Icon, title, content }: AdviceCardProps) {
  return (
    <article className="advice-card">
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
    <div className="timeline-block">
      <div className="minor-heading">24 小时时间轴</div>
      <ol className="timeline">
        {items.map((item) => (
          <li className="timeline-item" key={`${item.time}-${item.action}`}>
            <time>{item.time}</time>
            <p>{item.action}</p>
          </li>
        ))}
      </ol>
    </div>
  );
}

function EmptyResult() {
  return (
    <div className="empty-result">
      <Activity size={30} aria-hidden="true" />
      <h3>等待分析</h3>
      <p>结果将在这里显示。</p>
    </div>
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

export default App;
