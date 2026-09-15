from __future__ import annotations

import io
import re
from pathlib import Path

from pydantic import BaseModel, Field

try:
    from pypdf import PdfReader  # type: ignore[import-untyped]
    _PYPDF_AVAILABLE = True
except ImportError:
    _PYPDF_AVAILABLE = False


class ExtractedPage(BaseModel):
    page_number: int
    text: str


class StructuredDocument(BaseModel):
    raw_text: str
    pages: list[ExtractedPage] = Field(default_factory=list)
    sections: dict[str, str] = Field(default_factory=dict)


class PdfService:
    """Extract and normalize document text for downstream reader agents.

    Supports:
    - Plain UTF-8 text files / strings
    - Raw PDF bytes (via pypdf when available, with UTF-8 fallback)
    - File paths (auto-detects .pdf vs text)
    - Multi-page extraction with section classification
    """

    MAX_PAGES_LIMIT = 100

    SECTION_HEADERS = {
        "abstract": re.compile(r"^(?:abstract|summary)\b", re.IGNORECASE),
        "introduction": re.compile(r"^(?:1\.?\s*)?introduction\b", re.IGNORECASE),
        "methodology": re.compile(r"^(?:\d\.?\s*)?(?:methodology|methods|proposed\s+approach|system\s+design|architecture)\b", re.IGNORECASE),
        "results": re.compile(r"^(?:\d\.?\s*)?(?:results|experiments|empirical\s+evaluation|findings)\b", re.IGNORECASE),
        "discussion": re.compile(r"^(?:\d\.?\s*)?(?:discussion|analysis|limitations)\b", re.IGNORECASE),
        "conclusion": re.compile(r"^(?:\d\.?\s*)?(?:conclusion|conclusions|future\s+work)\b", re.IGNORECASE),
        "references": re.compile(r"^(?:references|bibliography)\b", re.IGNORECASE),
    }

    def __init__(self, max_pages: int = 100) -> None:
        self.max_pages = max(1, min(max_pages, self.MAX_PAGES_LIMIT))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract_text_from_file(self, path: str | Path) -> str:
        file_path = Path(path)
        if file_path.suffix.lower() == ".pdf":
            return self.extract_text_from_bytes(file_path.read_bytes())
        raw_text = file_path.read_text(encoding="utf-8", errors="ignore")
        return self.normalize_text(raw_text)

    def extract_structured_document(self, payload: bytes) -> StructuredDocument:
        """Extract multi-page text and academic sections from document bytes."""
        pages: list[ExtractedPage] = []
        if _PYPDF_AVAILABLE and self._looks_like_pdf(payload):
            try:
                reader = PdfReader(io.BytesIO(payload))
                for idx, page in enumerate(reader.pages, start=1):
                    if idx > self.max_pages:
                        break
                    p_text = self.normalize_text(page.extract_text() or "")
                    if p_text:
                        pages.append(ExtractedPage(page_number=idx, text=p_text))
            except Exception:
                pass

        if not pages:
            raw_str = self.normalize_text(payload.decode("utf-8", errors="ignore"))
            pages = [ExtractedPage(page_number=1, text=raw_str)] if raw_str else []

        full_raw_text = "\n\n".join(p.text for p in pages)
        sections = self.segment_sections(full_raw_text)

        return StructuredDocument(
            raw_text=full_raw_text,
            pages=pages,
            sections=sections,
        )

    def segment_sections(self, text: str) -> dict[str, str]:
        """Classify blocks of text into standard academic sections."""
        lines = text.splitlines()
        sections: dict[str, list[str]] = {}
        current_section = "preamble"

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            matched_sec = None
            if len(stripped) < 80:
                for sec_name, pattern in self.SECTION_HEADERS.items():
                    if pattern.match(stripped):
                        matched_sec = sec_name
                        break

            if matched_sec:
                current_section = matched_sec
                sections.setdefault(current_section, [])
            else:
                sections.setdefault(current_section, []).append(stripped)

        return {k: "\n".join(v) for k, v in sections.items() if v}

    def extract_text_from_bytes(self, payload: bytes) -> str:
        """Extract text from raw bytes — tries PDF parsing first, then UTF-8."""
        if _PYPDF_AVAILABLE and self._looks_like_pdf(payload):
            extracted = self._extract_pdf_text(payload)
            if extracted:
                return self.normalize_text(extracted)
        # Fallback: treat as UTF-8 text
        raw_text = payload.decode("utf-8", errors="ignore")
        return self.normalize_text(raw_text)

    def normalize_text(self, text: str) -> str:
        """Collapse excess whitespace and normalise line endings."""
        collapsed = text.replace("\r\n", "\n").replace("\r", "\n")
        # Remove form-feed characters common in PDFs
        collapsed = collapsed.replace("\x0c", "\n")
        # Collapse runs of blank lines to at most two
        collapsed = re.sub(r"\n{3,}", "\n\n", collapsed)
        # Collapse horizontal whitespace
        collapsed = re.sub(r"[ \t]+", " ", collapsed)
        # Strip lines that contain only whitespace
        lines = [ln.rstrip() for ln in collapsed.splitlines()]
        return "\n".join(lines).strip()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _looks_like_pdf(data: bytes) -> bool:
        return data[:5] == b"%PDF-"

    def _extract_pdf_text(self, data: bytes) -> str:
        """Extract text pages from a PDF binary blob up to max_pages."""
        try:
            reader = PdfReader(io.BytesIO(data))
            parts: list[str] = []
            for idx, page in enumerate(reader.pages, start=1):
                if idx > self.max_pages:
                    break
                page_text = page.extract_text() or ""
                if page_text.strip():
                    parts.append(page_text)
            return "\n\n".join(parts)
        except Exception:  # noqa: BLE001
            return ""

