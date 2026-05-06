from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv(
        "RUNRECOVER_DATABASE_URL", "sqlite:///./data/runrecover.db"
    )
    llm_provider: str = os.getenv("RUNRECOVER_LLM_PROVIDER", "template")


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
