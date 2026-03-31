import {
  type QueryType,
  type ResearchResponse,
  type SessionListResponse,
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
