import unittest

from backend.agents.builder_agent import BuilderAgent
from backend.models.schemas import (
    AnalystResponse,
    BuilderRequest,
    ConflictSummary,
    CriticResponse,
    CritiqueItem,
    InnovationSummary,
)


class BuilderAgentTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_builder_agent_generates_implementation_plan(self) -> None:
        agent = BuilderAgent()
        analysis = AnalystResponse(
            query="multi agent research",
            themes=["multi agent workflows"],
            innovations=[
                InnovationSummary(
                    paper_title="Paper A",
                    innovation="A multi-agent retrieval pipeline using dataset: ResearchArena Corpus",
                    impact="Improved throughput",
                )
            ],
            consensus=[
                "Multiple papers rely on the dataset or benchmark `ResearchArena Corpus`."
            ],
            conflicts=[
                ConflictSummary(
                    topic="accuracy",
                    description="Accuracy differs across papers.",
                    papers=["Paper A", "Paper B"],
                )
            ],
            gaps=["Open direction highlighted by the papers: broader domain evaluation is still needed."],
            practical_applications=["Research workflow automation"],
        )
        critique = CriticResponse(
            query="multi agent research",
            critiques=[
                CritiqueItem(
                    category="methodology",
                    issue="Conflicting evidence detected around `accuracy`.",
                    severity="medium",
                    evidence="Accuracy differs across papers.",
                    impact="Validate performance on a shared benchmark before making strong claims.",
                )
            ],
            overall_confidence=0.7,
            review_mode="heuristic",
            llm_summary=None,
        )

        result = await agent.run(
            BuilderRequest(
                query="multi agent research",
                analysis=analysis,
                critique=critique,
            )
        )

        self.assertEqual(result.query, "multi agent research")
        self.assertIn("research copilot", result.project_idea.lower())
        self.assertTrue(result.architecture.components)
        self.assertIn("ResearchArena Corpus", result.data_requirements.datasets)
        self.assertEqual(len(result.mvp_roadmap), 3)
        self.assertTrue(result.challenges)


if __name__ == "__main__":
    unittest.main()
