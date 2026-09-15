import asyncio
import re
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
from backend.core.rate_limiter import research_limiter

router = APIRouter(prefix="/research", tags=["research"])


def get_current_user(request: Request) -> str:
    """Extract authenticated user identity from Authorization header or X-User-ID."""
    auth_header = request.headers.get("authorization")
    user_header = request.headers.get("x-user-id")

    user_id: str | None = None
    if auth_header and auth_header.startswith("Bearer "):
        user_id = auth_header[7:].strip()
    elif user_header:
        user_id = user_header.strip()

    settings = get_settings()
    if not user_id:
        if getattr(settings, "auth_required", False) or request.headers.get("x-require-auth"):
            raise HTTPException(
                status_code=401,
                detail="Authentication credentials were not provided.",
            )
        return "default"

    if not re.match(r"^[a-zA-Z0-9_-]+$", user_id):
        raise HTTPException(status_code=400, detail="Invalid user identifier.")

    return user_id


def get_session_store(user_id: str = Depends(get_current_user)) -> SessionStore:
    settings = get_settings()
    return SessionStore(settings.local_storage_path, user_id=user_id)


def get_orchestrator(
    session_store: SessionStore = Depends(get_session_store),
) -> Orchestrator:
    return Orchestrator(session_store=session_store)


def get_pdf_service() -> PdfService:
    return PdfService()


def get_academic_exporter() -> AcademicExporterService:
    return AcademicExporterService()


@router.post("", response_model=ResearchResponse)
async def run_research(
    request: ResearchRequest,
    http_request: Request,
    orchestrator: Orchestrator = Depends(get_orchestrator),
) -> ResearchResponse:
    research_limiter.check(http_request)
    return await orchestrator.process(request)


@router.post("/analyze-doc", response_model=ResearchResponse)
async def analyze_document(
    request: UploadTextRequest,
    http_request: Request,
    orchestrator: Orchestrator = Depends(get_orchestrator),
) -> ResearchResponse:
    """Perform a research workflow on a specifically provided document/text."""
    research_limiter.check(http_request)
    return await orchestrator.process_document(request.title, request.content)


MAX_PDF_UPLOAD_BYTES = 20 * 1024 * 1024  # 20MB


@router.post("/upload-pdf", response_model=ResearchResponse)
async def upload_pdf_document(
    request: Request,
    title: str = Query(default="Uploaded Document"),
    pdf_service: PdfService = Depends(get_pdf_service),
    orchestrator: Orchestrator = Depends(get_orchestrator),
) -> ResearchResponse:
    """Extract text from uploaded raw PDF bytes and process through the pipeline."""
    research_limiter.check(request)
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_PDF_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail="File payload exceeds maximum allowed size of 20MB.",
        )

    payload = await request.body()
    if not payload:
        raise HTTPException(status_code=400, detail="Empty file payload received.")
    if len(payload) > MAX_PDF_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail="File payload exceeds maximum allowed size of 20MB.",
        )

    extracted_text = await asyncio.to_thread(pdf_service.extract_text_from_bytes, payload)
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

