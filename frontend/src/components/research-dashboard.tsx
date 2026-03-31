"use client";

import { useEffect, useState, useTransition } from "react";
import { getSession, listSessions, runResearch } from "@/lib/api";
import {
  type QueryType,
  type ResearchResponse,
  type SessionSummary,
} from "@/lib/types";
import { Button } from "./ui/Button";
import { Card, CardHeader, CardTitle, CardContent, Badge } from "./ui/Card";
import { Input, Select, Textarea } from "./ui/Input";

const QUERY_OPTIONS = [
  { label: "Simple Search", value: "simple_search" },
  { label: "Deep Analysis", value: "deep_analysis" },
  { label: "Critical Review", value: "critical_review" },
  { label: "Startup Idea", value: "startup_idea" },
];

export function ResearchDashboard() {
  const [query, setQuery] = useState("multi agent research systems");
  const [queryType, setQueryType] = useState<QueryType>("simple_search");
  const [maxResults, setMaxResults] = useState(3);
  const [report, setReport] = useState<ResearchResponse | null>(null);
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isRunning, startRunTransition] = useTransition();
  const [isLoadingSessions, startSessionsTransition] = useTransition();

  useEffect(() => {
    startSessionsTransition(async () => {
      try {
        const data = await listSessions();
        setSessions(data.sessions);
      } catch (loadError) {
        setError(
          loadError instanceof Error
            ? loadError.message
            : "Failed to load saved sessions.",
        );
      }
    });
  }, []);

  async function refreshSessions() {
    const data = await listSessions();
    setSessions(data.sessions);
  }

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    startRunTransition(async () => {
      try {
        const nextReport = await runResearch({
          query,
          maxResults,
          queryType,
        });
        setReport(nextReport);
        await refreshSessions();
      } catch (runError) {
        setError(
          runError instanceof Error
            ? runError.message
            : "Something went wrong while running the research workflow.",
        );
      }
    });
  }

  function handleSessionOpen(sessionId: string) {
    setError(null);
    startRunTransition(async () => {
      try {
        const savedReport = await getSession(sessionId);
        setReport(savedReport);
      } catch (loadError) {
        setError(
          loadError instanceof Error
            ? loadError.message
            : "Failed to open the saved session.",
        );
      }
    });
  }

  return (
    <div className="shell animate-slide-up">
      <div style={{ textAlign: "center", marginBottom: "32px" }}>
        <Badge variant="accent" className="mb-4">Local-First Workflow</Badge>
        <h1>Autonomous Research Orchestrator</h1>
        <p className="text-muted" style={{ maxWidth: "600px", margin: "16px auto", fontSize: "1.1rem" }}>
          Run the full multi-agent pipeline: discover papers, extract insights, critique methodologies, and generate actionable implementations.
        </p>
      </div>

      <div className="dashboard-grid">
        <aside>
          <Card className="mb-4">
            <CardHeader>
              <CardTitle>Configure Research</CardTitle>
              <p className="text-muted" style={{ fontSize: "0.9rem", marginTop: 4 }}>
                Describe your topic to initiate the agents.
              </p>
            </CardHeader>
            <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
              <Textarea
                label="Research Query"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="What do you want to research?"
              />
              <Select
                label="Workflow Mode"
                value={queryType}
                onChange={(e) => setQueryType(e.target.value as QueryType)}
                options={QUERY_OPTIONS}
              />
              <Input
                label="Max Papers"
                type="number"
                min={1}
                max={15}
                value={maxResults}
                onChange={(e) => setMaxResults(Number(e.target.value))}
              />
              <Button type="submit" isLoading={isRunning} className="mt-4">
                Execute Pipeline
              </Button>
            </form>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Saved Sessions</CardTitle>
              <p className="text-muted" style={{ fontSize: "0.9rem", marginTop: 4 }}>
                {isLoadingSessions ? "Loading..." : `${sessions.length} sessions available`}
              </p>
            </CardHeader>
            <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
              {sessions.length === 0 ? (
                <p className="text-muted" style={{ fontSize: "0.9rem" }}>No past sessions found.</p>
              ) : (
                sessions.map((session) => (
                  <button
                    key={session.session_id}
                    onClick={() => handleSessionOpen(session.session_id)}
                    style={{
                      textAlign: "left",
                      background: "var(--surface-strong)",
                      border: "1px solid var(--border)",
                      padding: "12px",
                      borderRadius: "var(--radius-sm)",
                      cursor: "pointer",
                      color: "var(--text)"
                    }}
                  >
                    <strong style={{ display: "block", marginBottom: 4 }}>{session.query}</strong>
                    <div className="flex-between text-muted" style={{ fontSize: "0.8rem" }}>
                      <span>{session.query_type}</span>
                      <span>{new Date(session.generated_at).toLocaleDateString()}</span>
                    </div>
                  </button>
                ))
              )}
            </div>
          </Card>
        </aside>

        <section>
          {error && (
            <div style={{ padding: "16px", background: "rgba(239, 68, 68, 0.15)", color: "#fca5a5", borderRadius: "var(--radius-md)", marginBottom: "24px", border: "1px solid rgba(239,68,68,0.3)" }}>
              {error}
            </div>
          )}

          {!report && !isRunning ? (
            <Card style={{ minHeight: "500px", display: "flex", alignItems: "center", justifyContent: "center", borderStyle: "dashed", background: "transparent" }}>
              <div style={{ textAlign: "center" }}>
                <CardTitle style={{ color: "var(--muted)", marginBottom: 8 }}>Awaiting Execution</CardTitle>
                <p className="text-muted">Start a query to see the multi-agent pipeline results.</p>
              </div>
            </Card>
          ) : isRunning ? (
            <Card className="animate-pulse-glow" style={{ minHeight: "500px", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <div style={{ textAlign: "center", display: "flex", flexDirection: "column", alignItems: "center", gap: 16 }}>
                <svg className="animate-spin" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth="2">
                  <path d="M12 2v4m0 12v4M4.93 4.93l2.83 2.83m8.48 8.48l2.83 2.83M2 12h4m12 0h4M4.93 19.07l2.83-2.83m8.48-8.48l2.83-2.83" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
                <CardTitle>Agents are active...</CardTitle>
                <p className="text-muted">Orchestrating search, reading, analysis, and critique.</p>
              </div>
            </Card>
          ) : (report &&
            <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
              <Card>
                <CardHeader>
                  <div className="flex-between">
                    <CardTitle>Research Overview</CardTitle>
                    <Badge variant="accent">{report.query_type}</Badge>
                  </div>
                </CardHeader>
                <CardContent>
                  <p style={{ fontSize: "1.1rem", lineHeight: 1.7, marginBottom: 20 }}>{report.summary}</p>
                  <div className="flex-row">
                    <Badge>{report.papers.length} Papers Synced</Badge>
                    {report.critique && (
                      <Badge variant={report.critique.overall_confidence > 0.8 ? "default" : "accent"}>
                        {Math.round(report.critique.overall_confidence * 100)}% Confidence
                      </Badge>
                    )}
                  </div>
                </CardContent>
              </Card>

              {report.analysis && (
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "24px" }}>
                  <Card>
                    <CardHeader><CardTitle>Key Themes</CardTitle></CardHeader>
                    <CardContent>
                      <ul style={{ display: "flex", flexDirection: "column", gap: 10, paddingLeft: 20, color: "var(--muted)" }}>
                        {report.analysis.themes.map((theme, i) => (
                          <li key={i}><span style={{ color: "var(--text)" }}>{theme}</span></li>
                        ))}
                      </ul>
                    </CardContent>
                  </Card>
                  
                  <Card>
                    <CardHeader><CardTitle>Identified Gaps</CardTitle></CardHeader>
                    <CardContent>
                      <ul style={{ display: "flex", flexDirection: "column", gap: 10, paddingLeft: 20, color: "var(--muted)" }}>
                        {report.analysis.gaps.map((gap, i) => (
                          <li key={i}><span style={{ color: "var(--text)" }}>{gap}</span></li>
                        ))}
                      </ul>
                    </CardContent>
                  </Card>
                </div>
              )}

              {report.papers.length > 0 && (
                <Card>
                  <CardHeader><CardTitle>Paper Sources</CardTitle></CardHeader>
                  <CardContent style={{ display: "grid", gap: "16px" }}>
                    {report.papers.map((paper) => (
                      <div key={paper.external_id} style={{ background: "var(--surface-strong)", padding: "16px", borderRadius: "var(--radius-md)", border: "1px solid var(--border)" }}>
                        <strong style={{ display: "block", marginBottom: 6, fontSize: "1.05rem" }}>{paper.title}</strong>
                        <div className="flex-row text-muted" style={{ fontSize: "0.85rem" }}>
                          <span>{paper.source}</span>
                          <span>•</span>
                          <span style={{ color: "var(--accent)" }}>Score: {paper.relevance_score}</span>
                        </div>
                      </div>
                    ))}
                  </CardContent>
                </Card>
              )}

              {report.implementation_plan && (
                <Card style={{ border: "1px solid rgba(139, 92, 246, 0.4)" }}>
                  <CardHeader>
                    <CardTitle style={{ color: "#c4b5fd" }}>Builder Agent: Implementation Plan</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div style={{ marginBottom: 20 }}>
                      <strong style={{ display: "block", marginBottom: 8, color: "var(--muted)" }}>Project Idea</strong>
                      <p style={{ fontSize: "1.1rem" }}>{report.implementation_plan.project_idea}</p>
                    </div>
                    <div style={{ marginBottom: 20 }}>
                      <strong style={{ display: "block", marginBottom: 8, color: "var(--muted)" }}>Value Proposition</strong>
                      <p>{report.implementation_plan.value_proposition}</p>
                    </div>
                    <div>
                      <strong style={{ display: "block", marginBottom: 8, color: "var(--muted)" }}>MVP Roadmap</strong>
                      <div style={{ display: "grid", gap: 12 }}>
                        {report.implementation_plan.mvp_roadmap.map((phase) => (
                          <div key={phase.name} style={{ background: "rgba(0,0,0,0.2)", padding: 12, borderRadius: "var(--radius-sm)" }}>
                            <strong style={{ color: "var(--accent-secondary)" }}>{phase.name}</strong> <span className="text-muted">({phase.duration})</span>
                            <p style={{ marginTop: 4, fontSize: "0.9rem" }}>{phase.goals[0]}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
