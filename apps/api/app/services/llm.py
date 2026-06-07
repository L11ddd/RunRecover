from __future__ import annotations

import json
import logging
import time
from typing import Any

from app.schemas import (
    AnalyzeRecoveryRequest,
    Reason,
    RecommendationMeta,
    RecoveryAdvice,
    ScoreResult,
)
from app.services.recommendations import (
    SAFETY_NOTE,
    build_template_recommendation,
    get_advice_conservativeness,
    validate_recommendation_content,
)

logger = logging.getLogger(__name__)
PROMPT_VERSION = "recovery_reasons_v0.4"


# ──────────────────────────────────────────────
# 抽象基类：所有推荐引擎都必须实现 generate 方法
# ──────────────────────────────────────────────
class RecommendationProvider:
    last_metadata = RecommendationMeta(
        llm_provider="template",
        llm_model=None,
        prompt_version=PROMPT_VERSION,
    )

    def generate(
        self,
        run_input: AnalyzeRecoveryRequest,
        score_result: ScoreResult,
        safety_flags: list[str],
        reasons: list[Reason],
    ) -> RecoveryAdvice:
        raise NotImplementedError


# ──────────────────────────────────────────────
# 模板引擎：纯规则 if-else，不调用任何外部 API
# 适合演示、离线环境，或作为 LLM 失败时的兜底
# ──────────────────────────────────────────────
class TemplateRecommendationProvider(RecommendationProvider):
    def generate(
        self,
        run_input: AnalyzeRecoveryRequest,
        score_result: ScoreResult,
        safety_flags: list[str],
        reasons: list[Reason],
    ) -> RecoveryAdvice:
        advice = build_template_recommendation(run_input, score_result, safety_flags, reasons)
        validation_passed, _ = validate_recommendation_content(
            advice,
            run_input,
            score_result,
            safety_flags,
        )
        self.last_metadata = RecommendationMeta(
            llm_provider="template",
            llm_model=None,
            prompt_version=PROMPT_VERSION,
            advice_conservativeness=get_advice_conservativeness(
                run_input,
                score_result,
                safety_flags,
            ),
            used_fallback=False,
            llm_latency_ms=0,
            validation_passed=validation_passed,
        )
        return advice


# ──────────────────────────────────────────────
# OpenAI 兼容引擎：直接调用 OpenAI 官方 API 或兼容 OpenAI 协议的服务
# ──────────────────────────────────────────────
class OpenAIRecommendationProvider(RecommendationProvider):
    def __init__(self) -> None:
        # 延迟导入：只有真正使用 OpenAI 时才需要 openai 库
        from openai import OpenAI

        from app.config import get_settings

        settings = get_settings()

        if not settings.llm_api_key:
            raise RuntimeError(
                "使用 OpenAI 引擎需要设置环境变量 RUNRECOVER_LLM_API_KEY。"
            )

        api_url = settings.llm_base_url or "https://api.openai.com/v1"
        model_name = settings.llm_model or "gpt-3.5-turbo"

        self._client = OpenAI(
            api_key=settings.llm_api_key,
            base_url=api_url,
            timeout=settings.llm_timeout_seconds,
        )
        self._model = model_name
        self._fallback = TemplateRecommendationProvider()

    def generate(
        self,
        run_input: AnalyzeRecoveryRequest,
        score_result: ScoreResult,
        safety_flags: list[str],
        reasons: list[Reason],
    ) -> RecoveryAdvice:
        started_at = time.perf_counter()
        try:
            raw = self._call_api(run_input, score_result, safety_flags, reasons)
            advice = self._parse(raw)
            validation_passed, issues = validate_recommendation_content(
                advice,
                run_input,
                score_result,
                safety_flags,
            )
            if not validation_passed:
                raise ValueError(f"LLM 内容后校验失败：{'; '.join(issues)}")
            self.last_metadata = RecommendationMeta(
                llm_provider="openai",
                llm_model=self._model,
                prompt_version=PROMPT_VERSION,
                advice_conservativeness=get_advice_conservativeness(
                    run_input,
                    score_result,
                    safety_flags,
                ),
                used_fallback=False,
                llm_latency_ms=round((time.perf_counter() - started_at) * 1000),
                validation_passed=True,
            )
            return advice
        except Exception as exc:
            logger.warning("OpenAI 调用失败，降级到模板引擎。原因：%s", exc)
            advice = self._fallback.generate(run_input, score_result, safety_flags, reasons)
            self.last_metadata = RecommendationMeta(
                llm_provider="openai",
                llm_model=self._model,
                prompt_version=PROMPT_VERSION,
                advice_conservativeness=self._fallback.last_metadata.advice_conservativeness,
                used_fallback=True,
                llm_latency_ms=round((time.perf_counter() - started_at) * 1000),
                validation_passed=self._fallback.last_metadata.validation_passed,
            )
            return advice

    def _call_api(
        self,
        run_input: AnalyzeRecoveryRequest,
        score_result: ScoreResult,
        safety_flags: list[str],
        reasons: list[Reason],
    ) -> dict[str, Any]:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": _build_user_prompt(run_input, score_result, safety_flags, reasons),
                },
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
        )
        content = response.choices[0].message.content or "{}"
        return json.loads(content)

    @staticmethod
    def _parse(data: dict[str, Any]) -> RecoveryAdvice:
        data.setdefault("safety_note", SAFETY_NOTE)
        return RecoveryAdvice.model_validate(data)


# ──────────────────────────────────────────────
# DeepSeek 引擎：调用 DeepSeek API 生成个性化建议
# DeepSeek 兼容 OpenAI 协议，所以直接用 openai SDK，
# 只需把 base_url 指向 DeepSeek 的服务器即可。
# ──────────────────────────────────────────────
class DeepSeekRecommendationProvider(RecommendationProvider):
    def __init__(self) -> None:
        from openai import OpenAI

        from app.config import get_settings

        settings = get_settings()

        if not settings.llm_api_key:
            raise RuntimeError(
                "使用 DeepSeek 引擎需要设置环境变量 RUNRECOVER_LLM_API_KEY。"
                "请在 https://platform.deepseek.com/api_keys 申请 key。"
            )

        api_url = settings.llm_base_url or "https://api.deepseek.com"
        model_name = settings.llm_model or "deepseek-chat"

        self._client = OpenAI(
            api_key=settings.llm_api_key,
            base_url=api_url,
            timeout=settings.llm_timeout_seconds,
        )
        self._model = model_name
        self._fallback = TemplateRecommendationProvider()

    def generate(
        self,
        run_input: AnalyzeRecoveryRequest,
        score_result: ScoreResult,
        safety_flags: list[str],
        reasons: list[Reason],
    ) -> RecoveryAdvice:
        started_at = time.perf_counter()
        try:
            raw = self._call_api(run_input, score_result, safety_flags, reasons)
            advice = self._parse(raw)
            validation_passed, issues = validate_recommendation_content(
                advice,
                run_input,
                score_result,
                safety_flags,
            )
            if not validation_passed:
                raise ValueError(f"LLM 内容后校验失败：{'; '.join(issues)}")
            self.last_metadata = RecommendationMeta(
                llm_provider="deepseek",
                llm_model=self._model,
                prompt_version=PROMPT_VERSION,
                advice_conservativeness=get_advice_conservativeness(
                    run_input,
                    score_result,
                    safety_flags,
                ),
                used_fallback=False,
                llm_latency_ms=round((time.perf_counter() - started_at) * 1000),
                validation_passed=True,
            )
            return advice
        except Exception as exc:
            logger.warning("DeepSeek 调用失败，降级到模板引擎。原因：%s", exc)
            advice = self._fallback.generate(run_input, score_result, safety_flags, reasons)
            self.last_metadata = RecommendationMeta(
                llm_provider="deepseek",
                llm_model=self._model,
                prompt_version=PROMPT_VERSION,
                advice_conservativeness=self._fallback.last_metadata.advice_conservativeness,
                used_fallback=True,
                llm_latency_ms=round((time.perf_counter() - started_at) * 1000),
                validation_passed=self._fallback.last_metadata.validation_passed,
            )
            return advice

    def _call_api(
        self,
        run_input: AnalyzeRecoveryRequest,
        score_result: ScoreResult,
        safety_flags: list[str],
        reasons: list[Reason],
    ) -> dict[str, Any]:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": _build_user_prompt(run_input, score_result, safety_flags, reasons),
                },
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
        )
        content = response.choices[0].message.content or "{}"
        return json.loads(content)

    @staticmethod
    def _parse(data: dict[str, Any]) -> RecoveryAdvice:
        data.setdefault("safety_note", SAFETY_NOTE)
        return RecoveryAdvice.model_validate(data)


# ──────────────────────────────────────────────
# Anthropic/Claude 引擎：直接调用 Claude 兼容的 API
# ──────────────────────────────────────────────
class AnthropicRecommendationProvider(RecommendationProvider):
    def __init__(self) -> None:
        import httpx

        from app.config import get_settings

        settings = get_settings()

        if not settings.llm_api_key:
            raise RuntimeError(
                "使用 Claude/Anthropic 引擎需要设置环境变量 RUNRECOVER_LLM_API_KEY。"
            )

        self._client = httpx.Client(timeout=settings.llm_timeout_seconds)
        self._base_url = settings.llm_base_url or "https://api.anthropic.com/v1"
        self._model = settings.llm_model or "claude-sonnet-4-5"
        self._api_key = settings.llm_api_key
        self._fallback = TemplateRecommendationProvider()

    def generate(
        self,
        run_input: AnalyzeRecoveryRequest,
        score_result: ScoreResult,
        safety_flags: list[str],
        reasons: list[Reason],
    ) -> RecoveryAdvice:
        started_at = time.perf_counter()
        try:
            raw = self._call_api(run_input, score_result, safety_flags, reasons)
            advice = self._parse(raw)
            validation_passed, issues = validate_recommendation_content(
                advice,
                run_input,
                score_result,
                safety_flags,
            )
            if not validation_passed:
                raise ValueError(f"LLM 内容后校验失败：{'; '.join(issues)}")
            self.last_metadata = RecommendationMeta(
                llm_provider="anthropic",
                llm_model=self._model,
                prompt_version=PROMPT_VERSION,
                advice_conservativeness=get_advice_conservativeness(
                    run_input,
                    score_result,
                    safety_flags,
                ),
                used_fallback=False,
                llm_latency_ms=round((time.perf_counter() - started_at) * 1000),
                validation_passed=True,
            )
            return advice
        except Exception as exc:
            logger.warning("Claude/Anthropic 调用失败，降级到模板引擎。原因：%s", exc)
            advice = self._fallback.generate(run_input, score_result, safety_flags, reasons)
            self.last_metadata = RecommendationMeta(
                llm_provider="anthropic",
                llm_model=self._model,
                prompt_version=PROMPT_VERSION,
                advice_conservativeness=self._fallback.last_metadata.advice_conservativeness,
                used_fallback=True,
                llm_latency_ms=round((time.perf_counter() - started_at) * 1000),
                validation_passed=self._fallback.last_metadata.validation_passed,
            )
            return advice

    def _call_api(
        self,
        run_input: AnalyzeRecoveryRequest,
        score_result: ScoreResult,
        safety_flags: list[str],
        reasons: list[Reason],
    ) -> dict[str, Any]:
        url = f"{self._base_url.rstrip('/')}/messages"
        response = self._client.post(
            url,
            headers={
                "x-api-key": self._api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json={
                "model": self._model,
                "max_tokens": 1200,
                "system": _SYSTEM_PROMPT,
                "messages": [
                    {
                        "role": "user",
                        "content": _build_user_prompt(run_input, score_result, safety_flags, reasons),
                    },
                ],
                "temperature": 0.3,
            },
        )
        response.raise_for_status()
        content = _extract_content_from_response(response.json())
        return json.loads(content)

    @staticmethod
    def _parse(data: dict[str, Any]) -> RecoveryAdvice:
        data.setdefault("safety_note", SAFETY_NOTE)
        return RecoveryAdvice.model_validate(data)


def _extract_content_from_response(data: dict[str, Any]) -> str:
    if "choices" in data and data["choices"]:
        choice = data["choices"][0]
        if isinstance(choice, dict):
            message = choice.get("message")
            if isinstance(message, dict):
                content = message.get("content")
            else:
                content = choice.get("text")
        else:
            content = str(choice)
    elif "completion" in data:
        completion = data["completion"]
        if isinstance(completion, str):
            content = completion
        elif isinstance(completion, dict):
            if "content" in completion:
                content = completion["content"]
            elif "text" in completion:
                content = completion["text"]
            else:
                content = completion
        else:
            content = str(completion)
    else:
        content_blocks = data.get("content")
        if isinstance(content_blocks, list):
            text_parts = [
                block.get("text", "")
                for block in content_blocks
                if isinstance(block, dict) and block.get("type") == "text"
            ]
            content = "".join(text_parts).strip()
        else:
            raise ValueError("无法从 LLM 响应中提取内容。")

    if isinstance(content, dict):
        if "json" in content:
            return json.dumps(content["json"], ensure_ascii=False)
        if "value" in content:
            return json.dumps(content["value"], ensure_ascii=False)
        return json.dumps(content, ensure_ascii=False)

    return str(content)


# ──────────────────────────────────────────────
# 工厂函数：根据配置返回对应的引擎实例
# 调用方（main.py）只需要调这一个函数，不需要知道具体用哪个引擎
# ──────────────────────────────────────────────
def get_recommendation_provider(provider_name: str) -> RecommendationProvider:
    # 统一转小写，避免大小写问题（如 "DeepSeek" 和 "deepseek" 都能识别）
    name = (provider_name or "template").lower()

    if name == "deepseek":
        return DeepSeekRecommendationProvider()
    if name in {"openai", "gpt", "gpt4", "gpt-4"}:
        return OpenAIRecommendationProvider()
    if name in {"anthropic", "claude"}:
        return AnthropicRecommendationProvider()

    # 默认使用模板引擎，保持演示稳定性
    return TemplateRecommendationProvider()


# ──────────────────────────────────────────────
# Prompt 定义
# ──────────────────────────────────────────────

# system prompt：定义模型的角色和输出的 JSON 结构
# 把结构要求写在 system 里，比写在 user 里更稳定
_SYSTEM_PROMPT = (
    "你是一名专业的运动恢复顾问，根据用户的跑步数据和恢复评分，生成中文的个性化恢复建议。\n"
    "规则评分、主要原因 reasons 和 safety_flags 是事实来源，不得与它们冲突。\n"
    "用户画像 user_level 只用于校准建议保守程度和表达方式，不得显著改变恢复分数含义。\n"
    "beginner 使用更通俗、更保守的语言，强调基础恢复和安全；regular 使用平衡策略；advanced 可使用训练调整、降级、Z1/Z2 等更专业表达。\n"
    "无论 user_level 如何，safety_flags 的安全边界都必须优先，不得放松。\n"
    "如果 safety_flags 非空，summary 和 tomorrow 必须体现保守处理，不能鼓励继续高强度或坚持原计划。\n"
    "如果疼痛影响走路，不得推荐跑步、跳跃训练或强拉伸。\n"
    "必须严格返回 JSON 对象，不要包含任何多余文字或 markdown 格式。\n"
    "JSON 结构如下：\n"
    "{\n"
    '  "summary": "整体恢复情况的一句话总结",\n'
    '  "diet":       { "title": "饮食建议", "content": "具体建议内容" },\n'
    '  "hydration":  { "title": "补水建议", "content": "具体建议内容" },\n'
    '  "sleep":      { "title": "睡眠建议", "content": "具体建议内容" },\n'
    '  "relaxation": { "title": "放松建议", "content": "具体建议内容" },\n'
    '  "tomorrow":   { "title": "明日安排", "content": "具体建议内容" },\n'
    '  "timeline": [\n'
    '    { "time": "跑后 0-15 分钟", "action": "..." },\n'
    '    ...\n'
    "  ]\n"
    "}\n"
    "语气温和，建议实用，不做医疗诊断。"
)


def _build_user_prompt(
    run_input: AnalyzeRecoveryRequest,
    score_result: ScoreResult,
    safety_flags: list[str],
    reasons: list[Reason],
) -> str:
    # 把所有相关数据拼成自然语言，让模型有足够上下文生成针对性建议
    return (
        "以下是用户本次跑步和身体状态数据：\n"
        f"{run_input.model_dump_json(indent=2)}\n\n"
        f"用户画像 user_level：{run_input.user_level}\n"
        "画像使用原则：只调整建议保守程度、解释文案和明日训练建议，不大幅改变恢复分数。\n"
        f"建议保守程度：{get_advice_conservativeness(run_input, score_result, safety_flags)}\n\n"
        f"恢复总分：{score_result.score} 分（等级：{score_result.level}）\n"
        f"各维度得分：{score_result.component_scores}\n"
        f"派生指标：{score_result.derived_metrics}\n"
        f"主要原因 reasons：{json.dumps([reason.model_dump() for reason in reasons], ensure_ascii=False)}\n"
        f"安全预警标记：{safety_flags if safety_flags else '无'}\n\n"
        "请根据以上数据生成恢复建议，以 JSON 格式返回，并确保建议重点覆盖 reasons 中的主要因素。"
    )
