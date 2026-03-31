from __future__ import annotations

import re
from pathlib import Path


class PdfService:
    """Normalize document text for downstream reader agents.

    This is a lightweight first implementation that works with plain text
    sources today and leaves a clean seam for real PDF parsers later.
    """

    def extract_text_from_file(self, path: str | Path) -> str:
        file_path = Path(path)
        raw_text = file_path.read_text(encoding="utf-8")
        return self.normalize_text(raw_text)

    def extract_text_from_bytes(self, payload: bytes) -> str:
        raw_text = payload.decode("utf-8", errors="ignore")
        return self.normalize_text(raw_text)

    def normalize_text(self, text: str) -> str:
        collapsed = text.replace("\r\n", "\n").replace("\r", "\n")
        collapsed = re.sub(r"\n{3,}", "\n\n", collapsed)
        collapsed = re.sub(r"[ \t]+", " ", collapsed)
        return collapsed.strip()
