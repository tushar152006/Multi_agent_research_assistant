import unittest

from backend.agents.reader_agent import ReaderAgent
from backend.models.schemas import ReaderRequest


SAMPLE_PAPER_TEXT = """
Abstract
This paper studies autonomous research agents that reduce literature review time.
We focus on improving retrieval quality and structured synthesis.

Introduction
Researchers need help navigating large scientific corpora efficiently.

Methodology
Our approach combines retrieval, ranking, and summarization in a multi-agent pipeline.
Datasets: OpenAlex Benchmark, ResearchArena Corpus.
Metrics: accuracy, recall, F1-score.

Results
The system achieved accuracy 91% and recall 88% on the benchmark.
It also improved researcher task completion speed by 32%.

Limitations
The evaluation used a limited benchmark and did not cover every scientific field.

Future Work
Future work should evaluate broader domains and stronger long-context models.
"""


class ReaderAgentTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_reader_agent_extracts_structured_sections(self) -> None:
        agent = ReaderAgent()

        result = await agent.run(
            ReaderRequest(
                title="Autonomous Research Agents",
                source="arXiv",
                content=SAMPLE_PAPER_TEXT,
            )
        )

        self.assertEqual(result.title, "Autonomous Research Agents")
        self.assertIn("autonomous research agents", result.problem.lower())
        self.assertIn("multi-agent pipeline", result.methodology.approach.lower())
        self.assertIn("accuracy", result.methodology.metrics)
        self.assertEqual(result.results.metrics["accuracy"], "91%")
        self.assertTrue(result.limitations)
        self.assertTrue(result.future_work)
        self.assertIn("abstract", result.extracted_sections)


if __name__ == "__main__":
    unittest.main()
