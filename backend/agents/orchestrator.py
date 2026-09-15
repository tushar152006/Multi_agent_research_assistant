from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any, Callable

from backend.agents.analyst_agent import AnalystAgent
from backend.agents.builder_agent import BuilderAgent
from backend.agents.citation_auditor import CitationAuditor
from backend.agents.contradiction_agent import ContradictionAgent
from backend.agents.critic_agent import CriticAgent
from backend.agents.reader_agent import ReaderAgent
from backend.agents.research_agent import ResearchAgent
from backend.core.config import get_settings
from backend.core.dag_engine import DAGEngine, DAGNode, WorkflowContext
from backend.core.evidence_graph import EvidenceGraphEngine
from backend.core.prisma_review import PrismaReviewEngine
from backend.core.research_sufficiency import ResearchSufficiencyJudge, SufficiencyVerdict
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
        citation_auditor: CitationAuditor | None = None,
        session_store: SessionStore | None = None,
        prisma_engine: PrismaReviewEngine | None = None,
        graph_engine: EvidenceGraphEngine | None = None,
        sufficiency_judge: ResearchSufficiencyJudge | None = None,
        max_concurrency: int = 4,
    ) -> None:
        settings = get_settings()
        self.research_agent = research_agent or ResearchAgent()
        self.reader_agent = reader_agent or ReaderAgent()
        self.analyst_agent = analyst_agent or AnalystAgent()
        self.contradiction_agent = contradiction_agent or ContradictionAgent()
        self.critic_agent = critic_agent or CriticAgent()
        self.builder_agent = builder_agent or BuilderAgent()
        self.citation_auditor = citation_auditor or CitationAuditor()
        self.session_store = session_store or SessionStore(settings.local_storage_path)
        self.prisma_engine = prisma_engine or PrismaReviewEngine()
        self.graph_engine = graph_engine or EvidenceGraphEngine()
        self.sufficiency_judge = sufficiency_judge or ResearchSufficiencyJudge()
        self.max_concurrency = max(1, max_concurrency)

    @staticmethod
    def _extract_findings(analysis: Any) -> list[dict[str, str]]:
        findings: list[dict[str, str]] = []
        if not analysis:
            return findings
        for theme in getattr(analysis, "themes", []):
            findings.append({"claim_text": theme, "category": "theme"})
        for inn in getattr(analysis, "innovations", []):
            findings.append({"claim_text": f"{inn.paper_title}: {inn.innovation}", "category": "innovation"})
        for con in getattr(analysis, "consensus", []):
            findings.append({"claim_text": con, "category": "consensus"})
        for app in getattr(analysis, "practical_applications", []):
            findings.append({"claim_text": app, "category": "application"})
        return findings

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
                    content = paper.abstract
                    if getattr(paper, "source", "") == "arXiv" and hasattr(self.research_agent, "arxiv_service"):
                        try:
                            pdf_text = await self.research_agent.arxiv_service.fetch_pdf_text(
                                getattr(paper, "external_id", "")
                            )
                            if pdf_text and len(pdf_text) > len(content):
                                content = pdf_text
                                setattr(paper, "is_full_text", True)
                        except Exception:
                            pass
                    elif getattr(paper, "pdf_url", None) and hasattr(self.research_agent, "semantic_scholar_service"):
                        try:
                            pdf_text = await self.research_agent.semantic_scholar_service.fetch_pdf_text(
                                paper.pdf_url
                            )
                            if pdf_text and len(pdf_text) > len(content):
                                content = pdf_text
                                setattr(paper, "is_full_text", True)
                        except Exception:
                            pass

                    result = await self.reader_agent.run(
                        ReaderRequest(
                            title=paper.title,
                            source=paper.source,
                            content=content,
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

        async def citation_action(ctx: WorkflowContext) -> Any:
            reader_outputs = await ctx.get("reader_outputs", [])
            analysis = await ctx.get("analysis")
            findings: list[dict[str, str]] = []
            if analysis:
                for theme in getattr(analysis, "themes", []):
                    findings.append({"claim_text": theme, "category": "theme"})
                for inn in getattr(analysis, "innovations", []):
                    findings.append({"claim_text": f"{inn.paper_title}: {inn.innovation}", "category": "innovation"})
                for con in getattr(analysis, "consensus", []):
                    findings.append({"claim_text": con, "category": "consensus"})
                for app in getattr(analysis, "practical_applications", []):
                    findings.append({"claim_text": app, "category": "application"})

            audit_result = self.citation_auditor.audit(reader_outputs, findings)
            await ctx.set("grounding_audit", audit_result)
            if analysis:
                qualified = self.citation_auditor.qualify_analysis(analysis, audit_result)
                await ctx.set("analysis", qualified)
            return audit_result

        async def critic_action(ctx: WorkflowContext) -> Any:
            analysis = await ctx.get("analysis")
            grounding_audit = await ctx.get("grounding_audit")
            critique = await self.critic_agent.run(
                CriticRequest(
                    query=request.query,
                    analysis=analysis,
                    grounding_audit=grounding_audit,
                )
            )
            await ctx.set("critique", critique)
            return critique

        engine.add_node(DAGNode("research_agent", set(), research_action, timeout=120.0))
        engine.add_node(DAGNode("reader_agent", {"research_agent"}, reader_action, timeout=300.0))
        engine.add_node(DAGNode("analyst_agent", {"reader_agent"}, analyst_action, timeout=180.0))
        engine.add_node(DAGNode("contradiction_agent", {"reader_agent"}, contradiction_action, timeout=180.0))
        engine.add_node(DAGNode("citation_auditor", {"analyst_agent"}, citation_action, timeout=120.0))
        engine.add_node(DAGNode("critic_agent", {"analyst_agent", "citation_auditor"}, critic_action, timeout=180.0))

        await engine.execute(context, on_event)

        papers = await context.get("papers", [])
        reader_outputs = await context.get("reader_outputs", [])
        analysis = await context.get("analysis")
        critique = await context.get("critique")
        contradiction_matrix = await context.get("contradiction_matrix")
        grounding_audit = await context.get("grounding_audit")

        # Bounded Adaptive Research Loop driven by ResearchSufficiencyJudge
        iteration = 1
        all_papers = list(papers)
        all_reader_outputs = list(reader_outputs)

        while iteration < self.sufficiency_judge.max_iterations:
            verdict = self.sufficiency_judge.evaluate(
                query=request.query,
                iteration=iteration,
                papers=all_papers,
                analysis=analysis,
                critique=critique,
                grounding_audit=grounding_audit,
                contradiction_matrix=contradiction_matrix,
            )
            if on_event:
                event = on_event("sufficiency_verdict", verdict.model_dump())
                if asyncio.iscoroutine(event):
                    await event

            if verdict.is_sufficient or not verdict.recommended_queries:
                break

            next_query = verdict.recommended_queries[0]
            logger.info(
                "Adaptive loop iteration %d: targeting query '%s'",
                iteration + 1,
                next_query,
            )
            if on_event:
                event = on_event(
                    "adaptive_iteration",
                    {
                        "iteration": iteration + 1,
                        "target_query": next_query,
                        "missing_aspects": verdict.missing_aspects,
                    },
                )
                if asyncio.iscoroutine(event):
                    await event

            new_papers = await self.research_agent.run(
                ResearchRequest(
                    query=next_query,
                    max_results=2,
                    query_type=request.query_type,
                )
            )
            existing_ids = {p.external_id for p in all_papers}
            distinct_new = [p for p in new_papers if p.external_id not in existing_ids]

            if not distinct_new:
                break

            await context.set("papers", distinct_new)
            new_reader_outputs = await self._read_papers(context, on_event)
            all_papers.extend(distinct_new)
            all_reader_outputs.extend(new_reader_outputs)
            await context.set("papers", all_papers)
            await context.set("reader_outputs", all_reader_outputs)

            analysis = await self.analyst_agent.run(
                AnalystRequest(query=request.query, papers=all_reader_outputs)
            )
            contradiction_matrix = await self.contradiction_agent.run(all_reader_outputs)
            findings = self._extract_findings(analysis)
            grounding_audit = self.citation_auditor.audit(all_reader_outputs, findings)
            analysis = self.citation_auditor.qualify_analysis(analysis, grounding_audit)
            critique = await self.critic_agent.run(
                CriticRequest(
                    query=request.query,
                    analysis=analysis,
                    grounding_audit=grounding_audit,
                )
            )
            iteration += 1

        # Synthesize final builder implementation plan based on the complete evidence corpus
        implementation_plan = await self.builder_agent.run(
            BuilderRequest(
                query=request.query,
                analysis=analysis,
                critique=critique,
            )
        )

        papers = all_papers
        reader_outputs = all_reader_outputs
        session_id = str(uuid.uuid4())

        # Dynamic PRISMA screening based on relevance cutoff threshold
        cutoff = self.prisma_engine.relevance_cutoff
        screened_papers = [p for p in papers if p.relevance_score >= cutoff]
        if not screened_papers and papers:
            screened_papers = papers[:1]

        prisma_flow = self.prisma_engine.generate_flow(
            raw_papers=papers,
            screened_papers=screened_papers,
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
        if iteration > 1:
            execution_trace.append(
                AgentExecution(
                    agent_name="sufficiency_judge",
                    status="completed",
                    detail=f"Executed {iteration} bounded adaptive research loops to expand evidence coverage.",
                )
            )
        execution_trace.append(
            AgentExecution(
                agent_name="builder_agent",
                status="completed",
                detail="Synthesized actionable project roadmap based on grounded evidence.",
            )
        )
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
                "The system discovered papers, extracted structured findings with SHA-256 chunk grounding, "
                "synthesized insights, audited citations against source evidence, critiqued weak evidence, "
                "mapped cross-paper contradictions, and generated an actionable implementation plan."
            ),
            papers=papers,
            reader_outputs=reader_outputs,
            analysis=analysis,
            critique=critique,
            implementation_plan=implementation_plan,
            contradiction_matrix=contradiction_matrix,
            prisma_flow=prisma_flow,
            evidence_graph=evidence_graph,
            grounding_audit=grounding_audit,
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

        findings: list[dict[str, str]] = []
        if analysis:
            for theme in getattr(analysis, "themes", []):
                findings.append({"claim_text": theme, "category": "theme"})
            for inn in getattr(analysis, "innovations", []):
                findings.append({"claim_text": f"{inn.paper_title}: {inn.innovation}", "category": "innovation"})
            for con in getattr(analysis, "consensus", []):
                findings.append({"claim_text": con, "category": "consensus"})
            for app in getattr(analysis, "practical_applications", []):
                findings.append({"claim_text": app, "category": "application"})

        grounding_audit = self.citation_auditor.audit(reader_outputs, findings)
        if analysis:
            analysis = self.citation_auditor.qualify_analysis(analysis, grounding_audit)
        execution_trace.append(
            AgentExecution(
                agent_name="citation_auditor",
                status="completed",
                detail=f"Audited {grounding_audit.total_claims} claims (Precision: {int(grounding_audit.grounding_precision * 100)}%).",
            )
        )

        critique = await self.critic_agent.run(
            CriticRequest(query=title, analysis=analysis, grounding_audit=grounding_audit)
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
            grounding_audit=grounding_audit,
            session_id=session_id,
            execution_trace=execution_trace,
        )
        return await self.session_store.save_report(report)

