"""Run a council query."""

from __future__ import annotations

import argparse
import asyncio
import sys

from ..advisors.base import AdvisorStatus
from ..advisors.registry import AdvisorRegistry
from ..orchestration.council_orchestrator import CouncilOrchestrator
from .common import create_registry
from .modes import apply_mode
from .output import print_failures, print_progress, print_result


async def run_query(
    query: str,
    registry: AdvisorRegistry,
    mode: str = "general",
    output: str = "full",
    show_progress: bool = True,
) -> int:
    orchestrator = CouncilOrchestrator(registry)
    stage1, stage2, stage3, metadata = await orchestrator.run_full_council(
        apply_mode(query, mode),
        progress=print_progress if show_progress and output != "json" else None,
    )
    result = {
        "schema_version": metadata.get("schema_version", 1),
        "run_id": metadata.get("run_id"),
        "mode": mode,
        "query": query,
        "stage1": stage1,
        "stage2": stage2,
        "stage3": stage3,
        "metadata": metadata,
    }
    print_result(result, output)
    print_failures(metadata)
    return 0 if stage3.get("status") == AdvisorStatus.SUCCESS.value else 1


def run_ask_command(args: argparse.Namespace) -> int:
    query = " ".join(args.query).strip()
    if not query and not sys.stdin.isatty():
        query = sys.stdin.read().strip()
    if not query:
        print("Error: provide a query argument or pipe a query on stdin.", file=sys.stderr)
        return 2

    registry = create_registry(args.config)
    output = "final" if args.brief else args.output
    return asyncio.run(
        run_query(
            query,
            registry,
            mode=args.mode,
            output=output,
            show_progress=not args.no_progress,
        )
    )
