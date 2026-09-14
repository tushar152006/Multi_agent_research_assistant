import unittest

from backend.core.contradiction_matrix import (
    ContradictionPair,
    ContradictionSeverity,
)
from backend.core.evidence_graph import (
    EvidenceGraphEngine,
    GraphNodeType,
    GraphRelation,
)
from backend.core.prisma_review import (
    PrismaReviewEngine,
    PrismaStage,
    PrismaStatus,
)
from backend.models.schemas import (
    AnalystResponse,
    MethodologySummary,
    PaperSummary,
    ReaderResponse,
    ResultsSummary,
)


class PrismaAndEvidenceGraphTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.prisma_engine = PrismaReviewEngine(relevance_cutoff=50)
        self.graph_engine = EvidenceGraphEngine()

    def test_prisma_review_generates_flow_and_mermaid(self) -> None:
        raw_papers = [
            PaperSummary(
                title="Paper A",
                authors=["A"],
                source="arXiv",
                external_id="1",
                abstract="Summary of Paper A with extensive methodology.",
                relevance_score=85,
            ),
            PaperSummary(
                title="Paper A Duplicate",
                authors=["A"],
                source="Semantic Scholar",
                external_id="2",
                abstract="Duplicate text of Paper A.",
                relevance_score=85,
            ),
            PaperSummary(
                title="Paper B (Low Relevance)",
                authors=["B"],
                source="Web",
                external_id="3",
                abstract="Unrelated article with minimal details.",
                relevance_score=35,
            ),
        ]
        screened_papers = [raw_papers[0], raw_papers[2]]  # 1 duplicate removed

        reader_outputs = [
            ReaderResponse(
                title="Paper A",
                problem="Problem A",
                methodology=MethodologySummary(approach="App A", datasets=["DS1"], metrics=["acc"]),
                results=ResultsSummary(primary_findings=["Found A"], metrics={"acc": "90%"}),
                limitations=[],
                future_work=[],
                extracted_sections={},
            )
        ]

        result = self.prisma_engine.generate_flow(
            raw_papers=raw_papers,
            screened_papers=screened_papers,
            reader_outputs=reader_outputs,
        )

        self.assertEqual(result.total_identified, 3)
        self.assertEqual(result.duplicates_removed, 1)
        self.assertEqual(result.records_screened, 2)
        self.assertEqual(result.records_excluded, 1)
        self.assertEqual(result.studies_included, 1)
        self.assertEqual(len(result.audit_trail), 2)

        # Audit trail checks
        excluded_item = next(a for a in result.audit_trail if a.status == PrismaStatus.EXCLUDED)
        self.assertEqual(excluded_item.paper_title, "Paper B (Low Relevance)")
        self.assertEqual(excluded_item.stage, PrismaStage.ELIGIBILITY)

        included_item = next(a for a in result.audit_trail if a.status == PrismaStatus.INCLUDED)
        self.assertEqual(included_item.paper_title, "Paper A")

        # Mermaid flowchart check
        self.assertIn("graph TD", result.mermaid_flowchart)
        self.assertIn("Records Identified (n = 3)", result.mermaid_flowchart)
        self.assertIn("Studies Included in Synthesis (n = 1)", result.mermaid_flowchart)

    def test_evidence_graph_generates_nodes_edges_and_contradictions(self) -> None:
        reader_outputs = [
            ReaderResponse(
                title="Alpha Method Paper",
                problem="Efficiency",
                methodology=MethodologySummary(
                    approach="Quantized Attention",
                    datasets=["GLUE Benchmark", "SuperGLUE"],
                    metrics=["accuracy", "latency"],
                ),
                results=ResultsSummary(
                    primary_findings=["High speedup"],
                    metrics={"accuracy": "91.2%", "latency": "12ms"},
                ),
                limitations=[],
                future_work=[],
                extracted_sections={},
            ),
            ReaderResponse(
                title="Beta Baseline Paper",
                problem="Efficiency",
                methodology=MethodologySummary(
                    approach="Standard Transformer",
                    datasets=["GLUE Benchmark"],
                    metrics=["accuracy"],
                ),
                results=ResultsSummary(
                    primary_findings=["Standard baseline"],
                    metrics={"accuracy": "84.0%"},
                ),
                limitations=[],
                future_work=[],
                extracted_sections={},
            ),
        ]

        analysis = AnalystResponse(
            query="transformer efficiency",
            themes=["Sparse Attention Architectures"],
            innovations=[],
            consensus=[],
            conflicts=[],
            gaps=[],
            practical_applications=[],
        )

        tensions = [
            ContradictionPair(
                paper_a="Alpha Method Paper",
                paper_b="Beta Baseline Paper",
                topic="Accuracy",
                claim_a="Reports accuracy 91.2%",
                claim_b="Reports accuracy 84.0%",
                severity=ContradictionSeverity.DIRECT_EMPIRICAL,
                confidence=0.91,
                root_cause="Shared benchmark divergence",
                resolution_hypothesis="Replicate under identical hyperparameter conditions.",
            )
        ]

        graph = self.graph_engine.build_graph(
            reader_outputs=reader_outputs,
            analysis=analysis,
            tensions=tensions,
        )

        self.assertGreaterEqual(len(graph.nodes), 4)
        self.assertGreaterEqual(len(graph.edges), 4)

        # Verify node types
        node_types = {n.node_type for n in graph.nodes}
        self.assertIn(GraphNodeType.PAPER, node_types)
        self.assertIn(GraphNodeType.DATASET, node_types)
        self.assertIn(GraphNodeType.METRIC, node_types)
        self.assertIn(GraphNodeType.THEME, node_types)

        # Verify contradiction edge
        contradict_edge = next(
            (e for e in graph.edges if e.relation == GraphRelation.CONTRADICTS), None
        )
        self.assertIsNotNone(contradict_edge)

        # Verify Mermaid diagram
        self.assertIn("graph LR", graph.mermaid_diagram)
        self.assertIn("Alpha Method Paper", graph.mermaid_diagram)
        self.assertIn("GLUE Benchmark", graph.mermaid_diagram)


if __name__ == "__main__":
    unittest.main()
