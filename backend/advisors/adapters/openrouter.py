"""OpenRouter advisor adapter."""

from __future__ import annotations

import os
import time

import httpx

from ..base import (
    Advisor,
    AdvisorHealth,
    AdvisorMode,
    AdvisorRequest,
    AdvisorResponse,
    AdvisorRole,
    AdvisorStatus,
)
from ..config import AdvisorConfig
from ...config import OPENROUTER_API_KEY, OPENROUTER_API_URL


class OpenRouterAdvisor(Advisor):
    """Advisor backed by OpenRouter chat completions."""

    mode = AdvisorMode.API
    supports_streaming = False

    def __init__(self, config: AdvisorConfig):
        self.config = config
        self.id = config.id
        self.display_name = config.display_name
        self.provider = config.provider
        self.roles = set(config.roles)
        self.model = config.model
        self.timeout_seconds = config.timeout_seconds
        self.env_api_key = config.env_api_key or "OPENROUTER_API_KEY"

    def _api_key(self) -> str | None:
        return os.getenv(self.env_api_key) or OPENROUTER_API_KEY

    async def ask(self, request: AdvisorRequest) -> AdvisorResponse:
        started = time.monotonic()
        if not self.model:
            return self._failed("missing_model", "OpenRouter advisor has no model configured")

        api_key = self._api_key()
        if not api_key:
            return self._failed(
                "missing_api_key",
                f"Missing API key env var {self.env_api_key}",
            )

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [message.model_dump() for message in request.messages],
        }
        timeout = request.timeout_seconds or self.timeout_seconds or 120.0

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(OPENROUTER_API_URL, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as exc:
            return self._failed(
                "http_error",
                f"OpenRouter returned HTTP {exc.response.status_code}",
                raw_error=exc.response.text,
                started=started,
            )
        except Exception as exc:
            return self._failed(
                "request_failed",
                str(exc),
                raw_error=str(exc),
                started=started,
            )

        message = data["choices"][0]["message"]
        return AdvisorResponse(
            advisor_id=self.id,
            display_name=self.display_name,
            provider=self.provider,
            mode=self.mode,
            status=AdvisorStatus.SUCCESS,
            content=message.get("content") or "",
            raw_output=message.get("content") or "",
            latency_ms=int((time.monotonic() - started) * 1000),
            metadata={
                "model": self.model,
                "reasoning_details": message.get("reasoning_details"),
            },
        )

    async def health_check(self) -> AdvisorHealth:
        return AdvisorHealth(
            advisor_id=self.id,
            display_name=self.display_name,
            provider=self.provider,
            mode=self.mode,
            installed=True,
            authenticated=bool(self._api_key()),
            model_available=bool(self.model),
            healthy=bool(self._api_key() and self.model),
            message=None if self._api_key() else f"Missing API key env var {self.env_api_key}",
        )

    def _failed(
        self,
        error_type: str,
        user_message: str,
        raw_error: str | None = None,
        started: float | None = None,
    ) -> AdvisorResponse:
        latency_ms = int((time.monotonic() - started) * 1000) if started else None
        return AdvisorResponse(
            advisor_id=self.id,
            display_name=self.display_name,
            provider=self.provider,
            mode=self.mode,
            status=AdvisorStatus.FAILED,
            content=None,
            raw_error=raw_error,
            error_type=error_type,
            user_message=user_message,
            latency_ms=latency_ms,
            metadata={"model": self.model},
        )

