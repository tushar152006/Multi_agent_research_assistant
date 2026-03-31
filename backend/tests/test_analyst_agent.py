import unittest

from backend.agents.analyst_agent import AnalystAgent
from backend.models.schemas import (
    AnalystRequest,
    MethodologySummary,
    ReaderResponse,
    ResultsSummary,
)


class AnalystAgentTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_analyst_agent_synthesizes_reader_outputs(self) -> None:
        agent = AnalystAgent()
        papers = [
            ReaderResponse(
                title="Autonomous Research Agents",
                problem="Autonomous research agents reduce literature review effort.",
                methodology=MethodologySummary(
                    approach="A multi-agent retrieval and summarization pipeline.",
                    datasets=["ResearchArena Corpus"],
                    metrics=["accuracy", "recall"],
                ),
                results=ResultsSummary(
                    primary_findings=[
                        "The system improves literature review throughput for researchers."
                    ],
                    metrics={"accuracy": "91%", "recall": "88%"},
                ),
                limitations=["The benchmark is limited to computer science papers."],
                future_work=["Broader domain evaluation is still needed."],
                extracted_sections={"abstract": "sample"},
            ),
            ReaderResponse(
                title="Collaborative Scientific Discovery",
                problem="Scientific discovery workflows benefit from coordinated agents.",
                methodology=MethodologySummary(
                    approach="A multi-agent planning pipeline with structured retrieval.",
                    datasets=["ResearchArena Corpus"],
                    metrics=["accuracy", "precision"],
                ),
                results=ResultsSummary(
                    primary_findings=[
                        "The approach improves planning quality and task completion consistency."
                    ],
                    metrics={"accuracy": "77%", "precision": "80%"},
                ),
                limitations=["The benchmark is limited to computer science papers."],
                future_work=["Broader domain evaluation is still needed."],
                extracted_sections={"abstract": "sample"},
            ),
        ]

        result = await agent.run(
            AnalystRequest(query="multi agent research", papers=papers)
        )

        self.assertEqual(result.query, "multi agent research")
        self.assertTrue(result.themes)
        self.assertEqual(len(result.innovations), 2)
        self.assertTrue(result.consensus)
        self.assertTrue(result.conflicts)
        self.assertTrue(result.gaps)
        self.assertTrue(result.practical_applications)
        self.assertEqual(result.conflicts[0].topic, "accuracy")


if __name__ == "__main__":
    unittest.main()
