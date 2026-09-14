from fastapi import APIRouter, Depends, HTTPException, Query, Request
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

from backend.services.academic_exporter import AcademicExporterService

router = APIRouter(prefix="/research", tags=["research"])


def get_orchestrator() -> Orchestrator:
    return Orchestrator()


def get_session_store() -> SessionStore:
    settings = get_settings()
    return SessionStore(settings.local_storage_path)


def get_pdf_service() -> PdfService:
    return PdfService()


def get_academic_exporter() -> AcademicExporterService:
    return AcademicExporterService()


@router.post("", response_model=ResearchResponse)
async def run_research(
    request: ResearchRequest,
    orchestrator: Orchestrator = Depends(get_orchestrator),
) -> ResearchResponse:
    return await orchestrator.process(request)


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


@router.post("/upload-pdf", response_model=ResearchResponse)
async def upload_pdf_document(
    request: Request,
    title: str = Query(default="Uploaded Document"),
    pdf_service: PdfService = Depends(get_pdf_service),
    orchestrator: Orchestrator = Depends(get_orchestrator),
) -> ResearchResponse:
    """Extract text from uploaded raw PDF bytes and process through the pipeline."""
    payload = await request.body()
    if not payload:
        raise HTTPException(status_code=400, detail="Empty file payload received.")
    extracted_text = pdf_service.extract_text_from_bytes(payload)
    if not extracted_text or len(extracted_text.strip()) < 20:
        raise HTTPException(
            status_code=422,
            detail="Unable to extract meaningful text from document (content too short or empty).",
        )
    return await orchestrator.process_document(title, extracted_text)


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


@router.get("/{session_id}/export/bibtex")
@router.get("/export/{session_id}/bibtex")
async def export_research_session_bibtex(
    session_id: str,
    session_store: SessionStore = Depends(get_session_store),
    exporter: AcademicExporterService = Depends(get_academic_exporter),
) -> Response:
    """Download research paper bibliography in BibTeX format (.bib)."""
    report = await session_store.get_report(session_id)
    bibtex_content = exporter.generate_bibtex(report)
    filename = f"references-{session_id[:8]}.bib"
    return Response(
        content=bibtex_content,
        media_type="application/x-bibtex",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{session_id}/export/markdown")
@router.get("/export/{session_id}/markdown")
async def export_research_session_markdown(
    session_id: str,
    session_store: SessionStore = Depends(get_session_store),
    exporter: AcademicExporterService = Depends(get_academic_exporter),
) -> Response:
    """Download full systematic review report as publication-grade Markdown (.md)."""
    report = await session_store.get_report(session_id)
    markdown_content = exporter.generate_markdown_report(report)
    filename = f"review-{session_id[:8]}.md"
    return Response(
        content=markdown_content,
        media_type="text/markdown",
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

