import unittest

from fastapi.testclient import TestClient

from backend.main import app


class ApiSmokeTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

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


if __name__ == "__main__":
    unittest.main()
