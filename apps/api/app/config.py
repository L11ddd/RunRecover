from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# 在读取环境变量之前先加载 .env 文件。
# find_dotenv() 会自动从当前目录向上逐级查找 .env，
# 所以无论从仓库根目录还是 apps/api 启动后端都能找到。
# override=False 表示：如果 shell 里已经设置了同名变量，以 shell 为准，
# 这样在生产环境（直接设环境变量）时 .env 不会干扰。
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(usecwd=True), override=False)


def _csv_env(name: str, default: str) -> list[str]:
    raw_value = os.getenv(name, default)
    return [item.strip() for item in raw_value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    app_env: str = field(
        default_factory=lambda: os.getenv("RUNRECOVER_ENV", "development")
    )

    database_url: str = field(
        default_factory=lambda: os.getenv(
            "RUNRECOVER_DATABASE_URL", "sqlite:///./data/runrecover.db"
        )
    )

    api_host: str = field(
        default_factory=lambda: os.getenv("RUNRECOVER_API_HOST", "127.0.0.1")
    )

    api_port: int = field(
        default_factory=lambda: int(os.getenv("RUNRECOVER_API_PORT", "8000"))
    )

    cors_origins: list[str] = field(
        default_factory=lambda: _csv_env(
            "RUNRECOVER_CORS_ORIGINS",
            "http://127.0.0.1:5173,http://localhost:5173",
        )
    )

    # 控制使用哪个推荐引擎：
    #   "template"  → 纯规则模板（默认，无需 API key，适合演示）
    #   "deepseek"  → 调用 DeepSeek 大模型 API
    #   "openai"    → 直接调用 OpenAI 官方 API
    #   "anthropic" / "claude" → 直接调用 Claude/Anthropic API
    llm_provider: str = field(
        default_factory=lambda: os.getenv("RUNRECOVER_LLM_PROVIDER", "template")
    )

    # LLM API key，用于 DeepSeek/OpenAI/Anthropic
    llm_api_key: str = field(
        default_factory=lambda: os.getenv("RUNRECOVER_LLM_API_KEY", "")
    )

    # API 地址。默认由各 provider 自动选取：
    #   deepseek:   https://api.deepseek.com
    #   openai:     https://api.openai.com/v1
    #   anthropic:  https://api.anthropic.com/v1
    llm_base_url: str = field(
        default_factory=lambda: os.getenv("RUNRECOVER_LLM_BASE_URL", "")
    )

    # 使用的模型名称。默认由各 provider 自动选取：
    #   deepseek:   deepseek-chat
    #   openai:     gpt-3.5-turbo
    #   anthropic:  claude-3.5-mini
    llm_model: str = field(
        default_factory=lambda: os.getenv("RUNRECOVER_LLM_MODEL", "")
    )

    # 单次 API 调用的超时秒数，防止网络慢时把整个请求卡住
    llm_timeout_seconds: float = field(
        default_factory=lambda: float(os.getenv("RUNRECOVER_LLM_TIMEOUT", "20"))
    )

    screenshot_llm_provider: str = field(
        default_factory=lambda: os.getenv("RUNRECOVER_SCREENSHOT_LLM_PROVIDER", "openai")
    )

    screenshot_llm_model: str = field(
        default_factory=lambda: os.getenv(
            "RUNRECOVER_SCREENSHOT_LLM_MODEL",
            os.getenv("RUNRECOVER_LLM_MODEL", "gpt-4o-mini"),
        )
    )

    screenshot_llm_api_key: str = field(
        default_factory=lambda: os.getenv(
            "RUNRECOVER_SCREENSHOT_LLM_API_KEY",
            os.getenv("RUNRECOVER_LLM_API_KEY", ""),
        )
    )

    screenshot_llm_base_url: str = field(
        default_factory=lambda: os.getenv(
            "RUNRECOVER_SCREENSHOT_LLM_BASE_URL",
            os.getenv("RUNRECOVER_LLM_BASE_URL", "https://api.openai.com/v1"),
        )
    )

    screenshot_max_upload_mb: float = field(
        default_factory=lambda: float(os.getenv("RUNRECOVER_SCREENSHOT_MAX_MB", "5"))
    )


def get_settings() -> Settings:
    return Settings()


def sqlite_path_from_url(database_url: str) -> Path:
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        raise ValueError("Only sqlite:/// database URLs are supported in the MVP.")

    raw_path = database_url[len(prefix) :]
    path = Path(raw_path)
    if not path.is_absolute():
        path = Path.cwd() / path
    return path
