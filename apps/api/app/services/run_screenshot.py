from __future__ import annotations

import base64
import json
import logging
import re
import time
from typing import Any

from app.config import get_settings
from app.schemas import RunScreenshotExtractResponse

logger = logging.getLogger(__name__)

ALLOWED_IMAGE_TYPES = {
    "image/png",
    "image/jpeg",
    "image/webp",
}

OBJECTIVE_FIELDS = [
    "distance_km",
    "duration_min",
    "pace",
    "run_type_guess",
    "run_time_period_guess",
    "avg_hr",
    "max_hr",
    "calories",
    "elevation_gain",
    "source_app_guess",
]


class ScreenshotExtractionError(RuntimeError):
    pass


class ScreenshotValidationError(ValueError):
    pass


def validate_screenshot_upload(content: bytes, content_type: str | None) -> None:
    settings = get_settings()
    max_bytes = int(settings.screenshot_max_upload_mb * 1024 * 1024)

    if not content:
        raise ScreenshotValidationError("上传文件为空。")
    if len(content) > max_bytes:
        raise ScreenshotValidationError(
            f"图片过大，最大支持 {settings.screenshot_max_upload_mb:g}MB。"
        )
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise ScreenshotValidationError("仅支持 png、jpg、jpeg、webp 图片。")
    if not _matches_image_signature(content, content_type):
        raise ScreenshotValidationError("文件内容不是有效的图片格式。")


def extract_run_screenshot_from_image(
    content: bytes,
    content_type: str,
) -> RunScreenshotExtractResponse:
    settings = get_settings()
    provider = settings.screenshot_llm_provider.lower()

    if provider not in {"openai", "gpt", "gpt4", "gpt-4"}:
        raise ScreenshotExtractionError(
            "截图识别需要配置支持图片理解的模型。请设置 "
            "RUNRECOVER_SCREENSHOT_LLM_PROVIDER=openai。"
        )
    if not settings.screenshot_llm_api_key:
        raise ScreenshotExtractionError(
            "截图识别暂不可用：未配置 RUNRECOVER_SCREENSHOT_LLM_API_KEY "
            "或 RUNRECOVER_LLM_API_KEY。你仍可以手动填写跑步数据。"
        )

    started_at = time.perf_counter()
    try:
        data = _call_openai_vision(content, content_type)
        result = _parse_extraction_result(data)
    except Exception as exc:
        logger.warning("运动截图识别失败：%s", exc)
        raise ScreenshotExtractionError(
            "未能可靠识别截图内容，请手动填写跑步数据。"
        ) from exc

    result.warnings.append(
        f"截图识别耗时约 {round((time.perf_counter() - started_at) * 1000)}ms，请检查结果后再提交。"
    )
    return result


def _call_openai_vision(content: bytes, content_type: str) -> dict[str, Any]:
    from openai import OpenAI

    settings = get_settings()
    client = OpenAI(
        api_key=settings.screenshot_llm_api_key,
        base_url=settings.screenshot_llm_base_url,
        timeout=settings.llm_timeout_seconds,
    )

    encoded_image = base64.b64encode(content).decode("ascii")
    response = client.chat.completions.create(
        model=settings.screenshot_llm_model,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": _USER_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{content_type};base64,{encoded_image}",
                            "detail": "high",
                        },
                    },
                ],
            },
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )
    content_text = response.choices[0].message.content or "{}"
    return json.loads(_strip_json_fence(content_text))


def _parse_extraction_result(data: dict[str, Any]) -> RunScreenshotExtractResponse:
    normalized = {field: data.get(field) for field in OBJECTIVE_FIELDS}
    normalized["confidence"] = data.get("confidence") if isinstance(data.get("confidence"), dict) else {}
    normalized["missing_fields"] = _string_list(data.get("missing_fields"))
    normalized["warnings"] = _string_list(data.get("warnings"))

    result = RunScreenshotExtractResponse.model_validate(normalized)
    _sanitize_ranges(result)
    _fill_missing_fields(result)
    return result


def _sanitize_ranges(result: RunScreenshotExtractResponse) -> None:
    if result.distance_km is not None:
        result.distance_km = round(float(result.distance_km), 2)
        if result.distance_km <= 0 or result.distance_km > 200:
            result.warnings.append("识别到的距离超出合理范围，已忽略。")
            result.distance_km = None
    if result.duration_min is not None:
        result.duration_min = round(float(result.duration_min), 1)
        if result.duration_min <= 0 or result.duration_min > 1440:
            result.warnings.append("识别到的时长超出合理范围，已忽略。")
            result.duration_min = None
    if result.avg_hr is not None and not 30 <= result.avg_hr <= 240:
        result.warnings.append("识别到的平均心率超出合理范围，已忽略。")
        result.avg_hr = None
    if result.max_hr is not None and not 30 <= result.max_hr <= 260:
        result.warnings.append("识别到的最大心率超出合理范围，已忽略。")
        result.max_hr = None


def _fill_missing_fields(result: RunScreenshotExtractResponse) -> None:
    missing = set(result.missing_fields)
    for field in OBJECTIVE_FIELDS:
        if getattr(result, field) is None:
            missing.add(field)
    result.missing_fields = sorted(missing)


def _matches_image_signature(content: bytes, content_type: str | None) -> bool:
    if content_type == "image/png":
        return content.startswith(b"\x89PNG\r\n\x1a\n")
    if content_type == "image/jpeg":
        return content.startswith(b"\xff\xd8\xff")
    if content_type == "image/webp":
        return content.startswith(b"RIFF") and content[8:12] == b"WEBP"
    return False


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _strip_json_fence(value: str) -> str:
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", value, flags=re.DOTALL)
    return match.group(1) if match else value


_SYSTEM_PROMPT = (
    "你是运动截图结构化识别器，只从截图中明确可见的文字、数字和图标标签提取信息。"
    "不要根据常识、经验或训练习惯猜测截图中没有出现的数据。"
    "必须返回一个 JSON 对象，不要输出 markdown 或解释文字。"
)

_USER_PROMPT = (
    "请识别这张跑步 App、运动手表或健身记录截图中的客观跑步数据。\n"
    "规则：\n"
    "1. 只提取截图中明确出现的信息；没有出现就返回 null。\n"
    "2. 距离统一转换为 km；如果原图是 mi/英里，按 1 mi = 1.60934 km 转换，并在 warnings 说明。\n"
    "3. 时长统一为分钟，支持 00:48:30、48:30、48 min 等格式。\n"
    "4. 心率统一为 bpm；平均心率填 avg_hr，最大心率填 max_hr。\n"
    "5. pace 保留为字符串，例如 5'30\"/km 或 5:30/km；不要用 pace 反推距离或时长。\n"
    "6. run_type_guess 只能在截图明确出现训练类型时填写，可选值建议为 "
    "recovery/easy/steady/tempo/interval/long/race；无法判断则 null。\n"
    "7. run_time_period_guess 只能在截图明确显示晨跑、午间、傍晚、夜跑或可见时间时填写，"
    "可选 morning/noon/evening/night；无法判断则 null。\n"
    "8. confidence 中为每个字段给 0 到 1 的置信度；null 字段置信度给 0。\n"
    "9. missing_fields 列出截图中未能识别的字段名。\n"
    "10. warnings 列出单位转换、低置信度、多候选值、不清晰等风险。\n\n"
    "JSON 结构：\n"
    "{\n"
    '  "distance_km": number | null,\n'
    '  "duration_min": number | null,\n'
    '  "pace": string | null,\n'
    '  "run_type_guess": string | null,\n'
    '  "run_time_period_guess": string | null,\n'
    '  "avg_hr": number | null,\n'
    '  "max_hr": number | null,\n'
    '  "calories": number | null,\n'
    '  "elevation_gain": number | null,\n'
    '  "source_app_guess": string | null,\n'
    '  "confidence": {\n'
    '    "distance_km": number,\n'
    '    "duration_min": number,\n'
    '    "pace": number,\n'
    '    "run_type_guess": number,\n'
    '    "run_time_period_guess": number,\n'
    '    "avg_hr": number,\n'
    '    "max_hr": number\n'
    "  },\n"
    '  "missing_fields": string[],\n'
    '  "warnings": string[]\n'
    "}"
)
