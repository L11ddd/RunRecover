from app.services.llm import (
    AnthropicRecommendationProvider,
    DeepSeekRecommendationProvider,
    OpenAIRecommendationProvider,
    _extract_content_from_response,
    TemplateRecommendationProvider,
    _build_user_prompt,
    get_recommendation_provider,
)
from app.schemas import AnalyzeRecoveryRequest
from app.services.reasons import build_reasons
from app.services.scoring import calculate_score


def test_llm_provider_selection(monkeypatch):
    assert isinstance(get_recommendation_provider("template"), TemplateRecommendationProvider)

    monkeypatch.setenv("RUNRECOVER_LLM_API_KEY", "test-key")
    assert isinstance(get_recommendation_provider("deepseek"), DeepSeekRecommendationProvider)
    assert isinstance(get_recommendation_provider("openai"), OpenAIRecommendationProvider)
    assert isinstance(get_recommendation_provider("gpt"), OpenAIRecommendationProvider)
    assert isinstance(get_recommendation_provider("anthropic"), AnthropicRecommendationProvider)
    assert isinstance(get_recommendation_provider("claude"), AnthropicRecommendationProvider)


def test_llm_provider_requires_api_key(monkeypatch):
    monkeypatch.delenv("RUNRECOVER_LLM_API_KEY", raising=False)
    try:
        get_recommendation_provider("openai")
        raise AssertionError("Expected OpenAI provider creation to fail without API key")
    except RuntimeError as exc:
        assert "RUNRECOVER_LLM_API_KEY" in str(exc)


def test_llm_prompt_includes_user_level_and_conservativeness():
    run_input = AnalyzeRecoveryRequest(
        distance_km=8,
        duration_min=48,
        run_type="tempo",
        run_time_period="night",
        rpe=8,
        sleep_hours=5.8,
        fatigue_level=7,
        soreness_level=5,
        tomorrow_plan="intensity",
        user_level="beginner",
        symptoms=[],
    )
    score_result = calculate_score(run_input)
    reasons = build_reasons(run_input, score_result)

    prompt = _build_user_prompt(run_input, score_result, [], reasons)

    assert "用户画像 user_level：beginner" in prompt
    assert "建议保守程度：conservative" in prompt
    assert "不大幅改变恢复分数" in prompt


def test_anthropic_messages_response_text_is_extracted():
    content = _extract_content_from_response(
        {
            "id": "msg_test",
            "type": "message",
            "role": "assistant",
            "content": [
                {
                    "type": "text",
                    "text": '{"summary":"ok"}',
                }
            ],
        }
    )

    assert content == '{"summary":"ok"}'

    try:
        get_recommendation_provider("anthropic")
        raise AssertionError("Expected Anthropic provider creation to fail without API key")
    except RuntimeError as exc:
        assert "RUNRECOVER_LLM_API_KEY" in str(exc)
