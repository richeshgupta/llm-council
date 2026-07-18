import asyncio
import sys
import unittest
from types import SimpleNamespace

from backend.advisors.base import (
    Advisor,
    AdvisorMode,
    AdvisorRequest,
    AdvisorResponse,
    AdvisorRole,
    AdvisorStatus,
)
from backend.advisors.subprocess_runner import run_subprocess
from backend.orchestration.council_orchestrator import CouncilOrchestrator
from backend.orchestration.ranking import calculate_aggregate_rankings, parse_ranking_from_text


class FakeAdvisor(Advisor):
    mode = AdvisorMode.LOCAL
    supports_streaming = False

    def __init__(self, advisor_id, content_by_stage, roles=None):
        self.id = advisor_id
        self.display_name = advisor_id
        self.provider = "fake"
        self.roles = set(roles or [AdvisorRole.COUNCIL_MEMBER])
        self.content_by_stage = content_by_stage
        self.requests = []

    async def ask(self, request: AdvisorRequest) -> AdvisorResponse:
        self.requests.append(request)
        content = self.content_by_stage.get(request.stage, "")
        return AdvisorResponse(
            advisor_id=self.id,
            display_name=self.display_name,
            provider=self.provider,
            mode=self.mode,
            status=AdvisorStatus.SUCCESS,
            content=content,
            metadata={"model": self.id},
        )


class FakeRegistry:
    def __init__(self):
        self.config = SimpleNamespace(
            defaults=SimpleNamespace(
                max_parallel_api_requests=8,
                max_parallel_cli_processes=2,
            )
        )
        self.member_a = FakeAdvisor(
            "advisor-a",
            {
                "stage1": "Answer from A",
                "stage2": "Evaluation\n\nFINAL RANKING:\n1. Response A\n2. Response B",
            },
        )
        self.member_b = FakeAdvisor(
            "advisor-b",
            {
                "stage1": "Answer from B",
                "stage2": "Evaluation\n\nFINAL RANKING:\n1. Response B\n2. Response A",
            },
        )
        self.chairman = FakeAdvisor(
            "chairman",
            {"stage3": "Final synthesized answer", "title": "Test Title"},
            roles=[AdvisorRole.CHAIRMAN, AdvisorRole.TITLE_GENERATOR],
        )

    def get_council_advisors(self):
        return [self.member_a, self.member_b]

    def get_chairman_advisor(self):
        return self.chairman

    def get_title_generator_advisor(self):
        return self.chairman


class RankingTests(unittest.TestCase):
    def test_parse_ranking_from_final_section(self):
        text = "Notes mention Response B first.\n\nFINAL RANKING:\n1. Response C\n2. Response A"
        self.assertEqual(parse_ranking_from_text(text), ["Response C", "Response A"])

    def test_calculate_aggregate_rankings(self):
        results = [
            {"parsed_ranking": ["Response A", "Response B"]},
            {"parsed_ranking": ["Response B", "Response A"]},
            {"parsed_ranking": ["Response B", "Response A"]},
        ]
        label_to_model = {"Response A": "model-a", "Response B": "model-b"}
        aggregate = calculate_aggregate_rankings(results, label_to_model)
        self.assertEqual(aggregate[0]["model"], "model-b")
        self.assertEqual(aggregate[0]["average_rank"], 1.33)


class SubprocessRunnerTests(unittest.IsolatedAsyncioTestCase):
    async def test_subprocess_success(self):
        result = await run_subprocess(
            [sys.executable, "-c", "import sys; print(sys.stdin.read().upper())"],
            "ok",
            timeout_seconds=5,
        )
        self.assertEqual(result.exit_code, 0)
        self.assertFalse(result.timed_out)
        self.assertIn("OK", result.stdout)

    async def test_subprocess_timeout(self):
        result = await run_subprocess(
            [sys.executable, "-c", "import time; time.sleep(2)"],
            "",
            timeout_seconds=0.1,
        )
        self.assertTrue(result.timed_out)


class CouncilOrchestratorTests(unittest.IsolatedAsyncioTestCase):
    async def test_full_council_handoff(self):
        orchestrator = CouncilOrchestrator(FakeRegistry())
        stage1, stage2, stage3, metadata = await orchestrator.run_full_council("question")

        self.assertEqual(len(stage1), 2)
        self.assertEqual(len(stage2), 2)
        self.assertEqual(stage3["response"], "Final synthesized answer")
        self.assertEqual(
            metadata["label_to_model"],
            {"Response A": "advisor-a", "Response B": "advisor-b"},
        )
        self.assertIn("aggregate_rankings", metadata)


if __name__ == "__main__":
    unittest.main()
