"""Advisor configuration loading."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from .base import AdvisorMode, AdvisorRole
from ..config import CHAIRMAN_MODEL, COUNCIL_MODELS


DEFAULT_ADVISORS_CONFIG_PATH = "backend/advisors.json"


class AdvisorConfig(BaseModel):
    """Configuration for one advisor adapter."""

    id: str
    display_name: str
    provider: str
    mode: AdvisorMode
    enabled: bool = True
    roles: list[AdvisorRole] = Field(default_factory=lambda: [AdvisorRole.COUNCIL_MEMBER])
    model: str | None = None
    command: str | None = None
    timeout_seconds: float | None = None
    env_api_key: str | None = None
    options: dict[str, Any] = Field(default_factory=dict)


class CouncilDefaults(BaseModel):
    """Global council execution defaults."""

    stage_timeout_seconds: float = 240.0
    max_parallel_api_requests: int = 8
    max_parallel_cli_processes: int = 2


class ChairmanConfig(BaseModel):
    """Chairman advisor selection."""

    advisor_id: str | None = None


class TitleGeneratorConfig(BaseModel):
    """Title generator advisor selection."""

    advisor_id: str | None = None


class AdvisorsConfig(BaseModel):
    """Complete advisor configuration."""

    defaults: CouncilDefaults = Field(default_factory=CouncilDefaults)
    advisors: list[AdvisorConfig]
    chairman: ChairmanConfig = Field(default_factory=ChairmanConfig)
    title_generator: TitleGeneratorConfig = Field(default_factory=TitleGeneratorConfig)


def _default_openrouter_config() -> AdvisorsConfig:
    advisors = [
        AdvisorConfig(
            id=f"openrouter-{index}",
            display_name=model,
            provider="openrouter",
            mode=AdvisorMode.API,
            roles=[AdvisorRole.COUNCIL_MEMBER],
            model=model,
            env_api_key="OPENROUTER_API_KEY",
        )
        for index, model in enumerate(COUNCIL_MODELS)
    ]

    chairman_id = "openrouter-chairman"
    advisors.append(
        AdvisorConfig(
            id=chairman_id,
            display_name=CHAIRMAN_MODEL,
            provider="openrouter",
            mode=AdvisorMode.API,
            roles=[AdvisorRole.CHAIRMAN],
            model=CHAIRMAN_MODEL,
            env_api_key="OPENROUTER_API_KEY",
        )
    )
    advisors.append(
        AdvisorConfig(
            id="openrouter-title-generator",
            display_name="Gemini Flash Title Generator",
            provider="openrouter",
            mode=AdvisorMode.API,
            roles=[AdvisorRole.TITLE_GENERATOR],
            model="google/gemini-2.5-flash",
            timeout_seconds=30.0,
            env_api_key="OPENROUTER_API_KEY",
        )
    )

    return AdvisorsConfig(
        advisors=advisors,
        chairman=ChairmanConfig(advisor_id=chairman_id),
        title_generator=TitleGeneratorConfig(advisor_id="openrouter-title-generator"),
    )


def load_advisors_config(path: str | None = None) -> AdvisorsConfig:
    """Load advisor config from JSON, falling back to current OpenRouter defaults."""
    config_path = Path(path or os.getenv("ADVISORS_CONFIG_PATH", DEFAULT_ADVISORS_CONFIG_PATH))
    if not config_path.exists():
        return _default_openrouter_config()

    with config_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    return AdvisorsConfig.model_validate(data)

