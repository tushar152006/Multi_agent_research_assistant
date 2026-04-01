from fastapi import APIRouter, Depends
from fastapi.responses import Response

from backend.agents.orchestrator import Orchestrator
from backend.core.config import get_settings
from backend.models.schemas import (
    ResearchRequest,
    ResearchResponse,
    SessionListResponse,
    DeleteResponse,
    UploadTextRequest,
)
from backend.storage.session_store import SessionStore
from backend.services.pdf_service import PdfService

router = APIRouter(prefix="/research", tags=["research"])


def get_orchestrator() -> Orchestrator:
    return Orchestrator()


def get_session_store() -> SessionStore:
    settings = get_settings()
    return SessionStore(settings.local_storage_path)


def get_pdf_service() -> PdfService:
    return PdfService()


@router.post("/analyze-doc", response_model=ResearchResponse)
async def analyze_document(
    request: UploadTextRequest,
    orchestrator: Orchestrator = Depends(get_orchestrator),
) -> ResearchResponse:
    """Perform a research workflow on a specifically provided document/text."""
    # We create a pseudo-research request where the query is the title
    # and we manually pass the content to the orchestrator's agents
    # In a real implementation, we'd adjust the orchestrator to skip discovery
    # but for now, we'll just process it as a special case.
    return await orchestrator.process_document(request.title, request.content)


@router.get("/export/{session_id}", response_class=Response)
async def export_research_session(
    session_id: str,
    session_store: SessionStore = Depends(get_session_store),
) -> Response:
    """Download a session's full report as a JSON file."""
    json_content = await session_store.export_report_json(session_id)
    filename = f"research-{session_id[:8]}.json"
    return Response(
        content=json_content,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{session_id}", response_model=ResearchResponse)
async def get_research_session(
    session_id: str,
    session_store: SessionStore = Depends(get_session_store),
) -> ResearchResponse:
    return await session_store.get_report(session_id)


@router.delete("/{session_id}", response_model=DeleteResponse)
async def delete_research_session(
    session_id: str,
    session_store: SessionStore = Depends(get_session_store),
) -> DeleteResponse:
    """Delete a saved research session."""
    deleted = await session_store.delete_report(session_id)
    return DeleteResponse(session_id=session_id, deleted=deleted)


@router.get("", response_model=SessionListResponse)
async def list_research_sessions(
    session_store: SessionStore = Depends(get_session_store),
) -> SessionListResponse:
    return SessionListResponse(sessions=await session_store.list_sessions())

