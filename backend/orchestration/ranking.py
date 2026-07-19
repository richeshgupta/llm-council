"""Ranking parsing and aggregation."""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any


def parse_ranking_from_text(ranking_text: str) -> list[str]:
    """Parse only numbered entries from an explicit FINAL RANKING section."""
    match = re.search(r"FINAL\s+RANKING\s*:\s*(.*)", ranking_text, re.IGNORECASE | re.DOTALL)
    if not match:
        return []
    return re.findall(
        r"^\s*\d+\.\s*(Response\s+[A-Z]+)\s*$",
        match.group(1),
        re.IGNORECASE | re.MULTILINE,
    )


def calculate_aggregate_rankings(
    stage2_results: list[dict[str, Any]],
    label_to_model: dict[str, str],
) -> list[dict[str, Any]]:
    """Calculate average rank by model from parsed peer rankings."""
    model_positions = defaultdict(list)
    expected_labels = set(label_to_model)

    for ranking in stage2_results:
        parsed_ranking = ranking.get("parsed_ranking") or parse_ranking_from_text(ranking.get("ranking", ""))
        normalized = [f"Response {label.split()[-1].upper()}" for label in parsed_ranking]
        if len(normalized) != len(expected_labels) or set(normalized) != expected_labels:
            continue
        for position, label in enumerate(normalized, start=1):
            if label in label_to_model:
                model_positions[label_to_model[label]].append(position)

    aggregate = []
    for model, positions in model_positions.items():
        if positions:
            aggregate.append(
                {
                    "model": model,
                    "average_rank": round(sum(positions) / len(positions), 2),
                    "rankings_count": len(positions),
                }
            )

    aggregate.sort(key=lambda item: (item["average_rank"], item["model"]))
    return aggregate
