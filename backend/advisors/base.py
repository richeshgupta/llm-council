"""Provider-neutral advisor interface for LLM Council."""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class AdvisorMode(str, Enum):
    """Transport/runtime mode used by an advisor."""

    API = "api"
    CLI = "cli"
    LOCAL = "local"


class AdvisorRole(str, Enum):
    """Role an advisor can play in the council."""

    COUNCIL_MEMBER = "council_member"
    CHAIRMAN = "chairman"
    TITLE_GENERATOR = "title_generator"


class AdvisorStatus(str, Enum):
    """Normalized advisor call status."""

    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    SKIPPED = "skipped"


class AdvisorMessage(BaseModel):
    """Chat-style message passed to an advisor."""

    role: Literal["system", "user", "assistant"]
    content: str


class AdvisorRequest(BaseModel):
    """Provider-neutral advisor request."""

    run_id: str
    stage: Literal["stage1", "stage2", "stage3", "title", "health"]
    messages: list[AdvisorMessage]
    prompt_text: str | None = None
    timeout_seconds: float | None = None
    response_format: Literal["text", "json"] = "text"
    metadata: dict[str, Any] = Field(default_factory=dict)


class AdvisorResponse(BaseModel):
    """Provider-neutral advisor response."""

    advisor_id: str
    display_name: str
    provider: str
    mode: AdvisorMode
    status: AdvisorStatus
    content: str | None = None
    raw_output: str | None = None
    raw_error: str | None = None
    error_type: str | None = None
    user_message: str | None = None
    latency_ms: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AdvisorHealth(BaseModel):
    """Provider-neutral advisor health state."""

    advisor_id: str
    display_name: str
    provider: str
    mode: AdvisorMode
    installed: bool | None = None
    authenticated: bool | None = None
    model_available: bool | None = None
    healthy: bool
    message: str | None = None


class Advisor(ABC):
    """Abstract provider adapter contract."""

    id: str
    display_name: str
    provider: str
    mode: AdvisorMode
    roles: set[AdvisorRole]
    supports_streaming: bool = False

    @abstractmethod
    async def ask(self, request: AdvisorRequest) -> AdvisorResponse:
        """Ask the advisor to answer a request."""

    async def health_check(self) -> AdvisorHealth:
        """Return a lightweight health check for the advisor."""
        return AdvisorHealth(
            advisor_id=self.id,
            display_name=self.display_name,
            provider=self.provider,
            mode=self.mode,
            healthy=True,
            message="No explicit health check implemented",
        )

