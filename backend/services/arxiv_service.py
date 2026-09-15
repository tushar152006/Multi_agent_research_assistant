from __future__ import annotations

from dataclasses import dataclass
from typing import Final
from xml.etree import ElementTree

import httpx


ARXIV_API_URL: Final[str] = "https://export.arxiv.org/api/query"
ATOM_NAMESPACE: Final[dict[str, str]] = {"atom": "http://www.w3.org/2005/Atom"}
ARXIV_HEADERS: Final[dict[str, str]] = {
    "User-Agent": "MARA-Research-Assistant/1.0 (academic research; mailto:research@example.com)"
}


@dataclass(slots=True)
class ArxivPaper:
    title: str
    authors: list[str]
    summary: str
    entry_id: str


class ArxivService:
    """Client for the arXiv Atom API."""

    def __init__(
        self,
        base_url: str = ARXIV_API_URL,
        timeout: float = 15.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = base_url
        self.timeout = timeout
        self._client = client

    async def search(self, query: str, max_results: int = 5) -> list[ArxivPaper]:
        params = {
            "search_query": f"all:{query}",
            "start": 0,
            "max_results": max_results,
            "sortBy": "relevance",
            "sortOrder": "descending",
        }

        if self._client is not None:
            response = await self._client.get(
                self.base_url,
                params=params,
                headers=ARXIV_HEADERS,
                follow_redirects=True,
            )
        else:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                response = await client.get(
                    self.base_url,
                    params=params,
                    headers=ARXIV_HEADERS,
                )

        response.raise_for_status()
        return self.parse_response(response.text)

    def parse_response(self, xml_payload: str) -> list[ArxivPaper]:
        root = ElementTree.fromstring(xml_payload)
        papers: list[ArxivPaper] = []

        for entry in root.findall("atom:entry", ATOM_NAMESPACE):
            title = self._read_text(entry, "atom:title")
            summary = self._read_text(entry, "atom:summary")
            entry_id = self._read_text(entry, "atom:id")
            authors = [
                author_name.text.strip()
                for author in entry.findall("atom:author", ATOM_NAMESPACE)
                if (author_name := author.find("atom:name", ATOM_NAMESPACE)) is not None
                and author_name.text
            ]

            papers.append(
                ArxivPaper(
                    title=" ".join(title.split()),
                    authors=authors,
                    summary=" ".join(summary.split()),
                    entry_id=entry_id,
                )
            )

        return papers

    async def fetch_pdf_text(self, entry_id: str, max_bytes: int = 10_000_000) -> str | None:
        """Attempt to fetch and extract full text from an arXiv open-access PDF."""
        arxiv_id = (
            entry_id.rsplit("abs/", 1)[-1].strip()
            if "abs/" in entry_id
            else entry_id.rsplit("/", 1)[-1].strip()
        )
        if not arxiv_id:
            return None

        # Strip any prefix like 'arxiv:'
        if arxiv_id.lower().startswith("arxiv:"):
            arxiv_id = arxiv_id[6:]

        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        try:
            from backend.services.pdf_service import PdfService
            pdf_service = PdfService()

            async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
                response = await client.get(pdf_url, headers=ARXIV_HEADERS)
                if response.status_code == 200 and len(response.content) <= max_bytes:
                    extracted = pdf_service.extract_text_from_bytes(response.content)
                    if extracted and len(extracted) > 200:
                        return extracted
        except Exception:
            return None
        return None

    @staticmethod
    def _read_text(entry: ElementTree.Element, selector: str) -> str:
        node = entry.find(selector, ATOM_NAMESPACE)
        if node is None or node.text is None:
            return ""
        return node.text.strip()

