"""Console entrypoint for LLM Council."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
from typing import Any

from .advisors.base import AdvisorMessage, AdvisorRequest, AdvisorStatus
from .advisors.config import load_advisors_config, resolve_advisors_config_path
from .advisors.registry import AdvisorRegistry
from .orchestration.council_orchestrator import CouncilOrchestrator


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ask multiple LLM advisors, collect peer review, and synthesize an answer."
    )
    parser.add_argument("query", nargs="*", help="Question to ask. Reads stdin if omitted.")
    parser.add_argument("--brief", action="store_true", help="Alias for --output final.")
    parser.add_argument(
        "--output",
        choices=("full", "final", "json"),
        default="full",
        help="Output detail written to stdout (default: full).",
    )
    parser.add_argument("--config", help="Path to an advisors JSON configuration file.")
    parser.add_argument(
        "--doctor",
        action="store_true",
        help="Check configuration and provider availability without running a council.",
    )
    parser.add_argument(
        "--probe",
        action="store_true",
        help="With --doctor, query providers to verify auth/model access (may consume usage).",
    )
    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="Suppress stage progress written to stderr.",
    )
    return parser.parse_args(argv)


def _progress(event: str, data: dict[str, Any]) -> None:
    messages = {
        "stage1_start": lambda: f"Stage 1: asking {data['advisors']} advisor(s)...",
        "stage1_complete": lambda: f"Stage 1: {data['successful']} succeeded, {data['failed']} failed.",
        "stage2_start": lambda: f"Stage 2: collecting reviews from {data['advisors']} advisor(s)...",
        "stage2_complete": lambda: f"Stage 2: {data['successful']} succeeded, {data['failed']} failed.",
        "stage2_skipped": lambda: f"Stage 2: skipped ({data['reason']}).",
        "stage3_start": lambda: f"Stage 3: trying up to {data['candidates']} chairman(s)...",
        "stage3_complete": lambda: (
            f"Stage 3: {'complete' if data['successful'] else 'degraded/failed'}"
            f" ({data['failed']} failed attempt(s))."
        ),
    }
    message = messages.get(event)
    if message:
        print(message(), file=sys.stderr, flush=True)


def _print_failures(metadata: dict[str, Any]) -> None:
    for stage, failures in metadata.get("failures", {}).items():
        for failure in failures:
            detail = failure.get("message") or failure.get("error_type") or "unknown error"
            name = failure.get("display_name") or failure.get("advisor_id")
            print(f"Warning: {stage} {name} failed: {detail}", file=sys.stderr)


def _print_full(
    stage1: list[dict[str, Any]],
    stage2: list[dict[str, Any]],
    stage3: dict[str, Any],
    metadata: dict[str, Any],
) -> None:
    print("\n=== Stage 1: Advisor answers ===")
    for item in stage1:
        print(f"\n[{item.get('display_name') or item.get('model')}]")
        print(item.get("response", ""))

    print("\n=== Stage 2: Peer reviews ===")
    if not stage2:
        print("\nNo peer reviews were produced.")
    for item in stage2:
        print(f"\n[{item.get('display_name') or item.get('model')}]")
        print(item.get("ranking", ""))

    print("\n=== Aggregate ranking ===")
    rankings = metadata.get("aggregate_rankings", [])
    if not rankings:
        print("No valid aggregate ranking was produced.")
    for item in rankings:
        print(f"- {item['model']}: avg rank {item['average_rank']} ({item['rankings_count']} votes)")

    print("\n=== Final council answer ===")
    print(f"[{stage3.get('display_name') or stage3.get('model')}]")
    print(stage3.get("response", ""))


async def run_query(
    query: str,
    registry: AdvisorRegistry,
    output: str = "full",
    show_progress: bool = True,
) -> int:
    orchestrator = CouncilOrchestrator(registry)
    stage1, stage2, stage3, metadata = await orchestrator.run_full_council(
        query,
        progress=_progress if show_progress and output != "json" else None,
    )
    result = {
        "schema_version": metadata.get("schema_version", 1),
        "run_id": metadata.get("run_id"),
        "query": query,
        "stage1": stage1,
        "stage2": stage2,
        "stage3": stage3,
        "metadata": metadata,
    }

    if output == "json":
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif output == "final":
        print(stage3.get("response", ""))
    else:
        _print_full(stage1, stage2, stage3, metadata)

    _print_failures(metadata)
    return 0 if stage3.get("status") == AdvisorStatus.SUCCESS.value else 1


async def run_doctor(registry: AdvisorRegistry, config_path: str | None, probe: bool) -> int:
    print(f"Configuration: {resolve_advisors_config_path(config_path).resolve()}")
    advisors = registry.get_enabled_advisors()
    if not advisors:
        print("No enabled advisors are configured.", file=sys.stderr)
        return 1

    checks = await asyncio.gather(*(advisor.health_check() for advisor in advisors))
    healthy = True
    for advisor, check in zip(advisors, checks):
        state = "OK" if check.healthy else "FAIL"
        print(f"[{state}] {advisor.display_name} ({advisor.id}): {check.message or 'available'}")
        healthy = healthy and check.healthy

        if probe and check.healthy:
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
            response = await advisor.ask(request)
            probe_ok = (
                response.status == AdvisorStatus.SUCCESS
                and (response.content or "").strip() == "LLM_COUNCIL_OK"
            )
            probe_state = "OK" if probe_ok else "FAIL"
            detail = response.content or response.user_message or "no response"
            if not probe_ok and response.error_type:
                detail = f"{detail} ({response.error_type})"
            print(f"  [{probe_state}] authentication/model probe: {detail.strip()}")
            healthy = healthy and probe_ok

    try:
        chairman = registry.get_chairman_advisor()
    except ValueError as exc:
        print(f"Chairman: FAIL ({exc})", file=sys.stderr)
        return 1
    print(f"Chairman: {chairman.display_name} ({chairman.id})")
    return 0 if healthy else 1


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.probe and not args.doctor:
        print("Error: --probe requires --doctor.", file=sys.stderr)
        return 2

    try:
        registry = AdvisorRegistry(load_advisors_config(args.config))
    except Exception as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    try:
        if args.doctor:
            return asyncio.run(run_doctor(registry, args.config, args.probe))

        query = " ".join(args.query).strip()
        if not query and not sys.stdin.isatty():
            query = sys.stdin.read().strip()
        if not query:
            print("Error: provide a query argument or pipe a query on stdin.", file=sys.stderr)
            return 2

        output = "final" if args.brief else args.output
        return asyncio.run(
            run_query(query, registry, output=output, show_progress=not args.no_progress)
        )
    except KeyboardInterrupt:
        print("Cancelled.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
