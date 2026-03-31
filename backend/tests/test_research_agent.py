import unittest
from unittest.mock import AsyncMock

import httpx

from backend.agents.research_agent import ResearchAgent
from backend.models.schemas import ResearchRequest
from backend.services.arxiv_service import ArxivPaper, ArxivService
from backend.services.semantic_scholar_service import (
    SemanticScholarPaper,
    SemanticScholarService,
)


class ResearchAgentTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_run_uses_arxiv_results_when_available(self) -> None:
        arxiv_service = ArxivService()
        arxiv_service.search = AsyncMock(
            return_value=[
                ArxivPaper(
                    title="Multi-Agent Systems for Science",
                    authors=["Jane Doe"],
                    summary="A paper about multi-agent systems in science.",
                    entry_id="http://arxiv.org/abs/2501.00001v1",
                )
            ]
        )
        semantic_service = SemanticScholarService()
        semantic_service.search = AsyncMock(return_value=[])
        agent = ResearchAgent(
            arxiv_service=arxiv_service,
            semantic_scholar_service=semantic_service,
        )

        results = await agent.run(
            ResearchRequest(query="multi agent science", max_results=3)
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].source, "arXiv")
        self.assertEqual(results[0].external_id, "arxiv:2501.00001v1")
        self.assertGreaterEqual(results[0].relevance_score, 60)

    async def test_run_falls_back_when_service_fails(self) -> None:
        arxiv_service = ArxivService()
        arxiv_service.search = AsyncMock(side_effect=httpx.ConnectError("network down"))
        semantic_service = SemanticScholarService()
        semantic_service.search = AsyncMock(
            side_effect=httpx.ConnectError("network down")
        )
        agent = ResearchAgent(
            arxiv_service=arxiv_service,
            semantic_scholar_service=semantic_service,
        )

        results = await agent.run(
            ResearchRequest(query="multi agent science", max_results=2)
        )

        self.assertEqual(len(results), 2)
        self.assertTrue(all(result.source == "Fallback" for result in results))

    async def test_run_merges_and_deduplicates_multiple_sources(self) -> None:
        arxiv_service = ArxivService()
        arxiv_service.search = AsyncMock(
            return_value=[
                ArxivPaper(
                    title="Multi-Agent Systems for Science",
                    authors=["Jane Doe"],
                    summary="A paper about multi-agent systems in science.",
                    entry_id="http://arxiv.org/abs/2501.00001v1",
                )
            ]
        )
        semantic_service = SemanticScholarService()
        semantic_service.search = AsyncMock(
            return_value=[
                SemanticScholarPaper(
                    title="Multi-Agent Systems for Science",
                    authors=["Jane Doe", "John Roe"],
                    abstract="A broader knowledge graph view of multi-agent science.",
                    paper_id="semantic-001",
                    url="https://www.semanticscholar.org/paper/semantic-001",
                ),
                SemanticScholarPaper(
                    title="Autonomous Literature Review Agents",
                    authors=["Sam Smith"],
                    abstract="A study of autonomous agent pipelines for literature review.",
                    paper_id="semantic-002",
                    url="https://www.semanticscholar.org/paper/semantic-002",
                ),
            ]
        )
        agent = ResearchAgent(
            arxiv_service=arxiv_service,
            semantic_scholar_service=semantic_service,
        )

        results = await agent.run(
            ResearchRequest(query="multi agent science", max_results=5)
        )

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].title, "Multi-Agent Systems for Science")
        self.assertIn(results[0].source, {"arXiv", "Semantic Scholar"})


if __name__ == "__main__":
    unittest.main()
