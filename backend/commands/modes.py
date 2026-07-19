"""Generic council prompt modes."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class CouncilMode:
    name: str
    description: str
    instruction: str


MODES = {
    mode.name: mode
    for mode in (
        CouncilMode(
            "general",
            "General-purpose question answering and analysis.",
            "",
        ),
        CouncilMode(
            "brainstorm",
            "Generate diverse options before recommending a direction.",
            "Generate multiple meaningfully different options. Explore unconventional ideas, "
            "state tradeoffs, and only then recommend the strongest direction.",
        ),
        CouncilMode(
            "review",
            "Critique a design, proposal, document, or implementation.",
            "Act as a rigorous reviewer. Identify strengths, correctness issues, risks, missing "
            "considerations, and concrete improvements, prioritized by impact.",
        ),
        CouncilMode(
            "decision",
            "Compare alternatives and make a justified decision.",
            "Define relevant decision criteria, compare viable alternatives against them, expose "
            "uncertainty, and make one justified recommendation.",
        ),
        CouncilMode(
            "debug",
            "Generate and rank hypotheses for a technical problem.",
            "Form distinct root-cause hypotheses, rank them by evidence and likelihood, propose "
            "discriminating checks, and recommend the safest next action.",
        ),
        CouncilMode(
            "plan",
            "Turn an objective into an executable implementation plan.",
            "Produce a phased plan with dependencies, risks, validation criteria, and clear "
            "completion conditions.",
        ),
    )
}


def apply_mode(query: str, mode_name: str) -> str:
    mode = MODES[mode_name]
    if not mode.instruction:
        return query
    return f"COUNCIL MODE: {mode.name}\n{mode.instruction}\n\nUSER REQUEST:\n{query}"


def print_modes(args: argparse.Namespace) -> int:
    if args.json:
        print(json.dumps([asdict(mode) for mode in MODES.values()], indent=2))
        return 0
    for mode in MODES.values():
        print(f"{mode.name:10} {mode.description}")
    return 0
