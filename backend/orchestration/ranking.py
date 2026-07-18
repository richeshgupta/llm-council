"""Ranking parsing and aggregation."""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any


def parse_ranking_from_text(ranking_text: str) -> list[str]:
    """Parse the FINAL RANKING section from a model response."""
    if "FINAL RANKING:" in ranking_text:
        parts = ranking_text.split("FINAL RANKING:")
        if len(parts) >= 2:
            ranking_section = parts[1]
            numbered_matches = re.findall(r"\d+\.\s*Response [A-Z]", ranking_section)
            if numbered_matches:
                return [re.search(r"Response [A-Z]", match).group() for match in numbered_matches]
            return re.findall(r"Response [A-Z]", ranking_section)

    return re.findall(r"Response [A-Z]", ranking_text)


def calculate_aggregate_rankings(
    stage2_results: list[dict[str, Any]],
    label_to_model: dict[str, str],
) -> list[dict[str, Any]]:
    """Calculate average rank by model from parsed peer rankings."""
    model_positions = defaultdict(list)

    for ranking in stage2_results:
        parsed_ranking = ranking.get("parsed_ranking") or parse_ranking_from_text(ranking.get("ranking", ""))
        for position, label in enumerate(parsed_ranking, start=1):
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

    aggregate.sort(key=lambda item: item["average_rank"])
    return aggregate

