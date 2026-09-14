from __future__ import annotations

import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.agents.orchestrator import Orchestrator
from backend.models.schemas import ResearchRequest

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


async def _send(ws: WebSocket, event: str, data: dict) -> None:
    """Send a JSON-encoded event frame to the client."""
    await ws.send_text(json.dumps({"event": event, "data": data}))


@router.websocket("/ws/research")
async def research_websocket(ws: WebSocket) -> None:
    """
    WebSocket endpoint for real-time research pipeline progress powered by DAGEngine.
    """
    await ws.accept()

    try:
        raw = await ws.receive_text()
        payload = json.loads(raw)
    except (WebSocketDisconnect, json.JSONDecodeError) as exc:
        await _send(ws, "error", {"message": f"Invalid request: {exc}"})
        await ws.close()
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

    orchestrator = Orchestrator()

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
