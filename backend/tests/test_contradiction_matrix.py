import unittest

from backend.agents.contradiction_agent import ContradictionAgent
from backend.core.contradiction_matrix import (
    ContradictionMatrixEngine,
    ContradictionSeverity,
)
from backend.models.schemas import (
    MethodologySummary,
    ReaderResponse,
    ResultsSummary,
)


class ContradictionMatrixTestCase(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.engine = ContradictionMatrixEngine(empirical_metric_threshold=3.0)

    def test_direct_empirical_discrepancy_on_shared_dataset(self) -> None:
        paper_1 = ReaderResponse(
            title="Transformer Agents for Science",
            problem="Literature reviews are slow.",
            methodology=MethodologySummary(
                approach="Multi-agent graph retrieval pipeline.",
                datasets=["ResearchArena Benchmark"],
                metrics=["accuracy", "recall"],
            ),
            results=ResultsSummary(
                primary_findings=["Our pipeline outperforms standard retrieval."],
                metrics={"accuracy": "92.5%", "recall": "88.0%"},
            ),
            limitations=["Limited to English papers."],
            future_work=[],
            extracted_sections={},
        )
        paper_2 = ReaderResponse(
            title="Statistical Baselines for Science",
            problem="Complex agent pipelines may not be needed.",
            methodology=MethodologySummary(
                approach="Direct BM25 search with reranker.",
                datasets=["ResearchArena Benchmark"],
                metrics=["accuracy", "precision"],
            ),
            results=ResultsSummary(
                primary_findings=["Statistical methods match complex agents."],
                metrics={"accuracy": "76.0%", "precision": "81.0%"},
            ),
            limitations=["Does not generate natural language answers."],
            future_work=[],
            extracted_sections={},
        )

        matrix = self.engine.build_matrix([paper_1, paper_2])

        self.assertEqual(matrix.total_pairs_checked, 1)
        self.assertGreaterEqual(len(matrix.tensions), 1)

        empirical_tension = next(
            (t for t in matrix.tensions if t.severity == ContradictionSeverity.DIRECT_EMPIRICAL),
            None,
        )
        self.assertIsNotNone(empirical_tension)
        self.assertIn("Accuracy", empirical_tension.topic)
        self.assertIn("ResearchArena Benchmark", empirical_tension.root_cause)
        self.assertGreaterEqual(empirical_tension.confidence, 0.9)
        self.assertEqual(matrix.matrix_density, 1.0)
        self.assertIsNotNone(matrix.most_controversial_paper)

    def test_dataset_divergence_root_cause(self) -> None:
        paper_a = ReaderResponse(
            title="Alpha Model",
            problem="Classification latency.",
            methodology=MethodologySummary(
                approach="Quantized transformer.",
                datasets=["ArxivQA"],
                metrics=["accuracy"],
            ),
            results=ResultsSummary(
                primary_findings=["Reaches high accuracy on ArxivQA."],
                metrics={"accuracy": "95%"},
            ),
            limitations=[],
            future_work=[],
            extracted_sections={},
        )
        paper_b = ReaderResponse(
            title="Beta Model",
            problem="Classification latency.",
            methodology=MethodologySummary(
                approach="Quantized transformer.",
                datasets=["PubMedQA"],
                metrics=["accuracy"],
            ),
            results=ResultsSummary(
                primary_findings=["Scores moderately on PubMedQA."],
                metrics={"accuracy": "68%"},
            ),
            limitations=[],
            future_work=[],
            extracted_sections={},
        )

        matrix = self.engine.build_matrix([paper_a, paper_b])
        empirical_tension = next(
            (t for t in matrix.tensions if t.severity == ContradictionSeverity.DIRECT_EMPIRICAL),
            None,
        )
        self.assertIsNotNone(empirical_tension)
        self.assertIn("Dataset divergence", empirical_tension.root_cause)

    def test_qualitative_claim_polarity_conflict(self) -> None:
        paper_a = ReaderResponse(
            title="Deep Agentic Search",
            problem="Information overload.",
            methodology=MethodologySummary(
                approach="Recursive multi-agent search.",
                datasets=["WebQA"],
                metrics=[],
            ),
            results=ResultsSummary(
                primary_findings=[
                    "Recursive agent search outperforms traditional indexing significantly."
                ],
                metrics={},
            ),
            limitations=[],
            future_work=[],
            extracted_sections={},
        )
        paper_b = ReaderResponse(
            title="Flat Indexing Efficacy",
            problem="Search latency.",
            methodology=MethodologySummary(
                approach="Flat inverted index.",
                datasets=["WebQA"],
                metrics=[],
            ),
            results=ResultsSummary(
                primary_findings=[
                    "Recursive agent search underperforms traditional indexing on latency."
                ],
                metrics={},
            ),
            limitations=[],
            future_work=[],
            extracted_sections={},
        )

        matrix = self.engine.build_matrix([paper_a, paper_b])
        qualitative = next(
            (t for t in matrix.tensions if t.severity == ContradictionSeverity.QUALITATIVE_CONFLICT),
            None,
        )
        self.assertIsNotNone(qualitative)
        self.assertEqual(qualitative.severity, ContradictionSeverity.QUALITATIVE_CONFLICT)

    def test_limitation_collision_detection(self) -> None:
        paper_a = ReaderResponse(
            title="Chain of Thought Review",
            problem="Reasoning depth.",
            methodology=MethodologySummary(
                approach="Autoregressive prompting chain.",
                datasets=[],
                metrics=[],
            ),
            results=ResultsSummary(primary_findings=["Chain reasoning is viable."], metrics={}),
            limitations=[
                "Autoregressive prompting chain suffers severe hallucination accumulation over long contexts."
            ],
            future_work=[],
            extracted_sections={},
        )
        paper_b = ReaderResponse(
            title="Long Horizon Reasoner",
            problem="Complex literature synthesis.",
            methodology=MethodologySummary(
                approach="Autoregressive prompting chain across fifty papers.",
                datasets=[],
                metrics=[],
            ),
            results=ResultsSummary(primary_findings=["Long contexts work smoothly."], metrics={}),
            limitations=[],
            future_work=[],
            extracted_sections={},
        )

        matrix = self.engine.build_matrix([paper_a, paper_b])
        collision = next(
            (t for t in matrix.tensions if t.severity == ContradictionSeverity.LIMITATION_COLLISION),
            None,
        )
        self.assertIsNotNone(collision)
        self.assertEqual(collision.severity, ContradictionSeverity.LIMITATION_COLLISION)

    def test_empty_or_single_paper_handling(self) -> None:
        matrix_empty = self.engine.build_matrix([])
        self.assertEqual(matrix_empty.total_pairs_checked, 0)
        self.assertEqual(len(matrix_empty.tensions), 0)
        self.assertIsNone(matrix_empty.most_controversial_paper)

        paper = ReaderResponse(
            title="Solo Paper",
            problem="None",
            methodology=MethodologySummary(approach="Single test", datasets=[], metrics=[]),
            results=ResultsSummary(primary_findings=[], metrics={}),
            limitations=[],
            future_work=[],
            extracted_sections={},
        )
        matrix_single = self.engine.build_matrix([paper])
        self.assertEqual(matrix_single.total_pairs_checked, 0)
        self.assertEqual(len(matrix_single.tensions), 0)

    async def test_contradiction_agent_async_execution(self) -> None:
        agent = ContradictionAgent(engine=self.engine, llm_provider="heuristic")
        paper_1 = ReaderResponse(
            title="Model 1",
            problem="Testing",
            methodology=MethodologySummary(approach="Pipeline", datasets=["Bench"], metrics=["f1"]),
            results=ResultsSummary(primary_findings=[], metrics={"f1": "90"}),
            limitations=[],
            future_work=[],
            extracted_sections={},
        )
        paper_2 = ReaderResponse(
            title="Model 2",
            problem="Testing",
            methodology=MethodologySummary(approach="Pipeline", datasets=["Bench"], metrics=["f1"]),
            results=ResultsSummary(primary_findings=[], metrics={"f1": "70"}),
            limitations=[],
            future_work=[],
            extracted_sections={},
        )

        result = await agent.run([paper_1, paper_2])
        self.assertEqual(len(result.tensions), 1)
        self.assertEqual(result.papers_analyzed, ["Model 1", "Model 2"])
        self.assertTrue(len(result.key_open_debates) > 0)


if __name__ == "__main__":
    unittest.main()
