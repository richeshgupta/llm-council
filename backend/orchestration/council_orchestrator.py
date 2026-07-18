"""Provider-neutral LLM Council orchestrator."""

from __future__ import annotations

import uuid
from typing import Any

from ..advisors.base import Advisor, AdvisorMessage, AdvisorRequest, AdvisorStatus
from ..advisors.registry import AdvisorRegistry
from .executor import run_advisors_parallel
from .prompts import (
    ADVISOR_SYSTEM_PROMPT,
    build_stage1_prompt,
    build_stage2_prompt,
    build_stage3_prompt,
    build_title_prompt,
)
from .ranking import calculate_aggregate_rankings, parse_ranking_from_text


class CouncilOrchestrator:
    """Runs the three-stage council using provider-neutral advisors."""

    def __init__(self, registry: AdvisorRegistry | None = None):
        self.registry = registry or AdvisorRegistry()
        self.defaults = self.registry.config.defaults

    def _messages(self, prompt: str) -> list[AdvisorMessage]:
        return [
            AdvisorMessage(role="system", content=ADVISOR_SYSTEM_PROMPT),
            AdvisorMessage(role="user", content=prompt),
        ]

    def _request(self, stage: str, prompt: str, timeout_seconds: float | None = None) -> AdvisorRequest:
        return AdvisorRequest(
            run_id=str(uuid.uuid4()),
            stage=stage,
            messages=self._messages(prompt),
            prompt_text=prompt,
            timeout_seconds=timeout_seconds,
        )

    async def stage1_collect_responses(self, user_query: str) -> list[dict[str, Any]]:
        advisors = self.registry.get_council_advisors()
        prompt = build_stage1_prompt(user_query)

        responses = await run_advisors_parallel(
            advisors,
            lambda _advisor: self._request("stage1", prompt),
            self.defaults.max_parallel_api_requests,
            self.defaults.max_parallel_cli_processes,
        )

        results = []
        for response in responses:
            if response.status == AdvisorStatus.SUCCESS:
                results.append(
                    {
                        "model": response.metadata.get("model") or response.display_name,
                        "advisor_id": response.advisor_id,
                        "display_name": response.display_name,
                        "provider": response.provider,
                        "mode": response.mode.value,
                        "response": response.content or "",
                        "status": response.status.value,
                        "latency_ms": response.latency_ms,
                    }
                )
        return results

    async def stage2_collect_rankings(
        self,
        user_query: str,
        stage1_results: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], dict[str, str]]:
        advisors = self.registry.get_council_advisors()
        prompt, label_to_model = build_stage2_prompt(user_query, stage1_results)

        responses = await run_advisors_parallel(
            advisors,
            lambda _advisor: self._request("stage2", prompt),
            self.defaults.max_parallel_api_requests,
            self.defaults.max_parallel_cli_processes,
        )

        results = []
        for response in responses:
            if response.status == AdvisorStatus.SUCCESS:
                full_text = response.content or ""
                results.append(
                    {
                        "model": response.metadata.get("model") or response.display_name,
                        "advisor_id": response.advisor_id,
                        "display_name": response.display_name,
                        "provider": response.provider,
                        "mode": response.mode.value,
                        "ranking": full_text,
                        "parsed_ranking": parse_ranking_from_text(full_text),
                        "status": response.status.value,
                        "latency_ms": response.latency_ms,
                    }
                )

        return results, label_to_model

    async def stage3_synthesize_final(
        self,
        user_query: str,
        stage1_results: list[dict[str, Any]],
        stage2_results: list[dict[str, Any]],
        aggregate_rankings: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        advisor = self.registry.get_chairman_advisor()
        prompt = build_stage3_prompt(user_query, stage1_results, stage2_results, aggregate_rankings)
        response = await advisor.ask(self._request("stage3", prompt))

        if response.status != AdvisorStatus.SUCCESS:
            return {
                "model": response.metadata.get("model") or advisor.display_name,
                "advisor_id": response.advisor_id,
                "display_name": response.display_name,
                "provider": response.provider,
                "mode": response.mode.value,
                "response": "Error: Unable to generate final synthesis.",
                "status": response.status.value,
                "error_type": response.error_type,
            }

        return {
            "model": response.metadata.get("model") or advisor.display_name,
            "advisor_id": response.advisor_id,
            "display_name": response.display_name,
            "provider": response.provider,
            "mode": response.mode.value,
            "response": response.content or "",
            "status": response.status.value,
            "latency_ms": response.latency_ms,
        }

    async def generate_conversation_title(self, user_query: str) -> str:
        advisor = self.registry.get_title_generator_advisor()
        prompt = build_title_prompt(user_query)
        response = await advisor.ask(self._request("title", prompt, timeout_seconds=30.0))

        if response.status != AdvisorStatus.SUCCESS or not response.content:
            return "New Conversation"

        title = response.content.strip().strip('"\'')
        if len(title) > 50:
            title = title[:47] + "..."
        return title

    async def run_full_council(self, user_query: str) -> tuple[list, list, dict, dict]:
        stage1_results = await self.stage1_collect_responses(user_query)
        if not stage1_results:
            return [], [], {
                "model": "error",
                "response": "All advisors failed to respond. Please try again.",
                "status": "failed",
            }, {}

        stage2_results, label_to_model = await self.stage2_collect_rankings(user_query, stage1_results)
        aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)
        stage3_result = await self.stage3_synthesize_final(
            user_query,
            stage1_results,
            stage2_results,
            aggregate_rankings,
        )
        metadata = {
            "label_to_model": label_to_model,
            "aggregate_rankings": aggregate_rankings,
        }
        return stage1_results, stage2_results, stage3_result, metadata


_default_orchestrator: CouncilOrchestrator | None = None


def get_default_orchestrator() -> CouncilOrchestrator:
    global _default_orchestrator
    if _default_orchestrator is None:
        _default_orchestrator = CouncilOrchestrator()
    return _default_orchestrator

