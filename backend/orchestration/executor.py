"""Bounded parallel advisor execution."""

from __future__ import annotations

import asyncio
from collections.abc import Callable

from ..advisors.base import Advisor, AdvisorMode, AdvisorRequest, AdvisorResponse


async def run_advisors_parallel(
    advisors: list[Advisor],
    request_factory: Callable[[Advisor], AdvisorRequest],
    max_parallel_api_requests: int,
    max_parallel_cli_processes: int,
) -> list[AdvisorResponse]:
    """Run advisors concurrently with separate API/CLI concurrency limits."""
    api_sem = asyncio.Semaphore(max_parallel_api_requests)
    cli_sem = asyncio.Semaphore(max_parallel_cli_processes)

    async def run_one(advisor: Advisor) -> AdvisorResponse:
        semaphore = cli_sem if advisor.mode == AdvisorMode.CLI else api_sem
        async with semaphore:
            return await advisor.ask(request_factory(advisor))

    return list(await asyncio.gather(*(run_one(advisor) for advisor in advisors)))

