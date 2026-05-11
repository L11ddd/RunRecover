from __future__ import annotations

import json
import logging
from typing import Any

from app.schemas import AnalyzeRecoveryRequest, RecoveryAdvice, ScoreResult
from app.services.recommendations import SAFETY_NOTE, build_template_recommendation

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# 抽象基类：所有推荐引擎都必须实现 generate 方法
# ──────────────────────────────────────────────
class RecommendationProvider:
    def generate(
        self,
        run_input: AnalyzeRecoveryRequest,
        score_result: ScoreResult,
        safety_flags: list[str],
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
    ) -> RecoveryAdvice:
        return build_template_recommendation(run_input, score_result, safety_flags)


# ──────────────────────────────────────────────
# DeepSeek 引擎：调用 DeepSeek API 生成个性化建议
# DeepSeek 兼容 OpenAI 协议，所以直接用 openai SDK，
# 只需把 base_url 指向 DeepSeek 的服务器即可。
# ──────────────────────────────────────────────
class DeepSeekRecommendationProvider(RecommendationProvider):
    def __init__(self) -> None:
        # 延迟导入：只有真正使用 DeepSeek 时才需要 openai 库
        from openai import OpenAI

        from app.config import get_settings

        settings = get_settings()

        # 没有配置 API key 时直接报错，避免后续调用时出现难以理解的 401 错误
        if not settings.llm_api_key:
            raise RuntimeError(
                "使用 DeepSeek 引擎需要设置环境变量 RUNRECOVER_LLM_API_KEY。"
                "请在 https://platform.deepseek.com/api_keys 申请 key。"
            )

        # 初始化 OpenAI 客户端，指向 DeepSeek 的 API 地址
        self._client = OpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,   # 默认 https://api.deepseek.com
            timeout=settings.llm_timeout_seconds,
        )
        self._model = settings.llm_model

        # 保存模板引擎实例，用于 API 调用失败时的降级
        self._fallback = TemplateRecommendationProvider()

    def generate(
        self,
        run_input: AnalyzeRecoveryRequest,
        score_result: ScoreResult,
        safety_flags: list[str],
    ) -> RecoveryAdvice:
        try:
            # 调用 DeepSeek API，拿到原始 JSON 字典
            raw = self._call_api(run_input, score_result, safety_flags)
            return self._parse(raw)
        except Exception as exc:
            # 任何异常（网络超时、限流、JSON 解析失败等）都降级到模板引擎，
            # 保证接口不会因为 LLM 问题而返回 500 错误
            logger.warning("DeepSeek 调用失败，降级到模板引擎。原因：%s", exc)
            return self._fallback.generate(run_input, score_result, safety_flags)

    def _call_api(
        self,
        run_input: AnalyzeRecoveryRequest,
        score_result: ScoreResult,
        safety_flags: list[str],
    ) -> dict[str, Any]:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                # system prompt：告诉模型它的角色和输出格式要求
                {"role": "system", "content": _SYSTEM_PROMPT},
                # user prompt：把用户的跑步数据和评分传给模型
                {"role": "user", "content": _build_user_prompt(run_input, score_result, safety_flags)},
            ],
            # 强制模型只输出合法 JSON，避免返回 markdown 代码块等格式
            response_format={"type": "json_object"},
            # temperature=0.3：降低随机性，让建议更稳定、不乱发挥
            temperature=0.3,
        )
        content = response.choices[0].message.content or "{}"
        return json.loads(content)

    @staticmethod
    def _parse(data: dict[str, Any]) -> RecoveryAdvice:
        # safety_note 是合规免责声明，不能让模型随意编写，
        # 如果模型漏了这个字段，用项目统一的常量兜底
        data.setdefault("safety_note", SAFETY_NOTE)

        # Pydantic 会自动校验所有字段的类型和必填项，
        # 如果模型返回的 JSON 缺字段或类型错误，这里会抛异常，触发上层降级
        return RecoveryAdvice.model_validate(data)


# ──────────────────────────────────────────────
# 工厂函数：根据配置返回对应的引擎实例
# 调用方（main.py）只需要调这一个函数，不需要知道具体用哪个引擎
# ──────────────────────────────────────────────
def get_recommendation_provider(provider_name: str) -> RecommendationProvider:
    # 统一转小写，避免大小写问题（如 "DeepSeek" 和 "deepseek" 都能识别）
    name = (provider_name or "template").lower()

    if name == "deepseek":
        return DeepSeekRecommendationProvider()

    # 默认使用模板引擎，保持演示稳定性
    return TemplateRecommendationProvider()


# ──────────────────────────────────────────────
# Prompt 定义
# ──────────────────────────────────────────────

# system prompt：定义模型的角色和输出的 JSON 结构
# 把结构要求写在 system 里，比写在 user 里更稳定
_SYSTEM_PROMPT = (
    "你是一名专业的运动恢复顾问，根据用户的跑步数据和恢复评分，生成中文的个性化恢复建议。\n"
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
) -> str:
    # 把所有相关数据拼成自然语言，让模型有足够上下文生成针对性建议
    return (
        "以下是用户本次跑步和身体状态数据：\n"
        f"{run_input.model_dump_json(indent=2)}\n\n"
        f"恢复总分：{score_result.score} 分（等级：{score_result.level}）\n"
        f"各维度得分：{score_result.component_scores}\n"
        f"安全预警标记：{safety_flags if safety_flags else '无'}\n\n"
        "请根据以上数据生成恢复建议，以 JSON 格式返回。"
    )
