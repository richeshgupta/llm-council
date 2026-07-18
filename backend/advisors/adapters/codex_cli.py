"""Codex CLI advisor adapter."""

from __future__ import annotations

import os
import shutil

from ..base import Advisor, AdvisorHealth, AdvisorMode, AdvisorRequest, AdvisorResponse, AdvisorStatus
from ..config import AdvisorConfig
from ..subprocess_runner import run_subprocess


class CodexCliAdvisor(Advisor):
    """Advisor backed by the local Codex CLI."""

    mode = AdvisorMode.CLI
    supports_streaming = False

    def __init__(self, config: AdvisorConfig):
        self.config = config
        self.id = config.id
        self.display_name = config.display_name
        self.provider = config.provider
        self.roles = set(config.roles)
        self.command = config.command or "codex"
        self.model = config.model
        self.timeout_seconds = config.timeout_seconds or 240.0
        self.sandbox = config.options.get("sandbox", "read-only")
        self.cwd = config.options.get("cwd") or os.getcwd()

    async def ask(self, request: AdvisorRequest) -> AdvisorResponse:
        args = [self.command, "exec", "--sandbox", self.sandbox, "--cd", self.cwd]
        if self.model:
            args.extend(["--model", self.model])
        args.append("-")

        prompt = request.prompt_text or "\n\n".join(m.content for m in request.messages)
        try:
            result = await run_subprocess(
                args=args,
                input_text=prompt,
                timeout_seconds=request.timeout_seconds or self.timeout_seconds,
                cwd=self.cwd,
            )
        except FileNotFoundError:
            return self._failed("not_installed", f"Command not found: {self.command}")

        if result.timed_out:
            return self._failed("timeout", "Codex CLI timed out", result.stderr, result.latency_ms, AdvisorStatus.TIMEOUT)
        if result.exit_code != 0:
            raw_error = result.stderr or result.stdout
            return self._failed(self._classify_error(raw_error), "Codex CLI failed", raw_error, result.latency_ms)

        return AdvisorResponse(
            advisor_id=self.id,
            display_name=self.display_name,
            provider=self.provider,
            mode=self.mode,
            status=AdvisorStatus.SUCCESS,
            content=result.stdout.strip(),
            raw_output=result.stdout,
            raw_error=result.stderr or None,
            latency_ms=result.latency_ms,
            metadata={"model": self.model, "sandbox": self.sandbox},
        )

    async def health_check(self) -> AdvisorHealth:
        installed = shutil.which(self.command) is not None
        return AdvisorHealth(
            advisor_id=self.id,
            display_name=self.display_name,
            provider=self.provider,
            mode=self.mode,
            installed=installed,
            authenticated=None,
            model_available=None,
            healthy=installed,
            message=None if installed else f"Command not found: {self.command}",
        )

    def _classify_error(self, stderr: str) -> str:
        text = stderr.lower()
        if "auth" in text or "login" in text:
            return "not_authenticated"
        if "limit" in text or "quota" in text:
            return "usage_limit_exceeded"
        if "model" in text and ("not" in text or "unknown" in text or "invalid" in text):
            return "model_unavailable"
        return "unknown_cli_error"

    def _failed(
        self,
        error_type: str,
        user_message: str,
        raw_error: str | None = None,
        latency_ms: int | None = None,
        status: AdvisorStatus = AdvisorStatus.FAILED,
    ) -> AdvisorResponse:
        return AdvisorResponse(
            advisor_id=self.id,
            display_name=self.display_name,
            provider=self.provider,
            mode=self.mode,
            status=status,
            error_type=error_type,
            user_message=user_message,
            raw_error=raw_error,
            latency_ms=latency_ms,
            metadata={"model": self.model, "sandbox": self.sandbox},
        )
