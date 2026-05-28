from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.repositories.recovery_repo import (
    init_database,
    list_recent_history,
    save_analysis,
    save_feedback,
)
from app.schemas import (
    AnalyzeRecoveryRequest,
    AnalyzeRecoveryResponse,
    FeedbackRequest,
    FeedbackResponse,
    HealthResponse,
    RecommendationMeta,
    RecoveryHistoryItem,
)
from app.services.llm import get_recommendation_provider
from app.services.reasons import build_reasons
from app.services.safety import evaluate_safety
from app.services.scoring import calculate_score


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_database()
    yield


settings = get_settings()
app = FastAPI(title="RunRecover API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="runrecover-api")


@app.post("/api/recovery/analyze", response_model=AnalyzeRecoveryResponse)
def analyze_recovery(run_input: AnalyzeRecoveryRequest) -> AnalyzeRecoveryResponse:
    settings = get_settings()
    score_result = calculate_score(run_input)
    safety_flags = evaluate_safety(run_input)
    reasons = build_reasons(run_input, score_result)
    provider = get_recommendation_provider(settings.llm_provider)
    advice = provider.generate(run_input, score_result, safety_flags, reasons)
    recommendation_meta = getattr(
        provider,
        "last_metadata",
        RecommendationMeta(
            llm_provider=settings.llm_provider,
            llm_model=None,
            prompt_version="recovery_reasons_v0.4",
        ),
    )
    recovery_id = save_analysis(
        run_input=run_input,
        score_result=score_result,
        reasons=[reason.model_dump() for reason in reasons],
        advice=advice,
        safety_flags=safety_flags,
        recommendation_meta=recommendation_meta,
    )

    return AnalyzeRecoveryResponse(
        recovery_id=recovery_id,
        score=score_result.score,
        level=score_result.level,
        component_scores=score_result.component_scores,
        derived_metrics=score_result.derived_metrics,
        reasons=reasons,
        advice=advice,
        timeline=advice.timeline,
        safety_flags=safety_flags,
        recommendation_meta=recommendation_meta,
    )


@app.get("/api/recovery/history", response_model=list[RecoveryHistoryItem])
def recovery_history(limit: int = Query(default=7, ge=1, le=20)) -> list[RecoveryHistoryItem]:
    return list_recent_history(limit=limit)


@app.post("/api/recovery/{recovery_id}/feedback", response_model=FeedbackResponse)
def create_feedback(recovery_id: int, feedback: FeedbackRequest) -> FeedbackResponse:
    try:
        feedback_id = save_feedback(recovery_id, feedback)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return FeedbackResponse(feedback_id=feedback_id, recovery_id=recovery_id)
