"""Provider diagnostics command."""

from __future__ import annotations

import argparse
import asyncio
import uuid
from typing import Any

from ..advisors.base import AdvisorMessage, AdvisorRequest, AdvisorStatus
from ..advisors.config import resolve_advisors_config_path
from ..advisors.registry import AdvisorRegistry
from .common import create_registry


async def run_doctor(registry: AdvisorRegistry, config_path: str | None, probe: bool) -> int:
    print(f"Configuration: {resolve_advisors_config_path(config_path).resolve()}")
    advisors = registry.get_enabled_advisors()
    if not advisors:
        print("No enabled advisors are configured.")
        return 1

    checks = await asyncio.gather(
        *(advisor.health_check() for advisor in advisors),
        return_exceptions=True,
    )
    healthy = True
    for advisor, check in zip(advisors, checks):
        if isinstance(check, BaseException):
            print(f"[FAIL] {advisor.display_name} ({advisor.id}): {type(check).__name__}: {check}")
            healthy = False
            continue
        state = "OK" if check.healthy else "FAIL"
        print(f"[{state}] {advisor.display_name} ({advisor.id}): {check.message or 'available'}")
        healthy = healthy and check.healthy
        if probe and check.healthy:
            probe_ok, detail = await _probe(advisor)
            print(f"  [{'OK' if probe_ok else 'FAIL'}] authentication/model probe: {detail}")
            healthy = healthy and probe_ok

    try:
        chairman = registry.get_chairman_advisor()
    except ValueError as exc:
        print(f"Chairman: FAIL ({exc})")
        return 1
    print(f"Chairman: {chairman.display_name} ({chairman.id})")
    return 0 if healthy else 1


async def _probe(advisor: Any) -> tuple[bool, str]:
    request = AdvisorRequest(
        run_id=str(uuid.uuid4()),
        stage="health",
        messages=[
            AdvisorMessage(
                role="user",
                content="Reply with exactly LLM_COUNCIL_OK and nothing else.",
            )
        ],
        timeout_seconds=min(getattr(advisor, "timeout_seconds", 60.0), 60.0),
    )
    try:
        response = await advisor.ask(request)
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"
    probe_ok = (
        response.status == AdvisorStatus.SUCCESS
        and (response.content or "").strip() == "LLM_COUNCIL_OK"
    )
    detail = response.content or response.user_message or "no response"
    if not probe_ok and response.error_type:
        detail = f"{detail} ({response.error_type})"
    return probe_ok, detail.strip()


def run_doctor_command(args: argparse.Namespace) -> int:
    return asyncio.run(run_doctor(create_registry(args.config), args.config, args.probe))
