"use client";

import { useEffect, useRef, useState } from "react";
import { getSession, listSessions } from "@/lib/api";
import {
  runResearchWebSocket,
  type AgentEvent,
  AGENT_LABELS,
} from "@/lib/websocket";
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

const PIPELINE_AGENTS = [
  "research_agent",
  "reader_agent",
  "analyst_agent",
  "critic_agent",
  "builder_agent",
];

const SOURCE_COLORS: Record<string, string> = {
  "arXiv": "var(--accent)",
  "Semantic Scholar": "var(--default)",
  "Web": "#10b981", // Emerald green for live web
};

function makeInitialAgents(): AgentEvent[] {
  return PIPELINE_AGENTS.map((id) => ({
    agent: id,
    label: AGENT_LABELS[id] ?? id,
    status: "idle" as const,
  }));
}

// ─── Agent Timeline ───────────────────────────────────────────────────────────

function AgentTimeline({ agents }: { agents: AgentEvent[] }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
      {agents.map((a, i) => {
        const isIdle = a.status === "idle";
        const isRunning = a.status === "running";
        const isDone = a.status === "done";

        const dotColor = isRunning
          ? "var(--accent)"
          : isDone
            ? "#34d399"
            : "var(--border)";

        const elapsed =
          isDone && a.startedAt && a.finishedAt
            ? ((a.finishedAt - a.startedAt) / 1000).toFixed(1)
            : null;

        return (
          <div key={a.agent} style={{ display: "flex", alignItems: "flex-start", gap: "14px" }}>
            {/* Dot + connector */}
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", flexShrink: 0 }}>
              <div
                style={{
                  width: 14,
                  height: 14,
                  borderRadius: "50%",
                  background: dotColor,
                  border: `2px solid ${dotColor}`,
                  boxShadow: isRunning ? `0 0 10px ${dotColor}` : "none",
                  transition: "all 0.3s ease",
                  marginTop: 4,
                }}
              />
              {i < agents.length - 1 && (
                <div
                  style={{
                    width: 2,
                    flexGrow: 1,
                    minHeight: 24,
                    background: isDone ? "#34d399" : "var(--border)",
                    marginTop: 2,
                    transition: "background 0.5s ease",
                  }}
                />
              )}
            </div>
            {/* Content */}
            <div style={{ paddingBottom: i < agents.length - 1 ? 12 : 0 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <span
                  style={{
                    fontWeight: 600,
                    color: isIdle ? "var(--muted)" : "var(--text)",
                    transition: "color 0.3s",
                  }}
                >
                  {a.label}
                </span>
                {isRunning && (
                  <span
                    style={{
                      fontSize: "0.75rem",
                      background: "rgba(139,92,246,0.2)",
                      color: "var(--accent)",
                      padding: "2px 8px",
                      borderRadius: 999,
                      fontWeight: 600,
                    }}
                  >
                    ● Active
                  </span>
                )}
                {isDone && elapsed && (
                  <span style={{ fontSize: "0.75rem", color: "#34d399" }}>
                    ✓ {elapsed}s
                  </span>
                )}
              </div>
              {(isRunning || isDone) && a.detail && (
                <p
                  style={{
                    margin: "4px 0 0",
                    fontSize: "0.82rem",
                    color: "var(--muted)",
                    lineHeight: 1.5,
                  }}
                >
                  {a.detail}
                </p>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ─── Result Tabs ──────────────────────────────────────────────────────────────

type Tab = "overview" | "papers" | "analysis" | "critique" | "plan";

function ResultPanel({ report }: { report: ResearchResponse }) {
  const [tab, setTab] = useState<Tab>("overview");

  const tabs: { id: Tab; label: string }[] = [
    { id: "overview", label: "Overview" },
    { id: "papers", label: `Papers (${report.papers.length})` },
    { id: "analysis", label: "Analysis" },
    { id: "critique", label: "Critique" },
    { id: "plan", label: "Build Plan" },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      {/* Tab bar */}
      <div
        style={{
          display: "flex",
          gap: 4,
          background: "var(--surface)",
          padding: 4,
          borderRadius: "var(--radius-md)",
          border: "1px solid var(--border)",
        }}
      >
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            style={{
              flex: 1,
              padding: "8px 12px",
              borderRadius: "calc(var(--radius-md) - 4px)",
              border: "none",
              cursor: "pointer",
              fontWeight: tab === t.id ? 700 : 500,
              fontSize: "0.85rem",
              background: tab === t.id ? "var(--accent)" : "transparent",
              color: tab === t.id ? "#fff" : "var(--muted)",
              transition: "all 0.2s",
            }}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {tab === "overview" && (
        <Card>
          <CardHeader>
            <div className="flex-between">
              <CardTitle>Research Overview</CardTitle>
              <Badge variant="accent">{report.query_type.replace(/_/g, " ")}</Badge>
            </div>
          </CardHeader>
          <CardContent>
            <p style={{ fontSize: "1.05rem", lineHeight: 1.8, marginBottom: 20 }}>{report.summary}</p>
            <div className="flex-row" style={{ flexWrap: "wrap", gap: 10 }}>
              <Badge>{report.papers.length} Papers</Badge>
              <Badge>{report.reader_outputs.length} Read</Badge>
              {report.critique && (
                <Badge variant={report.critique.overall_confidence > 0.8 ? "default" : "accent"}>
                  {Math.round(report.critique.overall_confidence * 100)}% Confidence
                </Badge>
              )}
              {report.critique?.review_mode && (
                <Badge>Mode: {report.critique.review_mode}</Badge>
              )}
            </div>

            {/* Execution trace */}
            {report.execution_trace.length > 0 && (
              <div style={{ marginTop: 24 }}>
                <strong style={{ fontSize: "0.85rem", color: "var(--muted)", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                  Execution Trace
                </strong>
                <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 8 }}>
                  {report.execution_trace.map((step, i) => (
                    <div key={i} style={{ display: "flex", justifyContent: "space-between", fontSize: "0.85rem", padding: "8px 12px", background: "var(--surface-strong)", borderRadius: "var(--radius-sm)" }}>
                      <span style={{ fontWeight: 600 }}>{AGENT_LABELS[step.agent_name] ?? step.agent_name}</span>
                      <span style={{ color: "var(--muted)" }}>{step.detail}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {tab === "papers" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {report.papers.map((paper) => (
            <Card key={paper.external_id}>
              <CardContent style={{ paddingTop: 16 }}>
                <div className="flex-between" style={{ alignItems: "flex-start", gap: 12 }}>
                  <strong style={{ fontSize: "1.05rem", lineHeight: 1.4 }}>{paper.title}</strong>
                  <Badge variant="accent" style={{ flexShrink: 0 }}>{paper.relevance_score}</Badge>
                </div>
                <p style={{ fontSize: "0.85rem", color: "var(--muted)", marginTop: 4 }}>
                  {paper.authors.join(", ")} · <span style={{ color: SOURCE_COLORS[paper.source] || "var(--muted)", fontWeight: 600 }}>{paper.source}</span>
                </p>
                <p style={{ fontSize: "0.9rem", marginTop: 10, lineHeight: 1.6, color: "var(--text)" }}>
                  {paper.abstract}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {tab === "analysis" && report.analysis && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <Card>
            <CardHeader><CardTitle>Key Research Themes</CardTitle></CardHeader>
            <CardContent>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                {report.analysis.themes.map((t, i) => (
                  <span key={i} style={{ padding: "6px 14px", background: "rgba(139,92,246,0.15)", color: "var(--accent)", borderRadius: 999, fontSize: "0.85rem", border: "1px solid rgba(139,92,246,0.3)" }}>
                    {t}
                  </span>
                ))}
              </div>
            </CardContent>
          </Card>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            <Card>
              <CardHeader><CardTitle>Consensus</CardTitle></CardHeader>
              <CardContent>
                <ul style={{ paddingLeft: 18, display: "flex", flexDirection: "column", gap: 8 }}>
                  {report.analysis.consensus.map((c, i) => (
                    <li key={i} style={{ fontSize: "0.9rem", color: "var(--text)", lineHeight: 1.6 }}>{c}</li>
                  ))}
                </ul>
              </CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle>Research Gaps</CardTitle></CardHeader>
              <CardContent>
                <ul style={{ paddingLeft: 18, display: "flex", flexDirection: "column", gap: 8 }}>
                  {report.analysis.gaps.map((g, i) => (
                    <li key={i} style={{ fontSize: "0.9rem", color: "var(--text)", lineHeight: 1.6 }}>{g}</li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          </div>

          {report.analysis.practical_applications.length > 0 && (
            <Card>
              <CardHeader><CardTitle>Practical Applications</CardTitle></CardHeader>
              <CardContent>
                <ul style={{ paddingLeft: 18, display: "flex", flexDirection: "column", gap: 8 }}>
                  {report.analysis.practical_applications.map((a, i) => (
                    <li key={i} style={{ fontSize: "0.9rem", lineHeight: 1.6 }}>{a}</li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {tab === "critique" && report.critique && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <Card>
            <CardHeader>
              <div className="flex-between">
                <CardTitle>Critique Summary</CardTitle>
                <div className="flex-row" style={{ gap: 8 }}>
                  <Badge>Mode: {report.critique.review_mode}</Badge>
                  <Badge variant={report.critique.overall_confidence > 0.8 ? "default" : "accent"}>
                    {Math.round(report.critique.overall_confidence * 100)}% Confidence
                  </Badge>
                </div>
              </div>
            </CardHeader>
            {report.critique.llm_summary && (
              <CardContent>
                <p style={{ fontStyle: "italic", color: "var(--muted)", lineHeight: 1.7, padding: "12px 16px", background: "var(--surface-strong)", borderRadius: "var(--radius-sm)", borderLeft: "3px solid var(--accent)" }}>
                  {report.critique.llm_summary}
                </p>
              </CardContent>
            )}
          </Card>
          {report.critique.critiques.map((c, i) => (
            <Card key={i}>
              <CardContent style={{ paddingTop: 16 }}>
                <div className="flex-between" style={{ marginBottom: 8 }}>
                  <Badge>{c.category}</Badge>
                  <Badge variant={c.severity === "high" ? "accent" : "default"}>{c.severity}</Badge>
                </div>
                <p style={{ fontWeight: 600, marginBottom: 6 }}>{c.issue}</p>
                <p style={{ fontSize: "0.88rem", color: "var(--muted)", marginBottom: 6 }}>
                  <strong>Evidence:</strong> {c.evidence}
                </p>
                <p style={{ fontSize: "0.88rem", color: "var(--muted)" }}>
                  <strong>Impact:</strong> {c.impact}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {tab === "plan" && report.implementation_plan && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <Card style={{ border: "1px solid rgba(139,92,246,0.4)" }}>
            <CardHeader><CardTitle style={{ color: "#c4b5fd" }}>Project Idea</CardTitle></CardHeader>
            <CardContent>
              <p style={{ fontSize: "1.1rem", lineHeight: 1.7 }}>{report.implementation_plan.project_idea}</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle>Value Proposition</CardTitle></CardHeader>
            <CardContent>
              <p style={{ lineHeight: 1.7 }}>{report.implementation_plan.value_proposition}</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle>MVP Roadmap</CardTitle></CardHeader>
            <CardContent>
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                {report.implementation_plan.mvp_roadmap.map((phase) => (
                  <div key={phase.name} style={{ padding: 14, background: "var(--surface-strong)", borderRadius: "var(--radius-md)", border: "1px solid var(--border)" }}>
                    <div className="flex-between" style={{ marginBottom: 8 }}>
                      <strong style={{ color: "var(--accent-secondary)" }}>{phase.name}</strong>
                      <span style={{ fontSize: "0.82rem", color: "var(--muted)" }}>{phase.duration}</span>
                    </div>
                    <ul style={{ paddingLeft: 18, margin: 0, display: "flex", flexDirection: "column", gap: 4 }}>
                      {phase.goals.map((g, i) => (
                        <li key={i} style={{ fontSize: "0.88rem", lineHeight: 1.6 }}>{g}</li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle>Challenges & Mitigations</CardTitle></CardHeader>
            <CardContent>
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {report.implementation_plan.challenges.map((ch, i) => (
                  <div key={i} style={{ padding: 12, background: "rgba(239,68,68,0.08)", borderRadius: "var(--radius-sm)", border: "1px solid rgba(239,68,68,0.2)" }}>
                    <p style={{ fontWeight: 600, marginBottom: 4, fontSize: "0.9rem" }}>⚠ {ch.challenge}</p>
                    <p style={{ fontSize: "0.88rem", color: "var(--muted)" }}>{ch.mitigation}</p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}

// ─── Main Dashboard ───────────────────────────────────────────────────────────

export function ResearchDashboard() {
  const [query, setQuery] = useState("multi agent research systems");
  const [queryType, setQueryType] = useState<QueryType>("deep_analysis");
  const [maxResults, setMaxResults] = useState(5);

  const [isRunning, setIsRunning] = useState(false);
  const [agents, setAgents] = useState<AgentEvent[]>(makeInitialAgents());
  const [report, setReport] = useState<ResearchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [isLoadingSessions, setIsLoadingSessions] = useState(false);

  const cleanupRef = useRef<(() => void) | null>(null);

  // Load past sessions on mount
  useEffect(() => {
    setIsLoadingSessions(true);
    listSessions()
      .then((data) => setSessions(data.sessions))
      .catch(() => {/* silently ignore — backend may not be ready */})
      .finally(() => setIsLoadingSessions(false));
  }, []);

  function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (isRunning) return;

    setError(null);
    setReport(null);
    setAgents(makeInitialAgents());
    setIsRunning(true);

    const cleanup = runResearchWebSocket(
      { query, maxResults, queryType },
      {
        onAgentStart(agent, message) {
          setAgents((prev) =>
            prev.map((a) =>
              a.agent === agent
                ? { ...a, status: "running", detail: message, startedAt: Date.now() }
                : a,
            ),
          );
        },
        onAgentDone(agent, detail) {
          setAgents((prev) =>
            prev.map((a) =>
              a.agent === agent
                ? { ...a, status: "done", detail, finishedAt: Date.now() }
                : a,
            ),
          );
        },
        onDone(result) {
          setReport(result);
          setIsRunning(false);
          // Refresh session list
          listSessions()
            .then((data) => setSessions(data.sessions))
            .catch(() => {});
        },
        onError(message) {
          setError(message);
          setIsRunning(false);
        },
      },
    );

    cleanupRef.current = cleanup;
  }

  // Cleanup WS on unmount
  useEffect(() => {
    return () => { cleanupRef.current?.(); };
  }, []);

  function handleSessionOpen(sessionId: string) {
    setError(null);
    setReport(null);
    setAgents(makeInitialAgents());
    getSession(sessionId)
      .then(setReport)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load session."));
  }

  const allDone = agents.every((a) => a.status === "done");

  return (
    <div className="shell animate-slide-up">
      <div style={{ textAlign: "center", marginBottom: "32px" }}>
        <Badge variant="accent" className="mb-4">Local-First · Ollama-Powered</Badge>
        <h1>Autonomous Research Orchestrator</h1>
        <p className="text-muted" style={{ maxWidth: "600px", margin: "16px auto", fontSize: "1.1rem" }}>
          Five specialized agents collaborate in real-time to discover papers, extract insights, critique methodologies, and generate actionable plans.
        </p>
      </div>

      <div className="dashboard-grid">
        {/* ── Left sidebar ── */}
        <aside>
          <Card className="mb-4">
            <CardHeader>
              <CardTitle>Configure Research</CardTitle>
              <p className="text-muted" style={{ fontSize: "0.9rem", marginTop: 4 }}>
                Describe your topic to initiate the pipeline.
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
                {isRunning ? "Pipeline Running..." : "Execute Pipeline"}
              </Button>
            </form>
          </Card>

          {/* Agent Progress Timeline */}
          {(isRunning || allDone) && (
            <Card className={isRunning ? "animate-pulse-glow" : ""}>
              <CardHeader>
                <CardTitle>Agent Pipeline</CardTitle>
                <p className="text-muted" style={{ fontSize: "0.85rem", marginTop: 4 }}>
                  {isRunning ? "Agents are working..." : "All agents completed ✓"}
                </p>
              </CardHeader>
              <CardContent>
                <AgentTimeline agents={agents} />
              </CardContent>
            </Card>
          )}

          {/* Past Sessions */}
          {!isRunning && (
            <Card style={{ marginTop: 16 }}>
              <CardHeader>
                <CardTitle>Saved Sessions</CardTitle>
                <p className="text-muted" style={{ fontSize: "0.9rem", marginTop: 4 }}>
                  {isLoadingSessions ? "Loading..." : `${sessions.length} sessions`}
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
                        color: "var(--text)",
                      }}
                    >
                      <strong style={{ display: "block", marginBottom: 4 }}>{session.query}</strong>
                      <div className="flex-between text-muted" style={{ fontSize: "0.8rem" }}>
                        <span>{session.query_type.replace(/_/g, " ")}</span>
                        <span>{new Date(session.generated_at).toLocaleDateString()}</span>
                      </div>
                    </button>
                  ))
                )}
              </div>
            </Card>
          )}
        </aside>

        {/* ── Main panel ── */}
        <section>
          {error && (
            <div style={{ padding: "16px", background: "rgba(239, 68, 68, 0.15)", color: "#fca5a5", borderRadius: "var(--radius-md)", marginBottom: "24px", border: "1px solid rgba(239,68,68,0.3)" }}>
              {error}
            </div>
          )}

          {!report && !isRunning && (
            <Card style={{ minHeight: "500px", display: "flex", alignItems: "center", justifyContent: "center", borderStyle: "dashed", background: "transparent" }}>
              <div style={{ textAlign: "center" }}>
                <CardTitle style={{ color: "var(--muted)", marginBottom: 8 }}>Awaiting Execution</CardTitle>
                <p className="text-muted">Configure your query and click Execute Pipeline to start.</p>
              </div>
            </Card>
          )}

          {isRunning && !report && (
            <Card style={{ minHeight: "500px", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <div style={{ textAlign: "center", display: "flex", flexDirection: "column", alignItems: "center", gap: 16 }}>
                <svg className="animate-spin" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth="2">
                  <path d="M12 2v4m0 12v4M4.93 4.93l2.83 2.83m8.48 8.48l2.83 2.83M2 12h4m12 0h4M4.93 19.07l2.83-2.83m8.48-8.48l2.83-2.83" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                <CardTitle>Agents are active...</CardTitle>
                <p className="text-muted">Watch the timeline in the sidebar as each agent completes.</p>
              </div>
            </Card>
          )}

          {report && <ResultPanel report={report} />}
        </section>
      </div>
    </div>
  );
}
