"""Safe async subprocess execution for CLI-backed advisors."""

from __future__ import annotations

import asyncio
import time

from pydantic import BaseModel


MAX_CAPTURE_CHARS = 200_000


class SubprocessResult(BaseModel):
    exit_code: int | None
    stdout: str
    stderr: str
    timed_out: bool
    latency_ms: int


def _truncate(text: str) -> str:
    if len(text) <= MAX_CAPTURE_CHARS:
        return text
    return text[:MAX_CAPTURE_CHARS] + "\n...[truncated]"


async def run_subprocess(
    args: list[str],
    input_text: str,
    timeout_seconds: float,
    cwd: str | None = None,
    env: dict[str, str] | None = None,
) -> SubprocessResult:
    """Run a subprocess without shell interpolation."""
    started = time.monotonic()
    process = await asyncio.create_subprocess_exec(
        *args,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
        env=env,
    )

    try:
        stdout, stderr = await asyncio.wait_for(
            process.communicate(input_text.encode("utf-8")),
            timeout=timeout_seconds,
        )
        timed_out = False
    except asyncio.TimeoutError:
        process.kill()
        stdout, stderr = await process.communicate()
        timed_out = True

    latency_ms = int((time.monotonic() - started) * 1000)
    return SubprocessResult(
        exit_code=process.returncode,
        stdout=_truncate(stdout.decode("utf-8", errors="replace")),
        stderr=_truncate(stderr.decode("utf-8", errors="replace")),
        timed_out=timed_out,
        latency_ms=latency_ms,
    )

