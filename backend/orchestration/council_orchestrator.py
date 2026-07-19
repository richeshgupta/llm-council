"""Provider-neutral LLM Council orchestrator."""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Callable
from typing import Any

from ..advisors.base import (
    Advisor,
    AdvisorMessage,
    AdvisorRequest,
    AdvisorResponse,
    AdvisorStatus,
)
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


ProgressCallback = Callable[[str, dict[str, Any]], None]


class CouncilOrchestrator:
    """Run independent answers, peer review, and chairman synthesis."""

    def __init__(self, registry: AdvisorRegistry | None = None):
        self.registry = registry or AdvisorRegistry()
        self.defaults = self.registry.config.defaults
        self._api_semaphore = asyncio.Semaphore(self.defaults.max_parallel_api_requests)
        self._cli_semaphore = asyncio.Semaphore(self.defaults.max_parallel_cli_processes)

    def _messages(self, prompt: str) -> list[AdvisorMessage]:
        return [
            AdvisorMessage(role="system", content=ADVISOR_SYSTEM_PROMPT),
            AdvisorMessage(role="user", content=prompt),
        ]

    def _request(
        self,
        stage: str,
        prompt: str,
        advisor: Advisor | None = None,
        timeout_seconds: float | None = None,
        run_id: str | None = None,
    ) -> AdvisorRequest:
        timeout_candidates = [
            value
            for value in (
                timeout_seconds,
                getattr(advisor, "timeout_seconds", None),
                getattr(self.defaults, "stage_timeout_seconds", 240.0),
            )
            if value is not None
        ]
        return AdvisorRequest(
            run_id=run_id or str(uuid.uuid4()),
            stage=stage,
            messages=self._messages(prompt),
            prompt_text=prompt,
            timeout_seconds=min(timeout_candidates),
        )

    @staticmethod
    def _failure_details(response: AdvisorResponse) -> dict[str, Any]:
        return {
            "advisor_id": response.advisor_id,
            "display_name": response.display_name,
            "provider": response.provider,
            "status": response.status.value,
            "error_type": response.error_type,
            "message": response.user_message,
            "latency_ms": response.latency_ms,
        }

    @staticmethod
    def _stage1_result(response: AdvisorResponse) -> dict[str, Any]:
        return {
            "model": response.metadata.get("model") or response.display_name,
            "advisor_id": response.advisor_id,
            "display_name": response.display_name,
            "provider": response.provider,
            "mode": response.mode.value,
            "response": response.content or "",
            "status": response.status.value,
            "latency_ms": response.latency_ms,
        }

    @staticmethod
    def _stage2_result(response: AdvisorResponse) -> dict[str, Any]:
        full_text = response.content or ""
        return {
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

    async def _stage1_responses(self, user_query: str, run_id: str) -> list[AdvisorResponse]:
        advisors = self.registry.get_council_advisors()
        prompt = build_stage1_prompt(user_query)
        return await run_advisors_parallel(
            advisors,
            lambda advisor: self._request("stage1", prompt, advisor=advisor, run_id=run_id),
            self.defaults.max_parallel_api_requests,
            self.defaults.max_parallel_cli_processes,
            self._api_semaphore,
            self._cli_semaphore,
        )

    async def stage1_collect_responses(self, user_query: str) -> list[dict[str, Any]]:
        responses = await self._stage1_responses(user_query, str(uuid.uuid4()))
        return [
            self._stage1_result(response)
            for response in responses
            if response.status == AdvisorStatus.SUCCESS and (response.content or "").strip()
        ]

    async def _stage2_responses(
        self,
        user_query: str,
        stage1_results: list[dict[str, Any]],
        run_id: str,
    ) -> tuple[list[AdvisorResponse], dict[str, str]]:
        prompt, label_to_model = build_stage2_prompt(user_query, stage1_results)
        responses = await run_advisors_parallel(
            self.registry.get_council_advisors(),
            lambda advisor: self._request("stage2", prompt, advisor=advisor, run_id=run_id),
            self.defaults.max_parallel_api_requests,
            self.defaults.max_parallel_cli_processes,
            self._api_semaphore,
            self._cli_semaphore,
        )
        return responses, label_to_model

    async def stage2_collect_rankings(
        self,
        user_query: str,
        stage1_results: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], dict[str, str]]:
        responses, label_to_model = await self._stage2_responses(
            user_query, stage1_results, str(uuid.uuid4())
        )
        return [
            self._stage2_result(response)
            for response in responses
            if response.status == AdvisorStatus.SUCCESS and (response.content or "").strip()
        ], label_to_model

    def _chairman_candidates(self) -> list[Advisor]:
        if hasattr(self.registry, "get_chairman_candidates"):
            return self.registry.get_chairman_candidates()
        return [self.registry.get_chairman_advisor()]

    async def stage3_synthesize_final(
        self,
        user_query: str,
        stage1_results: list[dict[str, Any]],
        stage2_results: list[dict[str, Any]],
        aggregate_rankings: list[dict[str, Any]] | None = None,
        run_id: str | None = None,
    ) -> dict[str, Any]:
        prompt = build_stage3_prompt(user_query, stage1_results, stage2_results, aggregate_rankings)
        failures: list[dict[str, Any]] = []

        for advisor in self._chairman_candidates():
            response = (
                await run_advisors_parallel(
                    [advisor],
                    lambda candidate: self._request(
                        "stage3", prompt, advisor=candidate, run_id=run_id
                    ),
                    self.defaults.max_parallel_api_requests,
                    self.defaults.max_parallel_cli_processes,
                    self._api_semaphore,
                    self._cli_semaphore,
                )
            )[0]

            if response.status != AdvisorStatus.SUCCESS or not (response.content or "").strip():
                failures.append(self._failure_details(response))
                continue

            return {
                "model": response.metadata.get("model") or advisor.display_name,
                "advisor_id": response.advisor_id,
                "display_name": response.display_name,
                "provider": response.provider,
                "mode": response.mode.value,
                "response": response.content or "",
                "status": response.status.value,
                "latency_ms": response.latency_ms,
                "failover_attempts": failures,
            }

        fallback = self._best_available_answer(stage1_results, aggregate_rankings or [])
        if fallback:
            return {
                **fallback,
                "response": fallback["response"],
                "status": AdvisorStatus.DEGRADED.value,
                "error_type": "all_chairmen_failed",
                "failover_attempts": failures,
            }

        return {
            "model": "error",
            "advisor_id": None,
            "display_name": "No available chairman",
            "provider": None,
            "mode": None,
            "response": "Unable to generate final synthesis.",
            "status": AdvisorStatus.FAILED.value,
            "error_type": "all_chairmen_failed",
            "failover_attempts": failures,
        }

    @staticmethod
    def _best_available_answer(
        stage1_results: list[dict[str, Any]],
        aggregate_rankings: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        if not stage1_results:
            return None
        if aggregate_rankings:
            best_model = aggregate_rankings[0].get("model")
            for result in stage1_results:
                if result.get("advisor_id") == best_model or result.get("model") == best_model:
                    return dict(result)
        return dict(stage1_results[0])

    async def generate_conversation_title(self, user_query: str) -> str:
        advisor = self.registry.get_title_generator_advisor()
        prompt = build_title_prompt(user_query)
        response = (
            await run_advisors_parallel(
                [advisor],
                lambda candidate: self._request(
                    "title", prompt, advisor=candidate, timeout_seconds=30.0
                ),
                self.defaults.max_parallel_api_requests,
                self.defaults.max_parallel_cli_processes,
                self._api_semaphore,
                self._cli_semaphore,
            )
        )[0]
        if response.status != AdvisorStatus.SUCCESS or not response.content:
            return "New Conversation"
        title = response.content.strip().strip('"\'')
        return title[:47] + "..." if len(title) > 50 else title

    async def run_full_council(
        self,
        user_query: str,
        progress: ProgressCallback | None = None,
    ) -> tuple[list, list, dict, dict]:
        run_id = str(uuid.uuid4())

        def emit(event: str, **data: Any) -> None:
            if progress:
                progress(event, data)

        council_advisors = self.registry.get_council_advisors()
        emit("stage1_start", advisors=len(council_advisors))
        stage1_responses = await self._stage1_responses(user_query, run_id)
        stage1_results = [
            self._stage1_result(response)
            for response in stage1_responses
            if response.status == AdvisorStatus.SUCCESS and (response.content or "").strip()
        ]
        stage1_failures = [
            self._failure_details(response)
            for response in stage1_responses
            if response.status != AdvisorStatus.SUCCESS or not (response.content or "").strip()
        ]
        emit("stage1_complete", successful=len(stage1_results), failed=len(stage1_failures))

        if not stage1_results:
            return [], [], {
                "model": "error",
                "response": "All advisors failed to respond.",
                "status": AdvisorStatus.FAILED.value,
                "error_type": "all_advisors_failed",
            }, {
                "schema_version": 1,
                "run_id": run_id,
                "label_to_model": {},
                "label_to_advisor": {},
                "aggregate_rankings": [],
                "failures": {"stage1": stage1_failures, "stage2": [], "stage3": []},
            }

        stage2_failures: list[dict[str, Any]] = []
        if len(stage1_results) > 1:
            emit("stage2_start", advisors=len(council_advisors))
            stage2_responses, label_to_model = await self._stage2_responses(
                user_query, stage1_results, run_id
            )
            stage2_results = [
                self._stage2_result(response)
                for response in stage2_responses
                if response.status == AdvisorStatus.SUCCESS and (response.content or "").strip()
            ]
            stage2_failures = [
                self._failure_details(response)
                for response in stage2_responses
                if response.status != AdvisorStatus.SUCCESS or not (response.content or "").strip()
            ]
            emit("stage2_complete", successful=len(stage2_results), failed=len(stage2_failures))
        else:
            stage2_results = []
            label_to_model = {"Response A": stage1_results[0]["advisor_id"]}
            emit("stage2_skipped", reason="only one advisor produced an answer")

        aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)
        emit("stage3_start", candidates=len(self._chairman_candidates()))
        stage3_result = await self.stage3_synthesize_final(
            user_query,
            stage1_results,
            stage2_results,
            aggregate_rankings,
            run_id=run_id,
        )
        stage3_failures = stage3_result.get("failover_attempts", [])
        emit(
            "stage3_complete",
            successful=stage3_result.get("status") == AdvisorStatus.SUCCESS.value,
            failed=len(stage3_failures),
        )
        metadata = {
            "schema_version": 1,
            "run_id": run_id,
            "label_to_model": label_to_model,
            "label_to_advisor": label_to_model,
            "aggregate_rankings": aggregate_rankings,
            "failures": {
                "stage1": stage1_failures,
                "stage2": stage2_failures,
                "stage3": stage3_failures,
            },
        }
        return stage1_results, stage2_results, stage3_result, metadata


_default_orchestrator: CouncilOrchestrator | None = None


def get_default_orchestrator() -> CouncilOrchestrator:
    global _default_orchestrator
    if _default_orchestrator is None:
        _default_orchestrator = CouncilOrchestrator()
    return _default_orchestrator
