import asyncio
import json
import re
import uuid
from pathlib import Path

from fastapi import HTTPException

from backend.models.schemas import ResearchResponse, SessionSummary


class SessionStore:
    """Persist research reports as local JSON files with non-blocking async operations."""

    def __init__(self, base_path: str | Path, user_id: str = "default") -> None:
        self.base_path = Path(base_path)
        self.user_id = self._sanitize_user_id(user_id)
        self.sessions_path = self.base_path / "sessions" / self.user_id
        self.sessions_path.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _sanitize_user_id(user_id: str) -> str:
        if not user_id or not re.match(r"^[a-zA-Z0-9_-]+$", user_id):
            return "default"
        return user_id

    @staticmethod
    def _validate_session_id(session_id: str) -> None:
        if not session_id or not re.match(r"^[a-zA-Z0-9_-]+$", session_id):
            raise HTTPException(status_code=400, detail=f"Invalid session ID '{session_id}'.")

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    async def save_report(self, report: ResearchResponse) -> ResearchResponse:
        session_id = report.session_id or str(uuid.uuid4())
        self._validate_session_id(session_id)
        persisted_report = report.model_copy(update={"session_id": session_id})
        session_file = self.sessions_path / f"{session_id}.json"
        
        def _write() -> None:
            session_file.write_text(
                persisted_report.model_dump_json(indent=2),
                encoding="utf-8",
            )

        await asyncio.to_thread(_write)
        return persisted_report

    def _resolve_session_file(self, session_id: str) -> Path:
        session_file = self.sessions_path / f"{session_id}.json"
        if session_file.exists():
            return session_file
        if self.user_id == "default":
            legacy_file = self.base_path / "sessions" / f"{session_id}.json"
            if legacy_file.exists():
                return legacy_file
        return session_file

    async def delete_report(self, session_id: str) -> bool:
        """Delete a session file. Returns True if it existed, False otherwise."""
        self._validate_session_id(session_id)
        session_file = self._resolve_session_file(session_id)

        def _delete() -> bool:
            if not session_file.exists():
                return False
            session_file.unlink()
            return True

        return await asyncio.to_thread(_delete)

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    async def get_report(self, session_id: str) -> ResearchResponse:
        self._validate_session_id(session_id)
        session_file = self._resolve_session_file(session_id)

        def _read() -> str:
            if not session_file.exists():
                raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
            return session_file.read_text(encoding="utf-8")

        raw = await asyncio.to_thread(_read)
        payload = json.loads(raw)
        return ResearchResponse.model_validate(payload)

    async def export_report_json(self, session_id: str) -> str:
        """Return the raw JSON string for a session (for file downloads)."""
        self._validate_session_id(session_id)
        session_file = self._resolve_session_file(session_id)

        def _read() -> str:
            if not session_file.exists():
                raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
            return session_file.read_text(encoding="utf-8")

        return await asyncio.to_thread(_read)

    async def list_sessions(self) -> list[SessionSummary]:
        def _scan() -> list[SessionSummary]:
            sessions: list[SessionSummary] = []
            for session_file in sorted(
                self.sessions_path.glob("*.json"),
                key=lambda path: path.stat().st_mtime,
                reverse=True,
            ):
                try:
                    payload = json.loads(session_file.read_text(encoding="utf-8"))
                    report = ResearchResponse.model_validate(payload)
                except Exception:  # noqa: BLE001
                    continue

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

        return await asyncio.to_thread(_scan)


