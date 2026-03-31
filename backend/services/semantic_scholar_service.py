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


class SemanticScholarService:
    """Client for Semantic Scholar paper search."""

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
            "fields": "title,abstract,authors,paperId,url",
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
            papers.append(
                SemanticScholarPaper(
                    title=(item.get("title") or "").strip(),
                    authors=authors,
                    abstract=" ".join((item.get("abstract") or "").split()),
                    paper_id=(item.get("paperId") or "").strip(),
                    url=(item.get("url") or "").strip(),
                )
            )

        return papers

    def _build_headers(self) -> dict[str, str]:
        if not self.api_key:
            return {}
        return {"x-api-key": self.api_key}
