from __future__ import annotations

from backend.agents.base_agent import BaseAgent
from backend.core.config import get_settings
from backend.core.llm import LLMService, build_llm_service
from backend.models.schemas import (
    ArchitecturePlan,
    BuilderRequest,
    BuilderResponse,
    ChallengeMitigation,
    DataRequirements,
    RoadmapPhase,
)


class BuilderAgent(BaseAgent[BuilderRequest, BuilderResponse]):
    """Hybrid implementation planner: heuristics + optional Ollama narrative enrichment."""

    name = "builder_agent"

    def __init__(self, llm_service: LLMService | None = None) -> None:
        settings = get_settings()
        self._llm_provider = settings.llm_provider
        self.llm_service = llm_service or build_llm_service(
            provider=settings.llm_provider,
            ollama_base_url=settings.ollama_base_url,
            ollama_model=settings.ollama_model,
        )

    async def run(self, payload: BuilderRequest) -> BuilderResponse:
        project_idea = self._build_project_idea(payload)
        value_proposition = self._build_value_proposition(payload)

        # Enrich the narrative fields with Ollama when available
        if self._llm_provider == "ollama":
            llm_idea, llm_value = await self._enrich_narrative(payload)
            if llm_idea:
                project_idea = llm_idea
            if llm_value:
                value_proposition = llm_value

        return BuilderResponse(
            query=payload.query,
            project_idea=project_idea,
            value_proposition=value_proposition,
            architecture=self._build_architecture(payload, project_idea),
            data_requirements=self._build_data_requirements(payload),
            mvp_roadmap=self._build_roadmap(payload),
            challenges=self._build_challenges(payload),
        )

    async def _enrich_narrative(
        self, payload: BuilderRequest
    ) -> tuple[str | None, str | None]:
        themes = payload.analysis.themes[:3]
        gaps = payload.analysis.gaps[:2]
        critique_issues = [c.issue for c in payload.critique.critiques[:2]]
        prompt = (
            f"Research query: {payload.query}\n"
            f"Key themes: {themes}\n"
            f"Research gaps: {gaps}\n"
            f"Known critique issues: {critique_issues}\n"
            "Based on this research, provide:\n"
            "LINE 1: A one-sentence project idea for a software product that addresses this research.\n"
            "LINE 2: A one-sentence value proposition explaining who benefits and why."
        )
        try:
            raw = await self.llm_service.generate(prompt)
            lines = [l.strip() for l in raw.splitlines() if l.strip()]
            idea = lines[0] if len(lines) > 0 and len(lines[0]) > 20 else None
            value = lines[1] if len(lines) > 1 and len(lines[1]) > 20 else None
            return idea, value
        except Exception:
            return None, None

    def _build_project_idea(self, payload: BuilderRequest) -> str:
        if payload.analysis.practical_applications:
            anchor = payload.analysis.practical_applications[0]
            return (
                "Build a local-first research copilot that turns paper discovery, "
                f"reading, critique, and planning into a single workflow. "
                f"Initial application focus: {anchor}"
            )

        return (
            "Build a local-first research copilot that helps users discover, "
            "analyze, critique, and operationalize research findings."
        )

    def _build_value_proposition(self, payload: BuilderRequest) -> str:
        if payload.analysis.themes:
            return (
                "The system helps users move from scattered papers to structured "
                f"action faster by focusing on themes like {payload.analysis.themes[0]}."
            )
        return (
            "The system reduces manual literature review effort and turns research "
            "findings into practical next steps."
        )

    def _build_architecture(
        self,
        payload: BuilderRequest,
        project_idea: str,
    ) -> ArchitecturePlan:
        components = [
            "FastAPI backend for orchestration and agent workflows",
            "Next.js frontend for query input, progress views, and reports",
            "Research agent pipeline using arXiv and Semantic Scholar",
            "Reader, analyst, critic, and builder agents for structured synthesis",
            "Optional Ollama integration for local model enhancement",
            "Local storage layer for sessions, cached papers, and reports",
        ]

        data_flow = [
            "User submits a research query through the frontend",
            "Discovery services retrieve and rank candidate papers",
            "Reader extracts structured findings from paper text",
            "Analyst synthesizes themes, gaps, conflicts, and applications",
            "Critic highlights risks and weak evidence",
            "Builder converts the research state into an actionable project plan",
        ]

        if payload.critique.llm_summary:
            components.append("Local LLM critique enhancement via Ollama")

        return ArchitecturePlan(
            summary=project_idea,
            components=components,
            data_flow=data_flow,
        )

    def _build_data_requirements(self, payload: BuilderRequest) -> DataRequirements:
        datasets = list(dict.fromkeys(self._collect_datasets(payload)))
        if not datasets:
            datasets = ["arXiv metadata", "Semantic Scholar metadata", "User-provided PDFs or text"]

        return DataRequirements(
            datasets=datasets[:6],
            collection_strategy=[
                "Fetch metadata from public research APIs during discovery",
                "Cache normalized paper text and extracted summaries locally",
                "Allow users to upload or paste paper content for deeper analysis",
            ],
            privacy_considerations=[
                "Keep user research sessions stored locally by default",
                "Avoid sending private paper content to remote services unless explicitly enabled",
                "Separate optional Ollama usage from external API dependencies",
            ],
        )

    def _build_roadmap(self, payload: BuilderRequest) -> list[RoadmapPhase]:
        return [
            RoadmapPhase(
                name="Phase 1",
                duration="1-2 weeks",
                goals=[
                    "Finalize the backend research pipeline from discovery to builder output",
                    "Store session results locally for repeatable experiments",
                    "Expose clean API endpoints for multi-step research workflows",
                ],
            ),
            RoadmapPhase(
                name="Phase 2",
                duration="2-3 weeks",
                goals=[
                    "Build a frontend for query submission, paper browsing, and report views",
                    "Add local project/session management",
                    "Improve structured document ingestion for PDFs and uploaded notes",
                ],
            ),
            RoadmapPhase(
                name="Phase 3",
                duration="ongoing",
                goals=[
                    "Add optional Ollama-powered enhancement to synthesis and critique",
                    "Strengthen export, memory, and long-running workflow support",
                    "Prepare the architecture for future deployment or collaboration features",
                ],
            ),
        ]

    def _build_challenges(self, payload: BuilderRequest) -> list[ChallengeMitigation]:
        challenges: list[ChallengeMitigation] = []

        for critique in payload.critique.critiques[:3]:
            challenges.append(
                ChallengeMitigation(
                    challenge=critique.issue,
                    mitigation=critique.impact,
                )
            )

        if not challenges:
            challenges.append(
                ChallengeMitigation(
                    challenge="The roadmap may outgrow the first MVP scope.",
                    mitigation="Keep the first release local-first and validate one end-to-end workflow before expanding.",
                )
            )

        return challenges[:5]

    @staticmethod
    def _collect_datasets(payload: BuilderRequest) -> list[str]:
        datasets: list[str] = []
        for consensus in payload.analysis.consensus:
            if "`" in consensus:
                datasets.append(consensus.split("`")[1])
        for innovation in payload.analysis.innovations:
            if "dataset" in innovation.innovation.lower():
                datasets.append(innovation.innovation)
        return datasets
