from __future__ import annotations

import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

import re
from backend.agents.orchestrator import Orchestrator
from backend.core.config import get_settings
from backend.models.schemas import ResearchRequest
from backend.storage.session_store import SessionStore

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


async def _send(ws: WebSocket, event: str, data: dict) -> None:
    """Send a JSON-encoded event frame to the client safely."""
    try:
        from starlette.websockets import WebSocketState
        if ws.client_state == WebSocketState.CONNECTED:
            await ws.send_text(json.dumps({"event": event, "data": data}))
    except Exception:
        pass


@router.websocket("/ws/research")
async def research_websocket(ws: WebSocket) -> None:
    """
    WebSocket endpoint for real-time research pipeline progress powered by DAGEngine.
    Enforces Origin header validation against CSWSH and isolates user sessions.
    """
    settings = get_settings()
    origin = ws.headers.get("origin")

    # Enforce Origin header check to prevent Cross-Site WebSocket Hijacking (CSWSH)
    if origin:
        allowed = set(settings.cors_origins)
        if "*" not in allowed and origin not in allowed:
            await ws.close(code=1008, reason="Cross-site connection forbidden.")
            return

    await ws.accept()

    try:
        raw = await ws.receive_text()
        payload = json.loads(raw)
    except (WebSocketDisconnect, json.JSONDecodeError) as exc:
        await _send(ws, "error", {"message": f"Invalid request: {exc}"})
        await ws.close()
        return

    # Extract user identity from query param, header, or payload
    user_id = ws.query_params.get("user_id") or ws.headers.get("x-user-id")
    if not user_id and isinstance(payload, dict):
        user_id = payload.get("user_id")

    if not user_id:
        if settings.auth_required:
            await _send(ws, "error", {"message": "Authentication required."})
            await ws.close(code=1008)
            return
        user_id = "default"

    if not re.match(r"^[a-zA-Z0-9_-]+$", str(user_id)):
        await _send(ws, "error", {"message": "Invalid user ID."})
        await ws.close(code=1008)
        return

    try:
        request = ResearchRequest(
            query=payload.get("query", ""),
            max_results=int(payload.get("max_results", 5)),
            query_type=payload.get("query_type", "deep_analysis"),
        )
    except Exception as exc:
        await _send(ws, "error", {"message": f"Validation error: {exc}"})
        await ws.close()
        return

    session_store = SessionStore(settings.local_storage_path, user_id=str(user_id))
    orchestrator = Orchestrator(session_store=session_store)

    async def on_event(event_name: str, data: dict) -> None:
        try:
            if event_name == "node_start":
                node = data.get("node", "")
                label = node.replace("_", " ").title()
                await _send(
                    ws,
                    "agent_start",
                    {"agent": node, "message": f"Executing {label}…"},
                )
            elif event_name == "node_done":
                node = data.get("node", "")
                duration = data.get("duration", 0)
                await _send(
                    ws,
                    "agent_done",
                    {"agent": node, "detail": f"Completed in {duration:.2f}s"},
                )
            elif event_name == "paper_progress":
                await _send(
                    ws,
                    "paper_progress",
                    {
                        "index": data.get("index", 1),
                        "total": data.get("total", 1),
                        "title": data.get("title", ""),
                    },
                )
            elif event_name == "adaptive_iteration":
                it = data.get("iteration", 2)
                tq = data.get("target_query", "")
                await _send(
                    ws,
                    "agent_start",
                    {
                        "agent": "research_agent",
                        "message": f"Adaptive Loop #{it}: Expanding corpus with '{tq}'…",
                    },
                )
        except Exception:
            logger.debug("Failed to stream event over websocket.", exc_info=True)

    try:
        report = await orchestrator.process(request, on_event=on_event)
        await _send(ws, "done", report.model_dump(mode="json"))
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.exception("Error during WebSocket research run.")
        try:
            await _send(ws, "error", {"message": str(exc)})
        except Exception:
            pass
    finally:
        try:
            await ws.close()
        except Exception:
            pass
