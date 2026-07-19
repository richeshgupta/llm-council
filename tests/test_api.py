import unittest
import tempfile
import uuid
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from backend.main import app, build_contextual_query
from backend import storage


class ApiSmokeTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_data_dir = storage.DATA_DIR
        storage.DATA_DIR = self.temp_dir.name
        self.client = TestClient(app)

    def tearDown(self):
        storage.DATA_DIR = self.original_data_dir
        self.temp_dir.cleanup()

    def test_root_health(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_advisors_endpoint(self):
        response = self.client.get("/api/advisors")
        self.assertEqual(response.status_code, 200)
        advisors = response.json()
        self.assertGreaterEqual(len(advisors), 1)
        self.assertIn("advisor_id", advisors[0])
        self.assertIn("provider", advisors[0])

    def test_advisor_health_endpoint(self):
        response = self.client.get("/api/advisors/health")
        self.assertEqual(response.status_code, 200)
        checks = response.json()
        self.assertGreaterEqual(len(checks), 1)
        self.assertIn("healthy", checks[0])

    def test_create_conversation_without_body(self):
        response = self.client.post("/api/conversations")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["messages"], [])

    def test_blank_message_is_rejected(self):
        response = self.client.post(
            "/api/conversations/not-found/message",
            json={"content": "   "},
        )
        self.assertEqual(response.status_code, 422)

    def test_follow_up_query_contains_conversation_context(self):
        conversation = {
            "messages": [
                {"role": "user", "content": "Use PostgreSQL"},
                {"role": "assistant", "stage3": {"response": "PostgreSQL selected"}},
            ]
        }
        query = build_contextual_query(conversation, "What database did we choose?")
        self.assertIn("Use PostgreSQL", query)
        self.assertIn("PostgreSQL selected", query)
        self.assertIn("CURRENT REQUEST:\nWhat database did we choose?", query)

    def test_stream_passes_aggregate_rankings_to_chairman(self):
        conversation_id = str(uuid.uuid4())
        storage.create_conversation(conversation_id)
        stage1 = [
            {
                "model": "model-a",
                "advisor_id": "a",
                "display_name": "A",
                "provider": "test",
                "mode": "local",
                "response": "answer a",
                "status": "success",
            },
            {
                "model": "model-b",
                "advisor_id": "b",
                "display_name": "B",
                "provider": "test",
                "mode": "local",
                "response": "answer b",
                "status": "success",
            },
        ]
        stage2 = [
            {
                "model": "judge",
                "advisor_id": "judge",
                "display_name": "Judge",
                "provider": "test",
                "mode": "local",
                "ranking": "FINAL RANKING:\n1. Response B\n2. Response A",
                "parsed_ranking": ["Response B", "Response A"],
                "status": "success",
            }
        ]
        label_map = {"Response A": "a", "Response B": "b"}
        synthesize = AsyncMock(return_value={"response": "final", "status": "success"})
        with (
            patch("backend.main.stage1_collect_responses", AsyncMock(return_value=stage1)),
            patch(
                "backend.main.stage2_collect_rankings",
                AsyncMock(return_value=(stage2, label_map)),
            ),
            patch("backend.main.stage3_synthesize_final", synthesize),
            patch("backend.main.generate_conversation_title", AsyncMock(return_value="Title")),
        ):
            response = self.client.post(
                f"/api/conversations/{conversation_id}/message/stream",
                json={"content": "question"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertIn('"type": "complete"', response.text)
        aggregate = synthesize.await_args.args[3]
        self.assertEqual(aggregate[0]["model"], "b")


if __name__ == "__main__":
    unittest.main()
