import shutil
import unittest
from datetime import datetime, timezone
from pathlib import Path

from backend.models.schemas import ResearchResponse
from backend.storage.session_store import SessionStore


class SessionStoreTestCase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.base_path = Path("backend/tests/.tmp/session_store")
        if self.base_path.exists():
            shutil.rmtree(self.base_path)
        self.store = SessionStore(self.base_path)

    async def asyncTearDown(self) -> None:
        if self.base_path.exists():
            shutil.rmtree(self.base_path)

    async def test_save_and_get_report(self) -> None:
        report = ResearchResponse(
            query="multi agent research",
            query_type="simple_search",
            summary="Test report",
            papers=[],
            execution_trace=[],
            generated_at=datetime.now(timezone.utc),
        )

        saved = await self.store.save_report(report)
        loaded = await self.store.get_report(saved.session_id)

        self.assertIsNotNone(saved.session_id)
        self.assertEqual(loaded.session_id, saved.session_id)
        self.assertEqual(loaded.query, "multi agent research")

    async def test_list_sessions_returns_saved_items(self) -> None:
        report = ResearchResponse(
            query="agent memory",
            query_type="simple_search",
            summary="Another report",
            papers=[],
            execution_trace=[],
            generated_at=datetime.now(timezone.utc),
        )

        saved = await self.store.save_report(report)
        sessions = await self.store.list_sessions()

        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0].session_id, saved.session_id)
        self.assertEqual(sessions[0].query, "agent memory")
