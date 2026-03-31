from __future__ import annotations

import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.agents.analyst_agent import AnalystAgent
from backend.agents.builder_agent import BuilderAgent
from backend.agents.critic_agent import CriticAgent
from backend.agents.reader_agent import ReaderAgent
from backend.agents.research_agent import ResearchAgent
from backend.core.config import get_settings
from backend.models.schemas import (
    AnalystRequest,
    BuilderRequest,
    CriticRequest,
    ReaderRequest,
    ResearchRequest,
    ResearchResponse,
    AgentExecution,
)
from backend.storage.session_store import SessionStore

import uuid

router = APIRouter(tags=["websocket"])


async def _send(ws: WebSocket, event: str, data: dict) -> None:
    """Send a JSON-encoded event frame to the client."""
    await ws.send_text(json.dumps({"event": event, "data": data}))


@router.websocket("/ws/research")
async def research_websocket(ws: WebSocket) -> None:
    """
    WebSocket endpoint for real-time research pipeline progress.

    Expected client message (JSON):
        { "query": "...", "max_results": 5, "query_type": "deep_analysis" }

    Server sends a stream of progress events followed by a final `done` event
    containing the full ResearchResponse payload.
    """
    await ws.accept()

    try:
        raw = await ws.receive_text()
        payload = json.loads(raw)
    except (WebSocketDisconnect, json.JSONDecodeError) as exc:
        await _send(ws, "error", {"message": f"Invalid request: {exc}"})
        await ws.close()
        return

    request = ResearchRequest(
        query=payload.get("query", ""),
        max_results=int(payload.get("max_results", 5)),
        query_type=payload.get("query_type", "deep_analysis"),
    )

    settings = get_settings()
    research_agent = ResearchAgent()
    reader_agent = ReaderAgent()
    analyst_agent = AnalystAgent()
    critic_agent = CriticAgent()
    builder_agent = BuilderAgent()
    session_store = SessionStore(settings.local_storage_path)

    execution_trace: list[AgentExecution] = []

    try:
        # ── Research Agent ────────────────────────────────────────────────
        await _send(ws, "agent_start", {"agent": "research_agent", "message": "Searching for papers…"})
        papers = await research_agent.run(request)
        step = AgentExecution(
            agent_name="research_agent",
            status="completed",
            detail=f"Found {len(papers)} candidate papers.",
        )
        execution_trace.append(step)
        await _send(ws, "agent_done", {"agent": "research_agent", "detail": step.detail})

        # ── Reader Agent ──────────────────────────────────────────────────
        await _send(ws, "agent_start", {"agent": "reader_agent", "message": "Extracting structured findings…"})
        reader_outputs = []
        for paper in papers:
            reader_output = await reader_agent.run(
                ReaderRequest(
                    title=paper.title,
                    source=paper.source,
                    content=paper.abstract,
                )
            )
            reader_outputs.append(reader_output)
        step = AgentExecution(
            agent_name="reader_agent",
            status="completed",
            detail=f"Parsed {len(reader_outputs)} paper summaries.",
        )
        execution_trace.append(step)
        await _send(ws, "agent_done", {"agent": "reader_agent", "detail": step.detail})

        # ── Analyst Agent ─────────────────────────────────────────────────
        await _send(ws, "agent_start", {"agent": "analyst_agent", "message": "Synthesising insights…"})
        analysis = await analyst_agent.run(
            AnalystRequest(query=request.query, papers=reader_outputs)
        )
        step = AgentExecution(
            agent_name="analyst_agent",
            status="completed",
            detail=f"Produced {len(analysis.themes)} themes and {len(analysis.gaps)} gaps.",
        )
        execution_trace.append(step)
        await _send(ws, "agent_done", {"agent": "analyst_agent", "detail": step.detail})

        # ── Critic Agent ──────────────────────────────────────────────────
        await _send(ws, "agent_start", {"agent": "critic_agent", "message": "Critiquing analysis (Ollama)…"})
        critique = await critic_agent.run(
            CriticRequest(query=request.query, analysis=analysis)
        )
        step = AgentExecution(
            agent_name="critic_agent",
            status="completed",
            detail=f"Generated {len(critique.critiques)} critique items. Mode: {critique.review_mode}.",
        )
        execution_trace.append(step)
        await _send(ws, "agent_done", {"agent": "critic_agent", "detail": step.detail})

        # ── Builder Agent ─────────────────────────────────────────────────
        await _send(ws, "agent_start", {"agent": "builder_agent", "message": "Building implementation plan…"})
        implementation_plan = await builder_agent.run(
            BuilderRequest(query=request.query, analysis=analysis, critique=critique)
        )
        step = AgentExecution(
            agent_name="builder_agent",
            status="completed",
            detail="Implementation plan ready.",
        )
        execution_trace.append(step)
        await _send(ws, "agent_done", {"agent": "builder_agent", "detail": step.detail})

        # ── Persist & respond ─────────────────────────────────────────────
        session_id = str(uuid.uuid4())
        report = ResearchResponse(
            query=request.query,
            query_type=request.query_type,
            summary=(
                "End-to-end research workflow completed via WebSocket. "
                "Papers discovered, findings extracted, insights synthesised, "
                "critique generated, and implementation plan produced."
            ),
            papers=papers,
            reader_outputs=reader_outputs,
            analysis=analysis,
            critique=critique,
            implementation_plan=implementation_plan,
            session_id=session_id,
            execution_trace=execution_trace,
        )
        saved = await session_store.save_report(report)
        await _send(ws, "done", saved.model_dump(mode="json"))

    except WebSocketDisconnect:
        pass
    except Exception as exc:  # noqa: BLE001
        await _send(ws, "error", {"message": str(exc)})
    finally:
        try:
            await ws.close()
        except Exception:  # noqa: BLE001
            pass
