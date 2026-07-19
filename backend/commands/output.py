"""Human and machine-readable council output."""

from __future__ import annotations

import json
import sys
from typing import Any


def print_progress(event: str, data: dict[str, Any]) -> None:
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


def print_failures(metadata: dict[str, Any]) -> None:
    for stage, failures in metadata.get("failures", {}).items():
        for failure in failures:
            detail = failure.get("message") or failure.get("error_type") or "unknown error"
            name = failure.get("display_name") or failure.get("advisor_id")
            print(f"Warning: {stage} {name} failed: {detail}", file=sys.stderr)


def print_result(result: dict[str, Any], output: str) -> None:
    if output == "json":
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif output == "final":
        print(result["stage3"].get("response", ""))
    else:
        print_full(result)


def print_full(result: dict[str, Any]) -> None:
    print("\n=== Stage 1: Advisor answers ===")
    for item in result["stage1"]:
        print(f"\n[{item.get('display_name') or item.get('model')}]")
        print(item.get("response", ""))

    print("\n=== Stage 2: Peer reviews ===")
    if not result["stage2"]:
        print("\nNo peer reviews were produced.")
    for item in result["stage2"]:
        print(f"\n[{item.get('display_name') or item.get('model')}]")
        print(item.get("ranking", ""))

    print("\n=== Aggregate ranking ===")
    rankings = result["metadata"].get("aggregate_rankings", [])
    if not rankings:
        print("No valid aggregate ranking was produced.")
    for item in rankings:
        print(f"- {item['model']}: avg rank {item['average_rank']} ({item['rankings_count']} votes)")

    print("\n=== Final council answer ===")
    stage3 = result["stage3"]
    print(f"[{stage3.get('display_name') or stage3.get('model')}]")
    print(stage3.get("response", ""))
