from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.repositories.recovery_repo import init_database, save_analysis
from app.schemas import (
    AnalyzeRecoveryRequest,
    AnalyzeRecoveryResponse,
    HealthResponse,
)
from app.services.llm import get_recommendation_provider
from app.services.reasons import build_reasons
from app.services.safety import evaluate_safety
from app.services.scoring import calculate_score


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_database()
    yield


app = FastAPI(title="RunRecover API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
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
    advice = provider.generate(run_input, score_result, safety_flags)
    recovery_id = save_analysis(
        run_input=run_input,
        score_result=score_result,
        reasons=[reason.model_dump() for reason in reasons],
        advice=advice,
        safety_flags=safety_flags,
    )

    return AnalyzeRecoveryResponse(
        recovery_id=recovery_id,
        score=score_result.score,
        level=score_result.level,
        component_scores=score_result.component_scores,
        reasons=reasons,
        advice=advice,
        timeline=advice.timeline,
        safety_flags=safety_flags,
    )
