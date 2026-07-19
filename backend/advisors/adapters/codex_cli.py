"""Codex CLI advisor adapter."""

from __future__ import annotations

import os
import shutil
import tempfile
from contextlib import nullcontext

from ..base import (
    Advisor,
    AdvisorHealth,
    AdvisorMode,
    AdvisorRequest,
    AdvisorResponse,
    AdvisorStatus,
    render_cli_prompt,
)
from ..config import AdvisorConfig
from ..subprocess_runner import run_subprocess


class CodexCliAdvisor(Advisor):
    """Advisor backed by the local Codex CLI."""

    mode = AdvisorMode.CLI
    supports_streaming = False

    def __init__(self, config: AdvisorConfig):
        unknown_options = set(config.options) - {"sandbox", "cwd"}
        if unknown_options:
            raise ValueError(f"Unknown Codex options: {', '.join(sorted(unknown_options))}")
        self.config = config
        self.id = config.id
        self.display_name = config.display_name
        self.provider = config.provider
        self.roles = set(config.roles)
        self.command = config.command or "codex"
        self.model = config.model
        self.timeout_seconds = config.timeout_seconds or 240.0
        self.sandbox = config.options.get("sandbox", "read-only")
        if self.sandbox not in {"read-only", "workspace-write", "danger-full-access"}:
            raise ValueError(f"Unsupported Codex sandbox: {self.sandbox}")
        self.cwd = config.options.get("cwd")

    async def ask(self, request: AdvisorRequest) -> AdvisorResponse:
        cwd_context = nullcontext(self.cwd) if self.cwd else tempfile.TemporaryDirectory(
            prefix="llm-council-codex-"
        )
        with cwd_context as runtime_cwd:
            args = [
                self.command,
                "exec",
                "--skip-git-repo-check",
                "--sandbox",
                self.sandbox,
                "--cd",
                runtime_cwd,
            ]
            if self.model:
                args.extend(["--model", self.model])
            args.append("-")

            prompt = render_cli_prompt(request)
            try:
                result = await run_subprocess(
                    args=args,
                    input_text=prompt,
                    timeout_seconds=request.timeout_seconds or self.timeout_seconds,
                    cwd=runtime_cwd,
                    env=self._safe_environment(),
                )
            except FileNotFoundError:
                return self._failed("not_installed", f"Command not found: {self.command}")

        if result.timed_out:
            return self._failed("timeout", "Codex CLI timed out", result.stderr, result.latency_ms, AdvisorStatus.TIMEOUT)
        if result.exit_code != 0:
            raw_error = result.stderr or result.stdout
            return self._failed(self._classify_error(raw_error), "Codex CLI failed", raw_error, result.latency_ms)
        if not result.stdout.strip():
            return self._failed("empty_response", "Codex CLI returned an empty response", result.stderr, result.latency_ms)

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
            metadata={"model": self.model, "sandbox": self.sandbox, "isolated_cwd": not self.cwd},
        )

    @staticmethod
    def _safe_environment() -> dict[str, str]:
        """Keep CLI/auth/network essentials without exposing unrelated project secrets."""
        allowed = {
            "PATH",
            "HOME",
            "CODEX_HOME",
            "XDG_CONFIG_HOME",
            "XDG_CACHE_HOME",
            "XDG_DATA_HOME",
            "TERM",
            "LANG",
            "LC_ALL",
            "HTTP_PROXY",
            "HTTPS_PROXY",
            "ALL_PROXY",
            "NO_PROXY",
            "SSL_CERT_FILE",
        }
        return {key: value for key, value in os.environ.items() if key in allowed}

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
            message=(
                "command installed; authentication/model not probed"
                if installed
                else f"Command not found: {self.command}"
            ),
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
            metadata={"model": self.model, "sandbox": self.sandbox, "isolated_cwd": not self.cwd},
        )
