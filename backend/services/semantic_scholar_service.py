from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final

import httpx


SEMANTIC_SCHOLAR_API_URL: Final[str] = (
    "https://api.semanticscholar.org/graph/v1/paper/search"
)


@dataclass(slots=True)
class SemanticScholarPaper:
    title: str
    authors: list[str]
    abstract: str
    paper_id: str
    url: str
    open_access_pdf_url: str | None = None


class SemanticScholarService:
    """Client for Semantic Scholar paper search and open-access retrieval."""

    def __init__(
        self,
        base_url: str = SEMANTIC_SCHOLAR_API_URL,
        timeout: float = 15.0,
        api_key: str | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = base_url
        self.timeout = timeout
        self.api_key = api_key
        self._client = client

    async def search(
        self,
        query: str,
        max_results: int = 5,
    ) -> list[SemanticScholarPaper]:
        params = {
            "query": query,
            "limit": max_results,
            "fields": "title,abstract,authors,paperId,url,openAccessPdf",
        }

        headers = self._build_headers()
        if self._client is not None:
            response = await self._client.get(
                self.base_url,
                params=params,
                headers=headers,
            )
        else:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    self.base_url,
                    params=params,
                    headers=headers,
                )

        response.raise_for_status()
        return self.parse_response(response.json())

    def parse_response(
        self,
        payload: dict[str, Any],
    ) -> list[SemanticScholarPaper]:
        items = payload.get("data", [])
        papers: list[SemanticScholarPaper] = []

        for item in items:
            authors = [
                author["name"].strip()
                for author in item.get("authors", [])
                if isinstance(author, dict) and author.get("name")
            ]
            oa_info = item.get("openAccessPdf")
            oa_url = (
                oa_info.get("url").strip()
                if isinstance(oa_info, dict) and oa_info.get("url")
                else None
            )
            papers.append(
                SemanticScholarPaper(
                    title=(item.get("title") or "").strip(),
                    authors=authors,
                    abstract=" ".join((item.get("abstract") or "").split()),
                    paper_id=(item.get("paperId") or "").strip(),
                    url=(item.get("url") or "").strip(),
                    open_access_pdf_url=oa_url,
                )
            )

        return papers

    async def fetch_pdf_text(
        self,
        pdf_url: str,
        max_bytes: int = 10_000_000,
    ) -> str | None:
        """Fetch and extract full text from an open-access PDF link with strict SSRF controls."""
        if not pdf_url:
            return None

        from backend.core.security import is_safe_url
        if not is_safe_url(pdf_url):
            return None

        import asyncio
        from urllib.parse import urljoin
        from backend.services.pdf_service import PdfService

        try:
            pdf_service = PdfService()
            current_url = pdf_url

            # Limit redirect hops to 3, validating every hop against SSRF policy
            for _ in range(4):
                if not is_safe_url(current_url):
                    return None

                async with httpx.AsyncClient(
                    timeout=self.timeout, follow_redirects=False
                ) as client:
                    response = await client.get(current_url)
                    if response.status_code in (301, 302, 303, 307, 308):
                        location = response.headers.get("location")
                        if not location:
                            return None
                        current_url = urljoin(current_url, location)
                        continue
                    elif response.status_code == 200 and len(response.content) <= max_bytes:
                        extracted = await asyncio.to_thread(
                            pdf_service.extract_text_from_bytes, response.content
                        )
                        if extracted and len(extracted) > 200:
                            return extracted
                    return None
            return None
        except Exception:
            return None

    def _build_headers(self) -> dict[str, str]:
        if not self.api_key:
            return {}
        return {"x-api-key": self.api_key}
