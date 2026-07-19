"""Compatibility facade for the provider-neutral council orchestrator."""

from typing import Any

from .orchestration.council_orchestrator import get_default_orchestrator
from .orchestration.ranking import calculate_aggregate_rankings, parse_ranking_from_text


async def stage1_collect_responses(user_query: str) -> list[dict[str, Any]]:
    """Stage 1: collect individual responses from all enabled council advisors."""
    return await get_default_orchestrator().stage1_collect_responses(user_query)


async def stage2_collect_rankings(
    user_query: str,
    stage1_results: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    """Stage 2: collect rankings from all enabled council advisors."""
    return await get_default_orchestrator().stage2_collect_rankings(user_query, stage1_results)


async def stage3_synthesize_final(
    user_query: str,
    stage1_results: list[dict[str, Any]],
    stage2_results: list[dict[str, Any]],
    aggregate_rankings: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Stage 3: synthesize final response through the configured chairman advisor."""
    return await get_default_orchestrator().stage3_synthesize_final(
        user_query,
        stage1_results,
        stage2_results,
        aggregate_rankings,
    )


async def generate_conversation_title(user_query: str) -> str:
    """Generate a short title for a conversation."""
    return await get_default_orchestrator().generate_conversation_title(user_query)


async def run_full_council(user_query: str) -> tuple[list, list, dict, dict]:
    """Run the complete 3-stage council process."""
    return await get_default_orchestrator().run_full_council(user_query)
