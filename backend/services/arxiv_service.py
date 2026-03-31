from __future__ import annotations

from dataclasses import dataclass
from typing import Final
from xml.etree import ElementTree

import httpx


ARXIV_API_URL: Final[str] = "http://export.arxiv.org/api/query"
ATOM_NAMESPACE: Final[dict[str, str]] = {"atom": "http://www.w3.org/2005/Atom"}


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
            response = await self._client.get(self.base_url, params=params)
        else:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(self.base_url, params=params)

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

    @staticmethod
    def _read_text(entry: ElementTree.Element, selector: str) -> str:
        node = entry.find(selector, ATOM_NAMESPACE)
        if node is None or node.text is None:
            return ""
        return node.text.strip()
