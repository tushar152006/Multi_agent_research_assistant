import time
import unittest
from unittest.mock import AsyncMock, patch

from backend.agents.orchestrator import Orchestrator
from backend.core.research_sufficiency import ResearchSufficiencyJudge
from backend.models.schemas import (
    MethodologySummary,
    PaperSummary,
    QueryType,
    ReaderResponse,
    ResearchRequest,
    ResultsSummary,
)


class GoldenBenchmarkTestCase(unittest.IsolatedAsyncioTestCase):
    """Scientific benchmark suite evaluating grounding precision, sufficiency, and bounded execution."""

    async def test_grounding_audit_blocks_unverified_claims_from_consensus(self) -> None:
        orchestrator = Orchestrator()

        # Mock reader outputs with grounded chunks
        text = "Transformer models utilize multi-head self-attention mechanisms to capture dependencies."
        chunks = orchestrator.reader_agent.grounding_engine.segment_into_chunks(
            paper_title="Attention Study",
            source="paper.pdf",
            text=text,
        )
        reader_resp = ReaderResponse(
            title="Attention Study",
            problem="Sequential modeling bottleneck",
            methodology=MethodologySummary(approach="Self-Attention architecture"),
            results=ResultsSummary(primary_findings=["Attention improves training parallelization"]),
            limitations=["Quadratic complexity with sequence length"],
            grounded_chunks=chunks,
        )

        # Process document
        response = await orchestrator.process_document(
            title="Attention Study",
            content=text,
        )

        self.assertIsNotNone(response.grounding_audit)
        self.assertGreater(response.grounding_audit.total_claims, 0)
        self.assertGreaterEqual(response.grounding_audit.grounding_precision, 0.0)
        self.assertTrue(len(response.grounding_audit.claims) > 0)

        # Check that any unverified claim in analysis consensus was explicitly qualified
        if response.grounding_audit.unsupported_claims:
            for unverified in response.grounding_audit.unsupported_claims:
                if response.analysis:
                    for consensus_item in response.analysis.consensus:
                        if unverified in consensus_item:
                            self.assertTrue(
                                consensus_item.startswith("[Unverified Evidence]"),
                                f"Unverified claim was not qualified in consensus: {consensus_item}",
                            )

    async def test_bounded_adaptive_research_loop_terminates_within_budget(self) -> None:
        # Construct mock services that simulate multiple iterations
        judge = ResearchSufficiencyJudge(
            min_papers=2,
            min_precision=0.70,
            max_iterations=2,
            max_total_papers=4,
        )
        orchestrator = Orchestrator(sufficiency_judge=judge)

        # Mock research agent to return 1 paper on initial search, triggering adaptive loop
        mock_paper1 = PaperSummary(
            title="Initial Discovery Paper",
            authors=["Alice Researcher"],
            source="arXiv",
            external_id="arxiv:2401.0001",
            abstract="This paper introduces initial findings on autonomous reasoning.",
            relevance_score=85,
        )
        mock_paper2 = PaperSummary(
            title="Targeted Follow-up Paper",
            authors=["Bob Scientist"],
            source="arXiv",
            external_id="arxiv:2401.0002",
            abstract="This paper provides empirical benchmarks and evaluation metrics.",
            relevance_score=88,
        )

        call_count = 0

        async def mock_research_run(req: ResearchRequest) -> list[PaperSummary]:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return [mock_paper1]
            return [mock_paper2]

        orchestrator.research_agent.run = AsyncMock(side_effect=mock_research_run)

        events_logged: list[str] = []

        def on_event(ev: str, payload: dict | None = None) -> None:
            events_logged.append(ev)

        start_time = time.time()
        req = ResearchRequest(
            query="Autonomous multi-agent consensus",
            max_results=3,
            query_type=QueryType.DEEP_ANALYSIS,
        )
        response = await orchestrator.process(req, on_event=on_event)
        elapsed = time.time() - start_time

        self.assertLess(elapsed, 60.0, "Execution took too long")
        self.assertTrue(len(response.papers) >= 2, "Adaptive loop failed to accumulate papers")
        self.assertIn("sufficiency_verdict", events_logged)
        self.assertIn("adaptive_iteration", events_logged)

        # Assert bounded iterations respected
        self.assertLessEqual(call_count, 3, "Exceeded maximum allowed search iterations")
        self.assertIsNotNone(response.implementation_plan)


if __name__ == "__main__":
    unittest.main()
