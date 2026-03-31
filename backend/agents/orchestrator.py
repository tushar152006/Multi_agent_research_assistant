import uuid

from backend.agents.analyst_agent import AnalystAgent
from backend.agents.builder_agent import BuilderAgent
from backend.agents.critic_agent import CriticAgent
from backend.agents.reader_agent import ReaderAgent
from backend.agents.research_agent import ResearchAgent
from backend.core.config import get_settings
from backend.models.schemas import (
    AgentExecution,
    AnalystRequest,
    BuilderRequest,
    CriticRequest,
    ReaderRequest,
    ResearchRequest,
    ResearchResponse,
)
from backend.storage.session_store import SessionStore


class Orchestrator:
    """Coordinate agent execution for a research request."""

    def __init__(
        self,
        research_agent: ResearchAgent | None = None,
        reader_agent: ReaderAgent | None = None,
        analyst_agent: AnalystAgent | None = None,
        critic_agent: CriticAgent | None = None,
        builder_agent: BuilderAgent | None = None,
        session_store: SessionStore | None = None,
    ) -> None:
        settings = get_settings()
        self.research_agent = research_agent or ResearchAgent()
        self.reader_agent = reader_agent or ReaderAgent()
        self.analyst_agent = analyst_agent or AnalystAgent()
        self.critic_agent = critic_agent or CriticAgent()
        self.builder_agent = builder_agent or BuilderAgent()
        self.session_store = session_store or SessionStore(settings.local_storage_path)

    async def process(self, request: ResearchRequest) -> ResearchResponse:
        papers = await self.research_agent.run(request)
        execution_trace = [
            AgentExecution(
                agent_name=self.research_agent.name,
                status="completed",
                detail=f"Generated {len(papers)} candidate papers for the query.",
            )
        ]

        reader_outputs = []
        for paper in papers:
            reader_output = await self.reader_agent.run(
                ReaderRequest(
                    title=paper.title,
                    source=paper.source,
                    content=paper.abstract,
                )
            )
            reader_outputs.append(reader_output)

        execution_trace.append(
            AgentExecution(
                agent_name=self.reader_agent.name,
                status="completed",
                detail=f"Parsed {len(reader_outputs)} paper summaries into structured outputs.",
            )
        )

        analysis = await self.analyst_agent.run(
            AnalystRequest(
                query=request.query,
                papers=reader_outputs,
            )
        )
        execution_trace.append(
            AgentExecution(
                agent_name=self.analyst_agent.name,
                status="completed",
                detail=(
                    f"Produced {len(analysis.themes)} themes and "
                    f"{len(analysis.gaps)} research gaps."
                ),
            )
        )

        critique = await self.critic_agent.run(
            CriticRequest(
                query=request.query,
                analysis=analysis,
            )
        )
        execution_trace.append(
            AgentExecution(
                agent_name=self.critic_agent.name,
                status="completed",
                detail=f"Generated {len(critique.critiques)} critique items.",
            )
        )

        implementation_plan = await self.builder_agent.run(
            BuilderRequest(
                query=request.query,
                analysis=analysis,
                critique=critique,
            )
        )
        execution_trace.append(
            AgentExecution(
                agent_name=self.builder_agent.name,
                status="completed",
                detail="Built an implementation plan from the synthesized research state.",
            )
        )

        session_id = str(uuid.uuid4())
        execution_trace.append(
            AgentExecution(
                agent_name="session_store",
                status="completed",
                detail=f"Saved research session as `{session_id}`.",
            )
        )

        report = ResearchResponse(
            query=request.query,
            query_type=request.query_type,
            summary=(
                "End-to-end research workflow completed successfully. "
                "The system discovered papers, extracted structured findings, "
                "synthesized insights, critiqued weak evidence, and generated "
                "an actionable implementation plan."
            ),
            papers=papers,
            reader_outputs=reader_outputs,
            analysis=analysis,
            critique=critique,
            implementation_plan=implementation_plan,
            session_id=session_id,
            execution_trace=execution_trace,
        )
        return await self.session_store.save_report(report)
