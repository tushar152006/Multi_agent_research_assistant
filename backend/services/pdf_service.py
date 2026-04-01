from __future__ import annotations

import io
import re
from pathlib import Path

try:
    from pypdf import PdfReader  # type: ignore[import-untyped]
    _PYPDF_AVAILABLE = True
except ImportError:
    _PYPDF_AVAILABLE = False


class PdfService:
    """Extract and normalize document text for downstream reader agents.

    Supports:
    - Plain UTF-8 text files / strings
    - Raw PDF bytes (via pypdf when available, with UTF-8 fallback)
    - File paths (auto-detects .pdf vs text)
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract_text_from_file(self, path: str | Path) -> str:
        file_path = Path(path)
        if file_path.suffix.lower() == ".pdf":
            return self.extract_text_from_bytes(file_path.read_bytes())
        raw_text = file_path.read_text(encoding="utf-8", errors="ignore")
        return self.normalize_text(raw_text)

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

    @staticmethod
    def _extract_pdf_text(data: bytes) -> str:
        """Extract all text pages from a PDF binary blob."""
        try:
            reader = PdfReader(io.BytesIO(data))
            parts: list[str] = []
            for page in reader.pages:
                page_text = page.extract_text() or ""
                if page_text.strip():
                    parts.append(page_text)
            return "\n\n".join(parts)
        except Exception:  # noqa: BLE001
            return ""

