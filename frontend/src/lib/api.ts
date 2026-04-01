import {
  type QueryType,
  type ResearchResponse,
  type SessionListResponse,
  type DeleteResponse,
} from "@/lib/types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";

type RunResearchInput = {
  query: string;
  maxResults: number;
  queryType: QueryType;
};

export async function runResearch(
  input: RunResearchInput,
): Promise<ResearchResponse> {
  const response = await fetch(`${API_BASE_URL}/research`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      query: input.query,
      max_results: input.maxResults,
      query_type: input.queryType,
    }),
  });

  if (!response.ok) {
    throw new Error("Failed to run research workflow.");
  }

  return (await response.json()) as ResearchResponse;
}

export async function analyzeDocument(
  title: string,
  content: string,
): Promise<ResearchResponse> {
  const response = await fetch(`${API_BASE_URL}/research/analyze-doc`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      title,
      content,
    }),
  });

  if (!response.ok) {
    throw new Error("Failed to analyze the document.");
  }

  return (await response.json()) as ResearchResponse;
}

export async function listSessions(): Promise<SessionListResponse> {
  const response = await fetch(`${API_BASE_URL}/research`, {
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error("Failed to fetch saved sessions.");
  }

  return (await response.json()) as SessionListResponse;
}

export async function getSession(sessionId: string): Promise<ResearchResponse> {
  const response = await fetch(`${API_BASE_URL}/research/${sessionId}`, {
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error("Failed to fetch the saved research session.");
  }

  return (await response.json()) as ResearchResponse;
}

export async function deleteSession(sessionId: string): Promise<DeleteResponse> {
  const response = await fetch(`${API_BASE_URL}/research/${sessionId}`, {
    method: "DELETE",
  });

  if (!response.ok) {
    throw new Error("Failed to delete the session.");
  }

  return (await response.json()) as DeleteResponse;
}

/**
 * Triggers a browser file download for a session's full JSON report.
 * Uses a short-lived blob URL to avoid navigating away from the app.
 */
export async function exportSession(sessionId: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/research/export/${sessionId}`, {
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error("Failed to export the session.");
  }

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `research-${sessionId.slice(0, 8)}.json`;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
}

