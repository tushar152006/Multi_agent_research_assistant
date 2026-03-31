import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from backend.core.config import get_settings
from backend.api.main import app


class ApiTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        session_dir = Path(get_settings().local_storage_path)
        if session_dir.exists():
            for path in session_dir.glob("sessions/*.json"):
                path.unlink()
        cls.client = TestClient(app)

    def test_healthcheck(self) -> None:
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_research_endpoint_returns_structured_response(self) -> None:
        response = self.client.post(
            "/api/v1/research",
            json={
                "query": "multi agent research systems",
                "max_results": 2,
                "query_type": "simple_search",
            },
        )

        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["query"], "multi agent research systems")
        self.assertEqual(payload["query_type"], "simple_search")
        self.assertEqual(len(payload["papers"]), 2)
        self.assertEqual(len(payload["reader_outputs"]), 2)
        self.assertIsNotNone(payload["analysis"])
        self.assertIsNotNone(payload["critique"])
        self.assertIsNotNone(payload["implementation_plan"])
        self.assertIsNotNone(payload["session_id"])
        self.assertEqual(
            payload["execution_trace"][0]["agent_name"],
            "research_agent",
        )
        self.assertEqual(
            payload["execution_trace"][-1]["agent_name"],
            "session_store",
        )

        session_response = self.client.get(f"/api/v1/research/{payload['session_id']}")
        self.assertEqual(session_response.status_code, 200)
        self.assertEqual(session_response.json()["session_id"], payload["session_id"])

    def test_research_sessions_can_be_listed(self) -> None:
        create_response = self.client.post(
            "/api/v1/research",
            json={
                "query": "research session listing",
                "max_results": 1,
                "query_type": "simple_search",
            },
        )
        self.assertEqual(create_response.status_code, 200)

        list_response = self.client.get("/api/v1/research")
        payload = list_response.json()

        self.assertEqual(list_response.status_code, 200)
        self.assertTrue(payload["sessions"])


if __name__ == "__main__":
    unittest.main()
