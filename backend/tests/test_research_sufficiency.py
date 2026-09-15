import unittest

from backend.core.citation_grounding import GroundingVerificationResult
from backend.core.research_sufficiency import ResearchSufficiencyJudge
from backend.models.schemas import AnalystResponse, PaperSummary


class ResearchSufficiencyTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.judge = ResearchSufficiencyJudge(
            min_papers=2,
            min_precision=0.65,
            max_iterations=3,
            max_total_papers=8,
        )

    def test_evaluate_insufficient_when_below_min_papers(self) -> None:
        papers = [
            PaperSummary(
                title="Single Paper",
                authors=["Author A"],
                source="arXiv",
                external_id="arxiv:0001",
                abstract="Summary text.",
                relevance_score=80,
            )
        ]
        verdict = self.judge.evaluate(
            query="quantum computing",
            iteration=1,
            papers=papers,
        )

        self.assertFalse(verdict.is_sufficient)
        self.assertEqual(verdict.stop_reason, "insufficient_papers")
        self.assertTrue(len(verdict.recommended_queries) > 0)

    def test_evaluate_stops_when_max_iterations_reached(self) -> None:
        papers = [
            PaperSummary(
                title="Paper 1",
                authors=["A"],
                source="arXiv",
                external_id="arxiv:1",
                abstract="Content 1",
                relevance_score=80,
            ),
            PaperSummary(
                title="Paper 2",
                authors=["B"],
                source="arXiv",
                external_id="arxiv:2",
                abstract="Content 2",
                relevance_score=85,
            ),
        ]
        verdict = self.judge.evaluate(
            query="multi agent systems",
            iteration=3,
            papers=papers,
        )

        self.assertTrue(verdict.is_sufficient)
        self.assertEqual(verdict.stop_reason, "max_iterations_reached")

    def test_evaluate_flags_missing_aspects_when_grounding_precision_is_low(self) -> None:
        papers = [
            PaperSummary(
                title="Paper 1",
                authors=["A"],
                source="arXiv",
                external_id="arxiv:1",
                abstract="Content 1",
                relevance_score=80,
            ),
            PaperSummary(
                title="Paper 2",
                authors=["B"],
                source="arXiv",
                external_id="arxiv:2",
                abstract="Content 2",
                relevance_score=85,
            ),
        ]
        grounding_audit = GroundingVerificationResult(
            total_claims=5,
            verified_claims=2,
            grounding_precision=0.40,
            claims=[],
            unsupported_claims=["Novel architecture eliminates hallucination."],
        )
        analysis = AnalystResponse(
            query="agent reasoning",
            themes=["agent reasoning"],
            gaps=["Evaluation across broader domains"],
        )

        verdict = self.judge.evaluate(
            query="agent reasoning",
            iteration=1,
            papers=papers,
            analysis=analysis,
            grounding_audit=grounding_audit,
        )

        self.assertFalse(verdict.is_sufficient)
        self.assertEqual(verdict.stop_reason, "evidence_needs_expansion")
        self.assertTrue(any("Grounding precision" in a for a in verdict.missing_aspects))
        self.assertTrue(len(verdict.recommended_queries) > 0)


if __name__ == "__main__":
    unittest.main()
