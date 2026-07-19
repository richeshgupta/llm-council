"""Bounded parallel advisor execution."""

from __future__ import annotations

import asyncio
from collections.abc import Callable

from ..advisors.base import Advisor, AdvisorMode, AdvisorRequest, AdvisorResponse, AdvisorStatus


async def run_advisors_parallel(
    advisors: list[Advisor],
    request_factory: Callable[[Advisor], AdvisorRequest],
    max_parallel_api_requests: int,
    max_parallel_cli_processes: int,
    api_semaphore: asyncio.Semaphore | None = None,
    cli_semaphore: asyncio.Semaphore | None = None,
) -> list[AdvisorResponse]:
    """Run advisors concurrently with separate API/CLI concurrency limits."""
    api_sem = api_semaphore or asyncio.Semaphore(max_parallel_api_requests)
    cli_sem = cli_semaphore or asyncio.Semaphore(max_parallel_cli_processes)

    async def run_one(advisor: Advisor) -> AdvisorResponse:
        semaphore = cli_sem if advisor.mode == AdvisorMode.CLI else api_sem
        async with semaphore:
            request = request_factory(advisor)
            try:
                call = advisor.ask(request)
                if request.timeout_seconds is not None:
                    return await asyncio.wait_for(call, timeout=request.timeout_seconds)
                return await call
            except asyncio.TimeoutError:
                return AdvisorResponse(
                    advisor_id=advisor.id,
                    display_name=advisor.display_name,
                    provider=advisor.provider,
                    mode=advisor.mode,
                    status=AdvisorStatus.TIMEOUT,
                    error_type="stage_timeout",
                    user_message=f"Advisor exceeded {request.timeout_seconds} seconds",
                    metadata={"model": getattr(advisor, "model", None)},
                )
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                return AdvisorResponse(
                    advisor_id=advisor.id,
                    display_name=advisor.display_name,
                    provider=advisor.provider,
                    mode=advisor.mode,
                    status=AdvisorStatus.FAILED,
                    error_type="adapter_exception",
                    user_message=f"{type(exc).__name__}: {exc}",
                    raw_error=repr(exc),
                    metadata={"model": getattr(advisor, "model", None)},
                )

    return list(await asyncio.gather(*(run_one(advisor) for advisor in advisors)))
