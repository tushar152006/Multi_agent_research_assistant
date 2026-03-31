import unittest

from backend.agents.critic_agent import CriticAgent
from backend.models.schemas import (
    AnalystResponse,
    ConflictSummary,
    CriticRequest,
    InnovationSummary,
)


class StubLLMService:
    async def generate(self, prompt: str) -> str:
        return "Local model summary."


class CriticAgentTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_critic_agent_generates_heuristic_critiques(self) -> None:
        agent = CriticAgent()
        analysis = AnalystResponse(
            query="multi agent research",
            themes=["multi agent pipelines"],
            innovations=[
                InnovationSummary(
                    paper_title="Paper A",
                    innovation="A retrieval pipeline",
                    impact="Improved throughput",
                )
            ],
            consensus=["Multiple papers use accuracy."],
            conflicts=[
                ConflictSummary(
                    topic="accuracy",
                    description="Accuracy differs substantially between papers.",
                    papers=["Paper A", "Paper B"],
                )
            ],
            gaps=["Open direction highlighted by the papers: broader domain evaluation is still needed."],
            practical_applications=["Research workflow automation"],
        )

        result = await agent.run(
            CriticRequest(query="multi agent research", analysis=analysis)
        )

        self.assertEqual(result.review_mode, "heuristic")
        self.assertTrue(result.critiques)
        self.assertLess(result.overall_confidence, 0.9)
        self.assertIsNone(result.llm_summary)

    async def test_critic_agent_can_return_llm_summary(self) -> None:
        agent = CriticAgent(llm_service=StubLLMService())
        agent.review_mode = "ollama"
        analysis = AnalystResponse(
            query="multi agent research",
            themes=["structured research workflows"],
            innovations=[
                InnovationSummary(
                    paper_title="Paper A",
                    innovation="A planning pipeline",
                    impact="Improved reliability",
                ),
                InnovationSummary(
                    paper_title="Paper B",
                    innovation="A synthesis pipeline",
                    impact="Improved throughput",
                ),
            ],
            consensus=["The papers align on structured automation."],
            conflicts=[],
            gaps=[],
            practical_applications=["Research productivity tooling"],
        )

        result = await agent.run(
            CriticRequest(query="multi agent research", analysis=analysis)
        )

        self.assertEqual(result.review_mode, "ollama")
        self.assertEqual(result.llm_summary, "Local model summary.")


if __name__ == "__main__":
    unittest.main()
