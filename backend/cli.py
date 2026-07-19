"""Console entrypoint for LLM Council."""

from __future__ import annotations

import argparse
import asyncio
import sys

from .council import run_full_council


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a one-shot LLM Council query.")
    parser.add_argument("query", nargs="*", help="Question to ask the council. Reads stdin if omitted.")
    parser.add_argument("--brief", action="store_true", help="Print only the final council answer.")
    return parser.parse_args(argv)


async def run_query(query: str, brief: bool = False) -> int:
    stage1, stage2, stage3, metadata = await run_full_council(query)

    if brief:
        print(stage3.get("response", ""))
        return 0

    print("\n=== Stage 1: Advisor answers ===")
    for item in stage1:
        print(f"\n[{item.get('display_name') or item.get('model')}]")
        print(item.get("response", ""))

    print("\n=== Stage 2: Peer rankings ===")
    for item in stage2:
        print(f"\n[{item.get('display_name') or item.get('model')}]")
        print(f"Parsed ranking: {item.get('parsed_ranking', [])}")

    print("\n=== Aggregate ranking ===")
    for item in metadata.get("aggregate_rankings", []):
        print(f"- {item['model']}: avg rank {item['average_rank']} ({item['rankings_count']} votes)")

    print("\n=== Final council answer ===")
    print(f"[{stage3.get('display_name') or stage3.get('model')}]")
    print(stage3.get("response", ""))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    query = " ".join(args.query).strip()
    if not query and not sys.stdin.isatty():
        query = sys.stdin.read().strip()
    if not query:
        print("Error: provide a query argument or pipe a query on stdin.", file=sys.stderr)
        return 2

    return asyncio.run(run_query(query, brief=args.brief))


if __name__ == "__main__":
    raise SystemExit(main())

