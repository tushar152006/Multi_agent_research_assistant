from fastapi import APIRouter, Depends

from backend.agents.orchestrator import Orchestrator
from backend.core.config import get_settings
from backend.models.schemas import (
    ResearchRequest,
    ResearchResponse,
    SessionListResponse,
)
from backend.storage.session_store import SessionStore

router = APIRouter(prefix="/research", tags=["research"])


def get_orchestrator() -> Orchestrator:
    return Orchestrator()


def get_session_store() -> SessionStore:
    settings = get_settings()
    return SessionStore(settings.local_storage_path)


@router.post("", response_model=ResearchResponse)
async def run_research(
    request: ResearchRequest,
    orchestrator: Orchestrator = Depends(get_orchestrator),
) -> ResearchResponse:
    return await orchestrator.process(request)


@router.get("/{session_id}", response_model=ResearchResponse)
async def get_research_session(
    session_id: str,
    session_store: SessionStore = Depends(get_session_store),
) -> ResearchResponse:
    return await session_store.get_report(session_id)


@router.get("", response_model=SessionListResponse)
async def list_research_sessions(
    session_store: SessionStore = Depends(get_session_store),
) -> SessionListResponse:
    return SessionListResponse(sessions=await session_store.list_sessions())
