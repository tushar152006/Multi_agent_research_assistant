import asyncio
import re

import httpx

from backend.agents.base_agent import BaseAgent
from backend.core.config import get_settings
from backend.models.schemas import PaperSummary, ResearchRequest
from backend.services.arxiv_service import ArxivPaper, ArxivService
from backend.services.semantic_scholar_service import (
    SemanticScholarPaper,
    SemanticScholarService,
)
from backend.services.web_scraper_service import WebScraperService


class ResearchAgent(BaseAgent[ResearchRequest, list[PaperSummary]]):
    """Paper discovery agent backed by multiple providers with fallback."""

    name = "research_agent"

    def __init__(
        self,
        arxiv_service: ArxivService | None = None,
        semantic_scholar_service: SemanticScholarService | None = None,
        web_scraper_service: WebScraperService | None = None,
    ) -> None:
        settings = get_settings()
        self.arxiv_service = arxiv_service or ArxivService()
        self.semantic_scholar_service = semantic_scholar_service or SemanticScholarService(
            api_key=settings.semantic_scholar_api_key
        )
        self.web_scraper_service = web_scraper_service or WebScraperService()

    async def run(self, payload: ResearchRequest) -> list[PaperSummary]:
        normalized_query = payload.query.strip()
        
        # Parallel fetch from multiple sources
        arxiv_papers_task = self._safe_search_arxiv(normalized_query, payload.max_results)
        semantic_papers_task = self._safe_search_semantic_scholar(normalized_query, payload.max_results)
        web_papers_task = self._search_web(normalized_query, 3) # Always grab top 3 web results
        
        arxiv_papers, semantic_papers, web_papers = await asyncio.gather(
            arxiv_papers_task, 
            semantic_papers_task,
            web_papers_task
        )

        merged_papers = self._merge_and_rank_papers(
            query=normalized_query,
            arxiv_papers=arxiv_papers,
            semantic_papers=semantic_papers,
            web_papers=web_papers,
            max_results=payload.max_results,
        )

        return merged_papers

    async def _search_web(self, query: str, max_results: int) -> list[PaperSummary]:
        """Search the web and convert results to PaperSummary format."""
        try:
            results = await self.web_scraper_service.search_and_scrape(query, max_results)
            summaries = []
            for i, res in enumerate(results, start=1):
                summaries.append(PaperSummary(
                    title=res.title,
                    authors=["Web Article"],
                    source="Web",
                    external_id=f"web:{res.url}",
                    abstract=res.content,
                    relevance_score=self._score_relevance(query, res.title, res.content, i, source="Web")
                ))
            return summaries
        except Exception:
            return []

    async def _safe_search_arxiv(
        self,
        query: str,
        max_results: int,
    ) -> list[ArxivPaper]:
        try:
            return await self.arxiv_service.search(query, max_results=max_results)
        except (httpx.HTTPError, ValueError):
            return []

    async def _safe_search_semantic_scholar(
        self,
        query: str,
        max_results: int,
    ) -> list[SemanticScholarPaper]:
        try:
            return await self.semantic_scholar_service.search(
                query,
                max_results=max_results,
            )
        except (httpx.HTTPError, ValueError):
            return []

    def _merge_and_rank_papers(
        self,
        query: str,
        arxiv_papers: list[ArxivPaper],
        semantic_papers: list[SemanticScholarPaper],
        web_papers: list[PaperSummary],
        max_results: int,
    ) -> list[PaperSummary]:
        candidates: list[PaperSummary] = []
        for rank, paper in enumerate(arxiv_papers, start=1):
            candidates.append(self._to_arxiv_summary(paper, query, rank))
        for rank, paper in enumerate(semantic_papers, start=1):
            candidates.append(self._to_semantic_scholar_summary(paper, query, rank))
        
        # Add web papers
        candidates.extend(web_papers)

        deduplicated = self._deduplicate_papers(candidates)
        deduplicated.sort(
            key=lambda paper: (-paper.relevance_score, paper.title.lower())
        )
        return deduplicated[:max_results]

    def _to_arxiv_summary(
        self,
        paper: ArxivPaper,
        query: str,
        rank: int,
    ) -> PaperSummary:
        return PaperSummary(
            title=paper.title,
            authors=paper.authors or ["Unknown"],
            source="arXiv",
            external_id=self._normalize_external_id(paper.entry_id),
            abstract=paper.summary,
            relevance_score=self._score_relevance(
                query=query,
                title=paper.title,
                summary=paper.summary,
                rank=rank,
            ),
        )

    def _to_semantic_scholar_summary(
        self,
        paper: SemanticScholarPaper,
        query: str,
        rank: int,
    ) -> PaperSummary:
        external_id = paper.paper_id or paper.url or "semanticscholar:unknown"
        if paper.paper_id:
            external_id = f"semanticscholar:{paper.paper_id}"

        return PaperSummary(
            title=paper.title or "Untitled Paper",
            authors=paper.authors or ["Unknown"],
            source="Semantic Scholar",
            external_id=external_id,
            abstract=paper.abstract or "Abstract unavailable.",
            relevance_score=self._score_relevance(
                query=query,
                title=paper.title,
                summary=paper.abstract,
                rank=rank,
            ),
            pdf_url=paper.open_access_pdf_url,
        )

    @staticmethod
    def _normalize_external_id(entry_id: str) -> str:
        if not entry_id:
            return "arxiv:unknown"
        if "abs/" in entry_id:
            return f"arxiv:{entry_id.rsplit('abs/', maxsplit=1)[-1]}"
        return entry_id

    @staticmethod
    def _deduplicate_papers(papers: list[PaperSummary]) -> list[PaperSummary]:
        by_title: dict[str, PaperSummary] = {}
        by_id: dict[str, PaperSummary] = {}

        for paper in papers:
            title_key = re.sub(r"[^a-z0-9]+", "", paper.title.lower())
            id_key = paper.external_id.lower().strip() if paper.external_id else ""

            # Check if existing in either index
            existing = by_title.get(title_key) or (by_id.get(id_key) if id_key else None)

            if existing is None:
                by_title[title_key] = paper
                if id_key:
                    by_id[id_key] = paper
            else:
                # Keep the candidate with higher score or open-access PDF
                if (paper.pdf_url and not existing.pdf_url) or paper.relevance_score > existing.relevance_score:
                    by_title[title_key] = paper
                    if id_key:
                        by_id[id_key] = paper

        return list(by_title.values())

    @staticmethod
    def _score_relevance(query: str, title: str, summary: str, rank: int, source: str = "arXiv") -> int:
        norm_query = query.strip().lower()
        query_terms = {
            term.lower()
            for term in re.findall(r"[a-zA-Z0-9]+", norm_query)
            if len(term) > 2
        }
        text_title = title.lower()
        text_summary = summary.lower()
        full_text = f"{text_title} {text_summary}"

        if not query_terms:
            return 70

        # Term overlap
        overlap = sum(1 for term in query_terms if term in full_text)
        overlap_ratio = overlap / len(query_terms)

        # Exact phrase bonus
        phrase_bonus = 0
        if norm_query in text_title:
            phrase_bonus += 15
        elif norm_query in text_summary:
            phrase_bonus += 8

        # Authority bonus for scholarly archives vs raw web
        authority_bonus = 5 if source in ("arXiv", "Semantic Scholar") else 0

        base_score = int(50 + overlap_ratio * 35 + phrase_bonus + authority_bonus)
        rank_penalty = min((rank - 1) * 2, 12)
        return max(35, min(99, base_score - rank_penalty))

