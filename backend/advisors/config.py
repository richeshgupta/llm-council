"""Advisor configuration loading."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .base import AdvisorMode, AdvisorRole


DEFAULT_ADVISORS_CONFIG_PATH = Path(__file__).resolve().parent.parent / "advisors.json"


class AdvisorConfig(BaseModel):
    """Configuration for one advisor adapter."""

    model_config = ConfigDict(extra="forbid")

    id: str
    display_name: str
    provider: str
    mode: AdvisorMode
    enabled: bool = True
    roles: list[AdvisorRole] = Field(default_factory=lambda: [AdvisorRole.COUNCIL_MEMBER])
    model: str | None = None
    command: str | None = None
    timeout_seconds: float | None = Field(default=None, gt=0)
    env_api_key: str | None = None
    options: dict[str, Any] = Field(default_factory=dict)


class CouncilDefaults(BaseModel):
    """Global council execution defaults."""

    model_config = ConfigDict(extra="forbid")

    stage_timeout_seconds: float = Field(default=240.0, gt=0)
    max_parallel_api_requests: int = Field(default=8, gt=0)
    max_parallel_cli_processes: int = Field(default=2, gt=0)


class ChairmanConfig(BaseModel):
    """Chairman advisor selection."""

    model_config = ConfigDict(extra="forbid")

    advisor_id: str | None = None


class TitleGeneratorConfig(BaseModel):
    """Title generator advisor selection."""

    model_config = ConfigDict(extra="forbid")

    advisor_id: str | None = None


class AdvisorsConfig(BaseModel):
    """Complete advisor configuration."""

    model_config = ConfigDict(extra="forbid")

    defaults: CouncilDefaults = Field(default_factory=CouncilDefaults)
    advisors: list[AdvisorConfig]
    chairman: ChairmanConfig = Field(default_factory=ChairmanConfig)
    title_generator: TitleGeneratorConfig = Field(default_factory=TitleGeneratorConfig)

    @model_validator(mode="after")
    def validate_advisor_references(self) -> "AdvisorsConfig":
        ids = [advisor.id for advisor in self.advisors]
        duplicates = sorted({advisor_id for advisor_id in ids if ids.count(advisor_id) > 1})
        if duplicates:
            raise ValueError(f"Duplicate advisor ids: {', '.join(duplicates)}")
        known_ids = set(ids)
        for field_name, advisor_id in (
            ("chairman.advisor_id", self.chairman.advisor_id),
            ("title_generator.advisor_id", self.title_generator.advisor_id),
        ):
            if advisor_id and advisor_id not in known_ids:
                raise ValueError(f"{field_name} references unknown advisor: {advisor_id}")

        enabled = {advisor.id: advisor for advisor in self.advisors if advisor.enabled}
        council_members = [
            advisor for advisor in enabled.values() if AdvisorRole.COUNCIL_MEMBER in advisor.roles
        ]
        if not council_members:
            raise ValueError("At least one enabled council_member advisor is required")
        if self.chairman.advisor_id:
            chairman = enabled.get(self.chairman.advisor_id)
            if not chairman:
                raise ValueError("chairman.advisor_id must reference an enabled advisor")
            if AdvisorRole.CHAIRMAN not in chairman.roles:
                raise ValueError("chairman.advisor_id must reference an advisor with the chairman role")
        if self.title_generator.advisor_id:
            title_advisor = enabled.get(self.title_generator.advisor_id)
            if not title_advisor:
                raise ValueError("title_generator.advisor_id must reference an enabled advisor")
            if AdvisorRole.TITLE_GENERATOR not in title_advisor.roles:
                raise ValueError(
                    "title_generator.advisor_id must reference an advisor with the title_generator role"
                )
        return self


def resolve_advisors_config_path(path: str | None = None) -> Path:
    """Resolve the config path independently of the caller's working directory."""
    configured_path = path or os.getenv("LLM_COUNCIL_CONFIG") or os.getenv("ADVISORS_CONFIG_PATH")
    return Path(configured_path).expanduser() if configured_path else DEFAULT_ADVISORS_CONFIG_PATH


def load_advisors_config(path: str | None = None) -> AdvisorsConfig:
    """Load and validate advisor configuration."""
    config_path = resolve_advisors_config_path(path)
    if not config_path.is_file():
        raise FileNotFoundError(
            f"Advisor config not found: {config_path}. Pass --config or set LLM_COUNCIL_CONFIG."
        )

    with config_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    return AdvisorsConfig.model_validate(data)
