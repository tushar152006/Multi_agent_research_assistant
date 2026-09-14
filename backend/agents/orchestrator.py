from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any, Callable

from backend.agents.analyst_agent import AnalystAgent
from backend.agents.builder_agent import BuilderAgent
from backend.agents.contradiction_agent import ContradictionAgent
from backend.agents.critic_agent import CriticAgent
from backend.agents.reader_agent import ReaderAgent
from backend.agents.research_agent import ResearchAgent
from backend.core.config import get_settings
from backend.core.dag_engine import DAGEngine, DAGNode, WorkflowContext
from backend.core.evidence_graph import EvidenceGraphEngine
from backend.core.prisma_review import PrismaReviewEngine
from backend.models.schemas import (
    AgentExecution,
    AnalystRequest,
    BuilderRequest,
    CriticRequest,
    QueryType,
    ReaderRequest,
    ResearchRequest,
    ResearchResponse,
)
from backend.storage.session_store import SessionStore

logger = logging.getLogger(__name__)


class Orchestrator:
    """Coordinate agent execution using the asynchronous DAG engine."""

    def __init__(
        self,
        research_agent: ResearchAgent | None = None,
        reader_agent: ReaderAgent | None = None,
        analyst_agent: AnalystAgent | None = None,
        contradiction_agent: ContradictionAgent | None = None,
        critic_agent: CriticAgent | None = None,
        builder_agent: BuilderAgent | None = None,
        session_store: SessionStore | None = None,
        prisma_engine: PrismaReviewEngine | None = None,
        graph_engine: EvidenceGraphEngine | None = None,
        max_concurrency: int = 4,
    ) -> None:
        settings = get_settings()
        self.research_agent = research_agent or ResearchAgent()
        self.reader_agent = reader_agent or ReaderAgent()
        self.analyst_agent = analyst_agent or AnalystAgent()
        self.contradiction_agent = contradiction_agent or ContradictionAgent()
        self.critic_agent = critic_agent or CriticAgent()
        self.builder_agent = builder_agent or BuilderAgent()
        self.session_store = session_store or SessionStore(settings.local_storage_path)
        self.prisma_engine = prisma_engine or PrismaReviewEngine()
        self.graph_engine = graph_engine or EvidenceGraphEngine()
        self.max_concurrency = max(1, max_concurrency)

    async def _read_papers(
        self,
        context: WorkflowContext,
        on_event: Callable | None,
    ) -> list[Any]:
        papers = await context.get("papers", [])
        semaphore = asyncio.Semaphore(self.max_concurrency)
        total_papers = len(papers)
        completed_count = 0
        progress_lock = asyncio.Lock()

        async def read_one(paper: Any) -> Any | None:
            nonlocal completed_count
            async with semaphore:
                try:
                    result = await self.reader_agent.run(
                        ReaderRequest(
                            title=paper.title,
                            source=paper.source,
                            content=paper.abstract,
                        )
                    )
                    async with progress_lock:
                        completed_count += 1
                        current_count = completed_count

                    if on_event:
                        event = on_event(
                            "paper_progress",
                            {
                                "node": "reader_agent",
                                "title": paper.title,
                                "index": current_count,
                                "total": total_papers,
                            },
                        )
                        if asyncio.iscoroutine(event):
                            await event
                    return result
                except Exception:
                    logger.exception("Failed to read paper: %s", getattr(paper, "title", "Unknown"))
                    return None

        results = await asyncio.gather(*(read_one(paper) for paper in papers))
        return [result for result in results if result is not None]

    async def process(
        self,
        request: ResearchRequest,
        on_event: Callable | None = None,
    ) -> ResearchResponse:
        context = WorkflowContext(
            metadata={
                "query": request.query,
                "query_type": request.query_type.value if hasattr(request.query_type, "value") else str(request.query_type),
            }
        )
        engine = DAGEngine()

        async def research_action(ctx: WorkflowContext) -> Any:
            papers = await self.research_agent.run(request)
            await ctx.set("papers", papers)
            return papers

        async def reader_action(ctx: WorkflowContext) -> Any:
            reader_outputs = await self._read_papers(ctx, on_event)
            await ctx.set("reader_outputs", reader_outputs)
            return reader_outputs

        async def analyst_action(ctx: WorkflowContext) -> Any:
            reader_outputs = await ctx.get("reader_outputs", [])
            analysis = await self.analyst_agent.run(
                AnalystRequest(
                    query=request.query,
                    papers=reader_outputs,
                )
            )
            await ctx.set("analysis", analysis)
            return analysis

        async def contradiction_action(ctx: WorkflowContext) -> Any:
            reader_outputs = await ctx.get("reader_outputs", [])
            matrix = await self.contradiction_agent.run(reader_outputs)
            await ctx.set("contradiction_matrix", matrix)
            return matrix

        async def critic_action(ctx: WorkflowContext) -> Any:
            analysis = await ctx.get("analysis")
            critique = await self.critic_agent.run(
                CriticRequest(
                    query=request.query,
                    analysis=analysis,
                )
            )
            await ctx.set("critique", critique)
            return critique

        async def builder_action(ctx: WorkflowContext) -> Any:
            analysis = await ctx.get("analysis")
            critique = await ctx.get("critique")
            plan = await self.builder_agent.run(
                BuilderRequest(
                    query=request.query,
                    analysis=analysis,
                    critique=critique,
                )
            )
            await ctx.set("implementation_plan", plan)
            return plan

        engine.add_node(DAGNode("research_agent", set(), research_action, timeout=120.0))
        engine.add_node(DAGNode("reader_agent", {"research_agent"}, reader_action, timeout=300.0))
        engine.add_node(DAGNode("analyst_agent", {"reader_agent"}, analyst_action, timeout=180.0))
        engine.add_node(DAGNode("contradiction_agent", {"reader_agent"}, contradiction_action, timeout=180.0))
        engine.add_node(DAGNode("critic_agent", {"analyst_agent"}, critic_action, timeout=180.0))
        engine.add_node(DAGNode("builder_agent", {"analyst_agent", "critic_agent"}, builder_action, timeout=180.0))

        await engine.execute(context, on_event)

        papers = await context.get("papers", [])
        reader_outputs = await context.get("reader_outputs", [])
        analysis = await context.get("analysis")
        critique = await context.get("critique")
        implementation_plan = await context.get("implementation_plan")
        contradiction_matrix = await context.get("contradiction_matrix")

        session_id = str(uuid.uuid4())

        prisma_flow = self.prisma_engine.generate_flow(
            raw_papers=papers,
            screened_papers=papers,
            reader_outputs=reader_outputs,
        )
        tensions = (
            getattr(contradiction_matrix, "tensions", None)
            if contradiction_matrix
            else None
        )
        evidence_graph = self.graph_engine.build_graph(
            reader_outputs=reader_outputs,
            analysis=analysis,
            tensions=tensions,
        )

        execution_trace = [
            AgentExecution(
                agent_name=item["node"],
                status=item["status"],
                detail=f"Completed in {item.get('duration', 0):.2f}s",
            )
            for item in context.execution_trace
        ]
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
                "End-to-end research workflow completed successfully via DAG engine. "
                "The system discovered papers, extracted structured findings, "
                "synthesized insights, critiqued weak evidence, mapped cross-paper "
                "contradictions, and generated an actionable implementation plan."
            ),
            papers=papers,
            reader_outputs=reader_outputs,
            analysis=analysis,
            critique=critique,
            implementation_plan=implementation_plan,
            contradiction_matrix=contradiction_matrix,
            prisma_flow=prisma_flow,
            evidence_graph=evidence_graph,
            session_id=session_id,
            execution_trace=execution_trace,
        )
        return await self.session_store.save_report(report)

    async def process_document(
        self,
        title: str,
        content: str,
    ) -> ResearchResponse:
        execution_trace = [
            AgentExecution(
                agent_name="document_loader",
                status="completed",
                detail=f"Inbound document '{title}' accepted for analysis.",
            )
        ]

        reader_output = await self.reader_agent.run(
            ReaderRequest(title=title, source="Upload", content=content)
        )
        reader_outputs = [reader_output]
        execution_trace.append(
            AgentExecution(
                agent_name=self.reader_agent.name,
                status="completed",
                detail="Extracted structured findings from the uploaded document.",
            )
        )

        contradiction_matrix = await self.contradiction_agent.run(reader_outputs)
        execution_trace.append(
            AgentExecution(
                agent_name=self.contradiction_agent.name,
                status="completed",
                detail="Evaluated internal document tensions and benchmark consistency.",
            )
        )

        analysis = await self.analyst_agent.run(
            AnalystRequest(query=f"Analysis of {title}", papers=reader_outputs)
        )
        execution_trace.append(
            AgentExecution(
                agent_name=self.analyst_agent.name,
                status="completed",
                detail="Synthesized innovations and key themes from the document.",
            )
        )

        critique = await self.critic_agent.run(
            CriticRequest(query=title, analysis=analysis)
        )
        execution_trace.append(
            AgentExecution(
                agent_name=self.critic_agent.name,
                status="completed",
                detail="Critiqued the document's methodology and evidence.",
            )
        )

        implementation_plan = await self.builder_agent.run(
            BuilderRequest(query=title, analysis=analysis, critique=critique)
        )
        execution_trace.append(
            AgentExecution(
                agent_name=self.builder_agent.name,
                status="completed",
                detail="Generated a project roadmap based on the document's insights.",
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

        tensions = (
            getattr(contradiction_matrix, "tensions", None)
            if contradiction_matrix
            else None
        )
        evidence_graph = self.graph_engine.build_graph(
            reader_outputs=reader_outputs,
            analysis=analysis,
            tensions=tensions,
        )

        report = ResearchResponse(
            query=f"Document: {title}",
            query_type=QueryType.DEEP_ANALYSIS,
            summary=f"Deep analysis of uploaded document '{title}' completed.",
            papers=[],
            reader_outputs=reader_outputs,
            analysis=analysis,
            critique=critique,
            implementation_plan=implementation_plan,
            contradiction_matrix=contradiction_matrix,
            evidence_graph=evidence_graph,
            session_id=session_id,
            execution_trace=execution_trace,
        )
        return await self.session_store.save_report(report)

