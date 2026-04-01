"use client";

import { useEffect, useRef, useState } from "react";
import { deleteSession, exportSession, getSession, listSessions, analyzeDocument } from "@/lib/api";
import {
  runResearchWebSocket,
  type AgentEvent,
  AGENT_LABELS,
} from "@/lib/websocket";
import {
  type PaperProgress,
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
  arXiv: "var(--accent)",
  "Semantic Scholar": "var(--muted)",
  Web: "#10b981",
};

function makeInitialAgents(): AgentEvent[] {
  return PIPELINE_AGENTS.map((id) => ({
    agent: id,
    label: AGENT_LABELS[id] ?? id,
    status: "idle" as const,
  }));
}

function relativeDate(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

// ─── Agent Timeline ───────────────────────────────────────────────────────────

function AgentTimeline({
  agents,
  paperProgress,
}: {
  agents: AgentEvent[];
  paperProgress: PaperProgress | null;
}) {
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

        const showProgress =
          a.agent === "reader_agent" && isRunning && paperProgress;

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
            <div style={{ flex: 1, paddingBottom: i < agents.length - 1 ? 12 : 0 }}>
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

              {/* Per-paper progress bar */}
              {showProgress && (
                <div style={{ marginTop: 8 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                    <span style={{ fontSize: "0.75rem", color: "var(--muted)" }} className="typing-cursor">
                      {paperProgress.index}/{paperProgress.total} &mdash; {paperProgress.title.slice(0, 42)}{paperProgress.title.length > 42 ? "…" : ""}
                    </span>
                  </div>
                  <div className="progress-bar-container">
                    <div
                      className="progress-bar-fill"
                      style={{ width: `${(paperProgress.index / paperProgress.total) * 100}%` }}
                    />
                  </div>
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ─── Result Tabs ──────────────────────────────────────────────────────────────

type Tab = "overview" | "papers" | "analysis" | "innovations" | "critique" | "plan" | "architecture";

function ResultPanel({
  report,
  onExport,
}: {
  report: ResearchResponse;
  onExport: () => void;
}) {
  const [tab, setTab] = useState<Tab>("overview");
  const [exporting, setExporting] = useState(false);

  const tabs: { id: Tab; label: string }[] = [
    { id: "overview", label: "Overview" },
    { id: "papers", label: `Papers (${report.papers.length})` },
    { id: "analysis", label: "Analysis" },
    { id: "innovations", label: "Innovations" },
    { id: "critique", label: "Critique" },
    { id: "plan", label: "Build Plan" },
    { id: "architecture", label: "Architecture" },
  ];

  async function handleExport() {
    setExporting(true);
    try {
      await onExport();
    } finally {
      setExporting(false);
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      {/* Header with export button */}
      <div className="flex-between" style={{ flexWrap: "wrap", gap: 12 }}>
        <div style={{ fontSize: "0.85rem", color: "var(--muted)" }}>
          Session: <code style={{ color: "var(--accent)", fontSize: "0.8rem" }}>{report.session_id?.slice(0, 8) ?? "—"}</code>
        </div>
        <button
          className={`btn-icon ${!exporting ? "btn-icon-success" : ""}`}
          onClick={handleExport}
          disabled={exporting || !report.session_id}
          title="Download full report as JSON"
        >
          {exporting ? "↓ Exporting…" : "↓ Export JSON"}
        </button>
      </div>

      {/* Tab bar */}
      <div
        style={{
          display: "flex",
          gap: 4,
          background: "var(--surface)",
          padding: 4,
          borderRadius: "var(--radius-md)",
          border: "1px solid var(--border)",
          overflowX: "auto",
          scrollbarWidth: "none",
        }}
      >
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            style={{
              flexShrink: 0,
              padding: "8px 12px",
              borderRadius: "calc(var(--radius-md) - 4px)",
              border: "none",
              cursor: "pointer",
              fontWeight: tab === t.id ? 700 : 500,
              fontSize: "0.82rem",
              background: tab === t.id ? "var(--accent)" : "transparent",
              color: tab === t.id ? "#fff" : "var(--muted)",
              transition: "all 0.2s",
              whiteSpace: "nowrap",
            }}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab content — each wrapped in animate-fade-in */}
      <div className="animate-fade-in" key={tab}>

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
                      <div
                        key={i}
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          fontSize: "0.85rem",
                          padding: "8px 12px",
                          background: "var(--surface-strong)",
                          borderRadius: "var(--radius-sm)",
                          gap: 12,
                          flexWrap: "wrap",
                        }}
                      >
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
                    <div style={{ display: "flex", gap: 6, flexShrink: 0 }}>
                      <Badge variant="accent">{paper.relevance_score}</Badge>
                      <span
                        style={{
                          fontSize: "0.75rem",
                          fontWeight: 700,
                          color: SOURCE_COLORS[paper.source] ?? "var(--muted)",
                          padding: "2px 8px",
                          borderRadius: 999,
                          border: `1px solid ${SOURCE_COLORS[paper.source] ?? "var(--border)"}22`,
                          background: `${SOURCE_COLORS[paper.source] ?? "var(--muted)"}18`,
                          alignSelf: "flex-start",
                        }}
                      >
                        {paper.source}
                      </span>
                    </div>
                  </div>
                  <p style={{ fontSize: "0.85rem", color: "var(--muted)", marginTop: 4 }}>
                    {paper.authors.join(", ")}
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

        {tab === "innovations" && report.analysis && (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            {/* Innovations grid */}
            {report.analysis.innovations.length > 0 ? (
              <>
                <Card>
                  <CardHeader><CardTitle>🔬 Paper Innovations</CardTitle></CardHeader>
                  <CardContent>
                    <div className="innovation-grid">
                      {report.analysis.innovations.map((inn, i) => (
                        <div
                          key={i}
                          style={{
                            padding: 16,
                            background: "var(--surface-strong)",
                            borderRadius: "var(--radius-md)",
                            border: "1px solid var(--border)",
                          }}
                        >
                          <p style={{ fontSize: "0.8rem", color: "var(--accent)", fontWeight: 700, marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.04em" }}>
                            {inn.paper_title.slice(0, 50)}{inn.paper_title.length > 50 ? "…" : ""}
                          </p>
                          <p style={{ fontSize: "0.9rem", lineHeight: 1.6, marginBottom: 8 }}>{inn.innovation}</p>
                          <p style={{ fontSize: "0.82rem", color: "#34d399", lineHeight: 1.5 }}>
                            <strong>Impact: </strong>{inn.impact}
                          </p>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>

                {/* Conflicts if any */}
                {report.analysis.conflicts.length > 0 && (
                  <Card>
                    <CardHeader><CardTitle>⚡ Conflicting Evidence</CardTitle></CardHeader>
                    <CardContent>
                      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                        {report.analysis.conflicts.map((conflict, i) => (
                          <div key={i} style={{ padding: 12, background: "rgba(245,158,11,0.08)", border: "1px solid rgba(245,158,11,0.25)", borderRadius: "var(--radius-sm)" }}>
                            <p style={{ fontWeight: 600, marginBottom: 4 }}>{conflict.topic}</p>
                            <p style={{ fontSize: "0.88rem", color: "var(--muted)" }}>{conflict.description}</p>
                            {conflict.papers.length > 0 && (
                              <div style={{ marginTop: 8, display: "flex", flexWrap: "wrap", gap: 4 }}>
                                {conflict.papers.map((p, j) => (
                                  <span key={j} style={{ fontSize: "0.75rem", padding: "2px 8px", background: "rgba(245,158,11,0.15)", color: "#fbbf24", borderRadius: 999, border: "1px solid rgba(245,158,11,0.2)" }}>
                                    {p.slice(0, 30)}{p.length > 30 ? "…" : ""}
                                  </span>
                                ))}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                )}
              </>
            ) : (
              <Card>
                <CardContent style={{ paddingTop: 24, textAlign: "center" }}>
                  <p className="text-muted">No innovation summaries were extracted for this query.</p>
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
                  {report.implementation_plan?.mvp_roadmap.map((phase, pi) => (
                    <div key={pi} style={{ padding: 14, background: "var(--surface-strong)", borderRadius: "var(--radius-md)", border: "1px solid var(--border)" }}>
                      <div className="flex-between" style={{ marginBottom: 8 }}>
                        <strong style={{ color: "var(--accent-secondary)" }}>{phase.name}</strong>
                        <span style={{ fontSize: "0.82rem", color: "var(--muted)" }}>{phase.duration}</span>
                      </div>
                      <ul style={{ paddingLeft: 18, margin: 0, display: "flex", flexDirection: "column", gap: 4 }}>
                        {phase.goals.map((g, gi) => (
                          <li key={gi} style={{ fontSize: "0.88rem", lineHeight: 1.6 }}>{g}</li>
                        ))}
                      </ul>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle>Challenges &amp; Mitigations</CardTitle></CardHeader>
              <CardContent>
                <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                  {report.implementation_plan?.challenges.map((ch, ci) => (
                    <div key={ci} style={{ padding: 12, background: "rgba(239,68,68,0.08)", borderRadius: "var(--radius-sm)", border: "1px solid rgba(239,68,68,0.2)" }}>
                      <p style={{ fontWeight: 600, marginBottom: 4, fontSize: "0.9rem" }}>⚠ {ch.challenge}</p>
                      <p style={{ fontSize: "0.88rem", color: "var(--muted)" }}>{ch.mitigation}</p>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {tab === "architecture" && report.implementation_plan && (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <Card>
              <CardHeader><CardTitle>🏗 System Architecture</CardTitle></CardHeader>
              <CardContent>
                <p style={{ lineHeight: 1.7, marginBottom: 20, borderLeft: "3px solid var(--accent)", paddingLeft: 14, color: "var(--muted)", fontStyle: "italic" }}>
                  {report.implementation_plan?.architecture.summary}
                </p>
                <strong style={{ fontSize: "0.85rem", color: "var(--muted)", textTransform: "uppercase", letterSpacing: "0.05em" }}>Components</strong>
                <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 8 }}>
                  {report.implementation_plan?.architecture.components.map((comp, i) => (
                    <div key={i} style={{ display: "flex", alignItems: "center", gap: 10, padding: "10px 14px", background: "var(--surface-strong)", borderRadius: "var(--radius-sm)", border: "1px solid var(--border)" }}>
                      <span style={{ color: "var(--accent)", fontSize: "1rem" }}>⬡</span>
                      <span style={{ fontSize: "0.9rem" }}>{comp}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle>🔄 Data Flow</CardTitle></CardHeader>
              <CardContent>
                <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
                  {report.implementation_plan?.architecture.data_flow.map((step, i) => (
                    <div key={i} style={{ display: "flex", gap: 14, alignItems: "flex-start" }}>
                      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", flexShrink: 0 }}>
                        <div style={{ width: 28, height: 28, borderRadius: "50%", background: "var(--accent-soft)", border: "1px solid rgba(139,92,246,0.4)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "0.75rem", fontWeight: 700, color: "var(--accent)" }}>
                          {i + 1}
                        </div>
                        {i < (report.implementation_plan?.architecture.data_flow.length || 0) - 1 && (
                          <div style={{ width: 2, height: 24, background: "rgba(139,92,246,0.2)", margin: "2px 0" }} />
                        )}
                      </div>
                      <p style={{ fontSize: "0.9rem", lineHeight: 1.6, paddingTop: 4, paddingBottom: i < (report.implementation_plan?.architecture.data_flow.length || 0) - 1 ? 0 : 0 }}>
                        {step}
                      </p>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
            {/* Data Requirements */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
               <Card>
                 <CardHeader><CardTitle>📦 Datasets</CardTitle></CardHeader>
                 <CardContent>
                   <ul style={{ paddingLeft: 18, display: "flex", flexDirection: "column", gap: 6 }}>
                     {report.implementation_plan?.data_requirements.datasets.map((d, i) => (
                       <li key={i} style={{ fontSize: "0.88rem" }}>{d}</li>
                     ))}
                   </ul>
                 </CardContent>
               </Card>
               <Card>
                 <CardHeader><CardTitle>🔒 Privacy</CardTitle></CardHeader>
                 <CardContent>
                   <ul style={{ paddingLeft: 18, display: "flex", flexDirection: "column", gap: 6 }}>
                     {report.implementation_plan?.data_requirements.privacy_considerations.map((p, i) => (
                       <li key={i} style={{ fontSize: "0.88rem" }}>{p}</li>
                     ))}
                   </ul>
                 </CardContent>
               </Card>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Main Dashboard ───────────────────────────────────────────────────────────

export function ResearchDashboard() {
  const [mode, setMode] = useState<"search" | "document">("search");
  const [query, setQuery] = useState("multi agent research systems");
  const [docTitle, setDocTitle] = useState("");
  const [docContent, setDocContent] = useState("");
  const [queryType, setQueryType] = useState<QueryType>("deep_analysis");
  const [maxResults, setMaxResults] = useState(5);

  const [isRunning, setIsRunning] = useState(false);
  const [agents, setAgents] = useState<AgentEvent[]>(makeInitialAgents());
  const [paperProgress, setPaperProgress] = useState<PaperProgress | null>(null);
  const [report, setReport] = useState<ResearchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [isLoadingSessions, setIsLoadingSessions] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const cleanupRef = useRef<(() => void) | null>(null);

  // Load past sessions on mount
  useEffect(() => {
    setIsLoadingSessions(true);
    listSessions()
      .then((data) => setSessions(data.sessions))
      .catch(() => {/* silently ignore — backend may not be ready */})
      .finally(() => setIsLoadingSessions(false));
  }, []);

  async function handleDocAnalysis(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (isRunning || !docContent) return;

    setError(null);
    setReport(null);
    setAgents(makeInitialAgents().slice(1)); // Skip discovery agent
    setIsRunning(true);

    try {
      const result = await analyzeDocument(docTitle || "Untitled Document", docContent);
      setReport(result);
      // Simulate agent completion for visual consistency
      setAgents(agents => agents.map(a => ({ ...a, status: "done", detail: "Processed uploaded content." })));
      // Refresh list
      const data = await listSessions();
      setSessions(data.sessions);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to analyze document.");
    } finally {
      setIsRunning(false);
    }
  }

  function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    if (mode === "document") {
      handleDocAnalysis(e);
      return;
    }
    
    e.preventDefault();
    if (isRunning) return;

    setError(null);
    setReport(null);
    setPaperProgress(null);
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
          // Clear paper progress when reader starts fresh
          if (agent === "reader_agent") setPaperProgress(null);
        },
        onAgentDone(agent, detail) {
          setAgents((prev) =>
            prev.map((a) =>
              a.agent === agent
                ? { ...a, status: "done", detail, finishedAt: Date.now() }
                : a,
            ),
          );
          if (agent === "reader_agent") setPaperProgress(null);
        },
        onPaperProgress(progress) {
          setPaperProgress(progress);
        },
        onDone(result) {
          setReport(result);
          setIsRunning(false);
          setPaperProgress(null);
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

  async function handleSessionDelete(sessionId: string) {
    setDeletingId(sessionId);
    try {
      await deleteSession(sessionId);
      setSessions((prev) => prev.filter((s) => s.session_id !== sessionId));
      // Clear report if it's the current one
      if (report?.session_id === sessionId) setReport(null);
    } catch {
      /* ignore */
    } finally {
      setDeletingId(null);
    }
  }

  async function handleExportReport() {
    if (!report?.session_id) return;
    await exportSession(report.session_id);
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
              <div className="flex-between">
                <CardTitle>Configure Research</CardTitle>
                <div style={{ display: "flex", gap: 4, background: "var(--surface)", padding: 2, borderRadius: 6 }}>
                   <button 
                     onClick={() => setMode("search")}
                     style={{ padding: "4px 8px", fontSize: "0.75rem", borderRadius: 4, border: "none", cursor: "pointer", background: mode === "search" ? "var(--accent)" : "transparent", color: mode === "search" ? "white" : "var(--muted)" }}
                   >Search</button>
                   <button 
                     onClick={() => setMode("document")}
                     style={{ padding: "4px 8px", fontSize: "0.75rem", borderRadius: 4, border: "none", cursor: "pointer", background: mode === "document" ? "var(--accent)" : "transparent", color: mode === "document" ? "white" : "var(--muted)" }}
                   >Doc</button>
                </div>
              </div>
              <p className="text-muted" style={{ fontSize: "0.9rem", marginTop: 4 }}>
                {mode === "search" ? "Discover new papers from the web" : "Analyze a specific document in depth"}
              </p>
            </CardHeader>
            <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
              {mode === "search" ? (
                <>
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
                </>
              ) : (
                <>
                  <Input
                    label="Document Title"
                    value={docTitle}
                    onChange={(e) => setDocTitle(e.target.value)}
                    placeholder="e.g., Attention Is All You Need"
                  />
                  <Textarea
                    label="Paste Content or Abstract"
                    value={docContent}
                    onChange={(e) => setDocContent(e.target.value)}
                    placeholder="Paste the document text here..."
                    style={{ minHeight: 200 }}
                  />
                </>
              )}
              <Button type="submit" isLoading={isRunning} className="mt-4">
                {isRunning ? "Running..." : mode === "search" ? "Execute Pipeline" : "Analyze Document"}
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
                <AgentTimeline agents={agents} paperProgress={paperProgress} />
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
                    <div
                      key={session.session_id}
                      style={{
                        background: "var(--surface-strong)",
                        border: report?.session_id === session.session_id ? "1px solid var(--accent)" : "1px solid var(--border)",
                        padding: "12px",
                        borderRadius: "var(--radius-sm)",
                        transition: "border-color 0.2s",
                      }}
                    >
                      <button
                        onClick={() => handleSessionOpen(session.session_id)}
                        style={{
                          display: "block",
                          width: "100%",
                          textAlign: "left",
                          background: "transparent",
                          border: "none",
                          cursor: "pointer",
                          color: "var(--text)",
                          padding: 0,
                          marginBottom: 8,
                        }}
                      >
                        <strong style={{ display: "block", marginBottom: 4, fontSize: "0.9rem", lineHeight: 1.4 }}>
                          {session.query}
                        </strong>
                        <div className="flex-between text-muted" style={{ fontSize: "0.78rem" }}>
                          <span>{session.query_type.replace(/_/g, " ")}</span>
                          <span title={new Date(session.generated_at).toLocaleString()}>
                            {relativeDate(session.generated_at)}
                          </span>
                        </div>
                      </button>
                      <div style={{ display: "flex", gap: 6 }}>
                        <button
                          className="btn-icon btn-icon-success"
                          style={{ flex: 1 }}
                          onClick={() => exportSession(session.session_id).catch(() => {})}
                          title="Export session as JSON"
                        >
                          ↓ Export
                        </button>
                        <button
                          className={`btn-icon btn-icon-danger`}
                          style={{ flex: 1 }}
                          disabled={deletingId === session.session_id}
                          onClick={() => handleSessionDelete(session.session_id)}
                          title="Delete session"
                        >
                          {deletingId === session.session_id ? "…" : "🗑 Delete"}
                        </button>
                      </div>
                    </div>
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
                <div style={{ fontSize: "3rem", marginBottom: 16 }}>🔬</div>
                <CardTitle style={{ color: "var(--muted)", marginBottom: 8 }}>Awaiting Execution</CardTitle>
                <p className="text-muted">Configure your query and click Execute Pipeline to start.</p>
              </div>
            </Card>
          )}

          {isRunning && !report && (
            <Card style={{ minHeight: "500px", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <div style={{ textAlign: "center", display: "flex", flexDirection: "column", alignItems: "center", gap: 20 }}>
                <svg className="animate-spin" width="56" height="56" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth="1.5">
                  <path d="M12 2v4m0 12v4M4.93 4.93l2.83 2.83m8.48 8.48l2.83 2.83M2 12h4m12 0h4M4.93 19.07l2.83-2.83m8.48-8.48l2.83-2.83" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                <div>
                  <CardTitle className="typing-cursor" style={{ marginBottom: 8 }}>Agents are active</CardTitle>
                  <p className="text-muted">Watch the timeline in the sidebar as each agent completes.</p>
                  {paperProgress && (
                    <p style={{ marginTop: 12, fontSize: "0.85rem", color: "var(--accent)" }}>
                      📄 Reading paper {paperProgress.index} of {paperProgress.total}
                    </p>
                  )}
                </div>
                {/* Flowing orbs for visual flair */}
                <div style={{ display: "flex", gap: 8 }}>
                  {[0, 1, 2, 3, 4].map((i) => (
                    <div
                      key={i}
                      style={{
                        width: 8,
                        height: 8,
                        borderRadius: "50%",
                        background: `hsl(${260 + i * 20}, 80%, 65%)`,
                        animation: `pulseGlow ${0.8 + i * 0.15}s ease-in-out infinite alternate`,
                        opacity: 0.7,
                      }}
                    />
                  ))}
                </div>
              </div>
            </Card>
          )}

          {report && (
            <ResultPanel report={report} onExport={handleExportReport} />
          )}
        </section>
      </div>
    </div>
  );
}
