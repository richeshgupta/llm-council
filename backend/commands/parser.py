"""CLI argument parser and backward-compatible argv normalization."""

from __future__ import annotations

import argparse
import sys

from .modes import MODES


COMMANDS = {"ask", "doctor", "advisors", "config", "modes"}


def normalize_argv(argv: list[str]) -> list[str]:
    if not argv or argv[0] in COMMANDS or argv[0] in {"-h", "--help"}:
        return argv
    if "--doctor" in argv:
        return ["doctor", *(item for item in argv if item != "--doctor")]
    return ["ask", *argv]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="llm-council",
        description="Multi-provider brainstorming, peer review, and synthesis.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    ask = subparsers.add_parser("ask", help="Run a council query.")
    ask.add_argument("query", nargs="*", help="Question to ask; reads stdin if omitted.")
    ask.add_argument("--mode", choices=tuple(MODES), default="general")
    ask.add_argument("--output", choices=("full", "final", "json"), default="full")
    ask.add_argument("--brief", action="store_true", help="Alias for --output final.")
    ask.add_argument("--config", help="Advisor configuration path.")
    ask.add_argument("--no-progress", action="store_true")

    doctor = subparsers.add_parser("doctor", help="Check provider readiness.")
    doctor.add_argument("--probe", action="store_true", help="Send a real minimal provider query.")
    doctor.add_argument("--config", help="Advisor configuration path.")

    advisors = subparsers.add_parser("advisors", help="List enabled advisors.")
    advisors.add_argument("--json", action="store_true")
    advisors.add_argument("--config", help="Advisor configuration path.")

    config = subparsers.add_parser("config", help="Inspect or validate configuration.")
    config.add_argument("action", choices=("path", "show", "validate"))
    config.add_argument("--config", help="Advisor configuration path.")

    modes = subparsers.add_parser("modes", help="List generic council modes.")
    modes.add_argument("--json", action="store_true")

    return parser.parse_args(normalize_argv(list(argv) if argv is not None else sys.argv[1:]))
