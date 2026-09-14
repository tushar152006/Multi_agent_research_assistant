import unittest

from backend.core.citation_grounding import (
    CitationGroundingEngine,
    GroundedClaim,
    GroundedChunk,
)


class CitationGroundingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = CitationGroundingEngine()

    def test_chunk_segmentation_and_deterministic_hashing(self) -> None:
        text = (
            "This study evaluates retrieval quality across multiple academic datasets. "
            "The results show that hybrid retrieval improves recall in low-resource settings."
        )

        first = self.engine.segment_into_chunks(
            paper_title="Retrieval Study",
            source="paper.pdf",
            text=text,
        )
        second = self.engine.segment_into_chunks(
            paper_title="Retrieval Study",
            source="paper.pdf",
            text=text,
        )

        self.assertEqual(len(first), 2)
        self.assertEqual(first[0].content_hash, second[0].content_hash)
        self.assertEqual(first[0].chunk_id, second[0].chunk_id)
        self.assertNotEqual(first[0].content_hash, first[1].content_hash)

    def test_claim_anchoring_finds_supporting_quote(self) -> None:
        chunks = [
            GroundedChunk.create(
                paper_title="Hybrid Retrieval",
                source="paper.pdf",
                section="results",
                sentence_index=0,
                text=(
                    "Hybrid retrieval improves recall in low-resource settings "
                    "when compared with sparse retrieval alone."
                ),
            )
        ]

        claim = self.engine.anchor_claim(
            claim="Hybrid retrieval improves recall in low-resource settings.",
            category="consensus",
            candidate_chunks=chunks,
            threshold=0.6,
        )

        self.assertEqual(claim.verification_status, "unverified")
        self.assertEqual(len(claim.citations), 1)
        self.assertEqual(
            claim.citations[0].exact_quote,
            chunks[0].text,
        )

    def test_hallucinated_quote_is_unverified(self) -> None:
        source_chunk = GroundedChunk.create(
            paper_title="Retrieval Study",
            source="paper.pdf",
            section="abstract",
            sentence_index=0,
            text="The evaluation measures retrieval recall across three public datasets.",
        )

        hallucinated = GroundedClaim(
            claim_text="The method achieves perfect retrieval accuracy.",
            category="theme",
            citations=[
                {
                    "paper_title": source_chunk.paper_title,
                    "chunk_id": source_chunk.chunk_id,
                    "exact_quote": "The method achieves perfect retrieval accuracy.",
                    "confidence_score": 0.99,
                }
            ],
        )

        result = self.engine.verify_synthesis(
            claims=[hallucinated],
            source_chunks=[source_chunk],
        )

        self.assertEqual(result.verified_claims, 0)
        self.assertEqual(result.grounding_precision, 0.0)
        self.assertEqual(
            result.claims[0].verification_status,
            "unverified",
        )
        self.assertFalse(result.claims[0].citations[0].is_verified)

    def test_grounding_precision(self) -> None:
        chunks = [
            GroundedChunk.create(
                paper_title="Paper One",
                source="one.pdf",
                section="abstract",
                sentence_index=0,
                text="The proposed method improves recall across benchmark datasets.",
            ),
            GroundedChunk.create(
                paper_title="Paper Two",
                source="two.pdf",
                section="results",
                sentence_index=0,
                text="The model reduces latency during large-scale retrieval.",
            ),
        ]

        verified_one = self.engine.anchor_claim(
            claim="The proposed method improves recall across benchmark datasets.",
            category="theme",
            candidate_chunks=chunks,
            threshold=0.6,
        )
        verified_two = self.engine.anchor_claim(
            claim="The model reduces latency during large-scale retrieval.",
            category="theme",
            candidate_chunks=chunks,
            threshold=0.6,
        )
        unsupported = GroundedClaim(
            claim_text="The system eliminates all hallucinations.",
            category="gap",
            citations=[],
        )

        result = self.engine.verify_synthesis(
            claims=[verified_one, verified_two, unsupported],
            source_chunks=chunks,
        )

        self.assertEqual(result.total_claims, 3)
        self.assertEqual(result.verified_claims, 2)
        self.assertAlmostEqual(result.grounding_precision, 0.6667, places=4)
        self.assertEqual(len(result.unsupported_claims), 1)


if __name__ == "__main__":
    unittest.main()
