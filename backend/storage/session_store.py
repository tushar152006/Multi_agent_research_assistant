from __future__ import annotations

import json
import uuid
from pathlib import Path

from backend.models.schemas import ResearchResponse, SessionSummary


class SessionStore:
    """Persist research reports as local JSON files."""

    def __init__(self, base_path: str | Path) -> None:
        self.base_path = Path(base_path)
        self.sessions_path = self.base_path / "sessions"
        self.sessions_path.mkdir(parents=True, exist_ok=True)

    async def save_report(self, report: ResearchResponse) -> ResearchResponse:
        session_id = report.session_id or str(uuid.uuid4())
        persisted_report = report.model_copy(update={"session_id": session_id})
        session_file = self.sessions_path / f"{session_id}.json"
        session_file.write_text(
            persisted_report.model_dump_json(indent=2),
            encoding="utf-8",
        )
        return persisted_report

    async def get_report(self, session_id: str) -> ResearchResponse:
        session_file = self.sessions_path / f"{session_id}.json"
        payload = json.loads(session_file.read_text(encoding="utf-8"))
        return ResearchResponse.model_validate(payload)

    async def list_sessions(self) -> list[SessionSummary]:
        sessions: list[SessionSummary] = []
        for session_file in sorted(
            self.sessions_path.glob("*.json"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        ):
            payload = json.loads(session_file.read_text(encoding="utf-8"))
            report = ResearchResponse.model_validate(payload)
            if report.session_id is None:
                continue
            sessions.append(
                SessionSummary(
                    session_id=report.session_id,
                    query=report.query,
                    query_type=report.query_type,
                    generated_at=report.generated_at,
                )
            )
        return sessions
