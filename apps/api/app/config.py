from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# 在读取环境变量之前先加载 .env 文件。
# find_dotenv() 会自动从当前目录向上逐级查找 .env，
# 所以无论从仓库根目录还是 apps/api 启动后端都能找到。
# override=False 表示：如果 shell 里已经设置了同名变量，以 shell 为准，
# 这样在生产环境（直接设环境变量）时 .env 不会干扰。
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(usecwd=True), override=False)


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv(
        "RUNRECOVER_DATABASE_URL", "sqlite:///./data/runrecover.db"
    )

    # 控制使用哪个推荐引擎：
    #   "template" → 纯规则模板（默认，无需 API key，适合演示）
    #   "deepseek" → 调用 DeepSeek 大模型 API
    llm_provider: str = os.getenv("RUNRECOVER_LLM_PROVIDER", "template")

    # DeepSeek API key，在 https://platform.deepseek.com/api_keys 申请
    llm_api_key: str = os.getenv("RUNRECOVER_LLM_API_KEY", "")

    # API 地址。DeepSeek 默认是 https://api.deepseek.com
    # 如果将来换成其他兼容 OpenAI 协议的模型（如通义千问、本地 Ollama），
    # 只需修改这个环境变量，代码不用动。
    llm_base_url: str = os.getenv(
        "RUNRECOVER_LLM_BASE_URL", "https://api.deepseek.com"
    )

    # 使用的模型名称。DeepSeek 常用：
    #   deepseek-chat    → 通用对话模型，性价比高
    #   deepseek-reasoner → 推理增强版，更贵但更准
    llm_model: str = os.getenv("RUNRECOVER_LLM_MODEL", "deepseek-chat")

    # 单次 API 调用的超时秒数，防止网络慢时把整个请求卡住
    llm_timeout_seconds: float = float(os.getenv("RUNRECOVER_LLM_TIMEOUT", "20"))


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
