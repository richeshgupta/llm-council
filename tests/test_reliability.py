import asyncio
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from types import SimpleNamespace

from pydantic import ValidationError

from backend.advisors.base import (
    Advisor,
    AdvisorMessage,
    AdvisorMode,
    AdvisorRequest,
    AdvisorResponse,
    AdvisorRole,
    AdvisorStatus,
    render_cli_prompt,
)
from backend.advisors.config import AdvisorsConfig, load_advisors_config
from backend.advisors.registry import AdvisorRegistry
from backend.cli import run_query
from backend.orchestration.council_orchestrator import CouncilOrchestrator
from backend.orchestration.executor import run_advisors_parallel
from backend.orchestration.prompts import build_stage2_prompt
from backend.orchestration.ranking import calculate_aggregate_rankings, parse_ranking_from_text


class ScriptedAdvisor(Advisor):
    mode = AdvisorMode.LOCAL

    def __init__(self, advisor_id, script, roles=None):
        self.id = advisor_id
        self.display_name = advisor_id
        self.provider = "test"
        self.roles = set(roles or [AdvisorRole.COUNCIL_MEMBER])
        self.script = script
        self.requests = []

    async def ask(self, request):
        self.requests.append(request)
        action = self.script.get(request.stage, "")
        if isinstance(action, Exception):
            raise action
        if isinstance(action, AdvisorStatus):
            return AdvisorResponse(
                advisor_id=self.id,
                display_name=self.display_name,
                provider=self.provider,
                mode=self.mode,
                status=action,
                error_type="scripted_failure",
                user_message="scripted failure",
                metadata={"model": self.id},
            )
        return AdvisorResponse(
            advisor_id=self.id,
            display_name=self.display_name,
            provider=self.provider,
            mode=self.mode,
            status=AdvisorStatus.SUCCESS,
            content=action,
            metadata={"model": self.id},
        )


class ScriptedRegistry:
    def __init__(self, members, chairmen, api_limit=4, stage_timeout=5):
        self.members = members
        self.chairmen = chairmen
        self.config = SimpleNamespace(
            defaults=SimpleNamespace(
                stage_timeout_seconds=stage_timeout,
                max_parallel_api_requests=api_limit,
                max_parallel_cli_processes=2,
            )
        )

    def get_council_advisors(self):
        return self.members

    def get_chairman_advisor(self):
        if not self.chairmen:
            raise ValueError("no chairman")
        return self.chairmen[0]

    def get_chairman_candidates(self):
        return self.chairmen


class ConfigTests(unittest.TestCase):
    def test_default_config_is_independent_of_working_directory(self):
        original = os.getcwd()
        try:
            os.chdir(tempfile.gettempdir())
            config = load_advisors_config()
        finally:
            os.chdir(original)
        self.assertEqual([a.provider for a in config.advisors if a.enabled], ["codex_cli", "claude_cli"])

    def test_missing_explicit_config_fails(self):
        with self.assertRaises(FileNotFoundError):
            load_advisors_config("/definitely/missing/advisors.json")

    def test_invalid_concurrency_and_duplicate_ids_fail(self):
        base = {
            "defaults": {"max_parallel_cli_processes": 0},
            "advisors": [
                {
                    "id": "same",
                    "display_name": "One",
                    "provider": "codex_cli",
                    "mode": "cli",
                    "roles": ["council_member", "chairman"],
                },
                {
                    "id": "same",
                    "display_name": "Two",
                    "provider": "claude_cli",
                    "mode": "cli",
                    "roles": ["council_member"],
                },
            ],
            "chairman": {"advisor_id": "same"},
        }
        with self.assertRaises(ValidationError):
            AdvisorsConfig.model_validate(base)

    def test_provider_mode_mismatch_fails_during_registry_creation(self):
        config = AdvisorsConfig.model_validate(
            {
                "advisors": [
                    {
                        "id": "codex",
                        "display_name": "Codex",
                        "provider": "codex_cli",
                        "mode": "api",
                        "roles": ["council_member", "chairman"],
                    }
                ],
                "chairman": {"advisor_id": "codex"},
            }
        )
        with self.assertRaisesRegex(ValueError, "does not match"):
            AdvisorRegistry(config)


class PromptAndRankingTests(unittest.TestCase):
    def test_cli_prompt_preserves_roles(self):
        request = AdvisorRequest(
            run_id="run",
            stage="stage1",
            messages=[
                AdvisorMessage(role="system", content="SYSTEM RULE"),
                AdvisorMessage(role="user", content="USER TASK"),
            ],
            prompt_text="USER TASK",
        )
        rendered = render_cli_prompt(request)
        self.assertIn("<SYSTEM>\nSYSTEM RULE", rendered)
        self.assertIn("<USER>\nUSER TASK", rendered)

    def test_parser_rejects_incidental_mentions(self):
        self.assertEqual(parse_ranking_from_text("Response B seems better than Response A"), [])

    def test_aggregate_rejects_duplicate_or_incomplete_ballots(self):
        mapping = {"Response A": "a", "Response B": "b"}
        results = [
            {"parsed_ranking": ["Response A", "Response A"]},
            {"parsed_ranking": ["Response A"]},
        ]
        self.assertEqual(calculate_aggregate_rankings(results, mapping), [])

    def test_labels_scale_past_z(self):
        results = [
            {"advisor_id": f"id-{index}", "model": "same", "response": "answer"}
            for index in range(28)
        ]
        _, mapping = build_stage2_prompt("question", results)
        self.assertIn("Response AA", mapping)
        self.assertIn("Response AB", mapping)
        self.assertEqual(len(set(mapping.values())), 28)


class ReliabilityTests(unittest.IsolatedAsyncioTestCase):
    async def test_executor_isolates_adapter_exception(self):
        good = ScriptedAdvisor("good", {"stage1": "answer"})
        bad = ScriptedAdvisor("bad", {"stage1": RuntimeError("boom")})
        request = AdvisorRequest(run_id="r", stage="stage1", messages=[])
        responses = await run_advisors_parallel([good, bad], lambda _: request, 2, 2)
        self.assertEqual(responses[0].status, AdvisorStatus.SUCCESS)
        self.assertEqual(responses[1].status, AdvisorStatus.FAILED)
        self.assertEqual(responses[1].error_type, "adapter_exception")

    async def test_partial_failure_is_reported_and_run_succeeds(self):
        good = ScriptedAdvisor(
            "good",
            {
                "stage1": "good answer",
                "stage2": "FINAL RANKING:\n1. Response A",
                "stage3": "final",
            },
            roles=[AdvisorRole.COUNCIL_MEMBER, AdvisorRole.CHAIRMAN],
        )
        bad = ScriptedAdvisor("bad", {"stage1": AdvisorStatus.FAILED})
        orchestrator = CouncilOrchestrator(ScriptedRegistry([good, bad], [good]))
        stage1, stage2, stage3, metadata = await orchestrator.run_full_council("question")
        self.assertEqual(len(stage1), 1)
        self.assertEqual(stage2, [])
        self.assertEqual(stage3["status"], "success")
        self.assertEqual(metadata["failures"]["stage1"][0]["advisor_id"], "bad")

    async def test_chairman_failover(self):
        member = ScriptedAdvisor(
            "member",
            {"stage1": "answer", "stage3": "fallback synthesis"},
            roles=[AdvisorRole.COUNCIL_MEMBER, AdvisorRole.CHAIRMAN],
        )
        primary = ScriptedAdvisor(
            "primary",
            {"stage3": AdvisorStatus.FAILED},
            roles=[AdvisorRole.CHAIRMAN],
        )
        orchestrator = CouncilOrchestrator(ScriptedRegistry([member], [primary, member]))
        _, _, stage3, metadata = await orchestrator.run_full_council("question")
        self.assertEqual(stage3["advisor_id"], "member")
        self.assertEqual(stage3["status"], "success")
        self.assertEqual(metadata["failures"]["stage3"][0]["advisor_id"], "primary")

    async def test_all_advisors_failed_has_diagnostics(self):
        failed = ScriptedAdvisor("failed", {"stage1": AdvisorStatus.TIMEOUT})
        orchestrator = CouncilOrchestrator(ScriptedRegistry([failed], []))
        stage1, stage2, stage3, metadata = await orchestrator.run_full_council("question")
        self.assertEqual(stage1, [])
        self.assertEqual(stage2, [])
        self.assertEqual(stage3["error_type"], "all_advisors_failed")
        self.assertEqual(metadata["failures"]["stage1"][0]["status"], "timeout")

    async def test_cli_failure_returns_nonzero_and_json_is_parseable(self):
        failed = ScriptedAdvisor("failed", {"stage1": AdvisorStatus.FAILED})
        registry = ScriptedRegistry([failed], [])
        stdout, stderr = StringIO(), StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = await run_query("question", registry, output="json", show_progress=False)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(code, 1)
        self.assertEqual(payload["stage3"]["status"], "failed")
        self.assertIn("Warning: stage1", stderr.getvalue())

    async def test_stage_timeout_is_enforced_for_uncooperative_adapter(self):
        class SlowAdvisor(ScriptedAdvisor):
            async def ask(self, request):
                await asyncio.sleep(1)
                return await super().ask(request)

        slow = SlowAdvisor("slow", {"stage1": "late"})
        orchestrator = CouncilOrchestrator(
            ScriptedRegistry([slow], [], stage_timeout=0.01)
        )
        _, _, stage3, metadata = await orchestrator.run_full_council("question")
        self.assertEqual(stage3["status"], "failed")
        self.assertEqual(metadata["failures"]["stage1"][0]["error_type"], "stage_timeout")

    async def test_concurrency_limit_is_shared_across_runs(self):
        state = {"active": 0, "maximum": 0}

        class TrackingAdvisor(ScriptedAdvisor):
            async def ask(self, request):
                state["active"] += 1
                state["maximum"] = max(state["maximum"], state["active"])
                try:
                    await asyncio.sleep(0.02)
                    return await super().ask(request)
                finally:
                    state["active"] -= 1

        advisor = TrackingAdvisor("tracked", {"stage1": "answer"})
        orchestrator = CouncilOrchestrator(
            ScriptedRegistry([advisor], [advisor], api_limit=1)
        )
        await asyncio.gather(
            orchestrator.stage1_collect_responses("one"),
            orchestrator.stage1_collect_responses("two"),
        )
        self.assertEqual(state["maximum"], 1)


if __name__ == "__main__":
    unittest.main()
