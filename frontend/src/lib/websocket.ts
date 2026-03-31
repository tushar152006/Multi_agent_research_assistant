/**
 * WebSocket client for the real-time research pipeline.
 *
 * The server emits a stream of JSON frames:
 *   { event: "agent_start", data: { agent, message } }
 *   { event: "agent_done",  data: { agent, detail  } }
 *   { event: "done",        data: ResearchResponse  }
 *   { event: "error",       data: { message }       }
 */

import type { ResearchResponse } from "@/lib/types";

const WS_BASE_URL =
  process.env.NEXT_PUBLIC_WS_BASE_URL ?? "ws://127.0.0.1:8000";

export type AgentStatus = "idle" | "running" | "done" | "error";

export type AgentEvent = {
  agent: string;
  label: string;
  status: AgentStatus;
  detail?: string;
  startedAt?: number;
  finishedAt?: number;
};

export type PipelineCallbacks = {
  onAgentStart: (agent: string, message: string) => void;
  onAgentDone: (agent: string, detail: string) => void;
  onDone: (report: ResearchResponse) => void;
  onError: (message: string) => void;
};

export type ResearchInput = {
  query: string;
  maxResults: number;
  queryType: string;
};

export const AGENT_LABELS: Record<string, string> = {
  research_agent: "Research Agent",
  reader_agent: "Reader Agent",
  analyst_agent: "Analyst Agent",
  critic_agent: "Critic Agent",
  builder_agent: "Builder Agent",
};

export function runResearchWebSocket(
  input: ResearchInput,
  callbacks: PipelineCallbacks,
): () => void {
  const ws = new WebSocket(`${WS_BASE_URL}/ws/research`);

  ws.onopen = () => {
    ws.send(
      JSON.stringify({
        query: input.query,
        max_results: input.maxResults,
        query_type: input.queryType,
      }),
    );
  };

  ws.onmessage = (event) => {
    try {
      const frame = JSON.parse(event.data as string) as {
        event: string;
        data: Record<string, unknown>;
      };

      if (frame.event === "agent_start") {
        callbacks.onAgentStart(
          frame.data.agent as string,
          frame.data.message as string,
        );
      } else if (frame.event === "agent_done") {
        callbacks.onAgentDone(
          frame.data.agent as string,
          frame.data.detail as string,
        );
      } else if (frame.event === "done") {
        callbacks.onDone(frame.data as unknown as ResearchResponse);
      } else if (frame.event === "error") {
        callbacks.onError(frame.data.message as string);
      }
    } catch {
      callbacks.onError("Failed to parse server message.");
    }
  };

  ws.onerror = () => {
    callbacks.onError(
      "WebSocket connection failed. Is the backend running on port 8000?",
    );
  };

  ws.onclose = () => {
    /* connection closed — nothing to do */
  };

  // Return a cleanup function
  return () => {
    if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
      ws.close();
    }
  };
}
