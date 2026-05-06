from __future__ import annotations

from app.schemas import AnalyzeRecoveryRequest, RecoveryAdvice, ScoreResult
from app.services.recommendations import build_template_recommendation


class RecommendationProvider:
    def generate(
        self,
        run_input: AnalyzeRecoveryRequest,
        score_result: ScoreResult,
        safety_flags: list[str],
    ) -> RecoveryAdvice:
        raise NotImplementedError


class TemplateRecommendationProvider(RecommendationProvider):
    def generate(
        self,
        run_input: AnalyzeRecoveryRequest,
        score_result: ScoreResult,
        safety_flags: list[str],
    ) -> RecoveryAdvice:
        return build_template_recommendation(run_input, score_result, safety_flags)


def get_recommendation_provider(provider_name: str) -> RecommendationProvider:
    # The MVP keeps external LLM calls disabled for demo stability.
    # This interface stays small so a real JSON LLM provider can be added later.
    return TemplateRecommendationProvider()
