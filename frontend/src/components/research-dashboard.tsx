"use client";

import { useEffect, useRef, useState } from "react";
import {
  deleteSession,
  exportSession,
  getSession,
  listSessions,
  analyzeDocument,
  uploadPdf,
} from "@/lib/api";
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
import { AgentTimeline } from "./dashboard/AgentTimeline";
import { ResultTabs } from "./dashboard/ResultTabs";
import { PdfDropzone } from "./dashboard/PdfDropzone";

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
  "contradiction_agent",
  "critic_agent",
  "builder_agent",
];

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

export function ResearchDashboard() {
  const [mode, setMode] = useState<"search" | "document">("search");
  const [docMethod, setDocMethod] = useState<"pdf" | "text">("pdf");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

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

  useEffect(() => {
    setIsLoadingSessions(true);
    listSessions()
      .then((data) => setSessions(data.sessions))
      .catch(() => {})
      .finally(() => setIsLoadingSessions(false));
  }, []);

  async function handleDocAnalysis(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (isRunning) return;

    if (docMethod === "pdf" && !selectedFile) {
      setError("Please select or drop a PDF file to analyze.");
      return;
    }
    if (docMethod === "text" && !docContent.trim()) {
      setError("Please paste the document content or abstract.");
      return;
    }

    setError(null);
    setReport(null);
    setAgents(makeInitialAgents().slice(1));
    setIsRunning(true);

    try {
      let result: ResearchResponse;
      if (docMethod === "pdf" && selectedFile) {
        result = await uploadPdf(selectedFile, docTitle || selectedFile.name);
      } else {
        result = await analyzeDocument(docTitle || "Uploaded Document", docContent);
      }
      setReport(result);
      setAgents((prev) =>
        prev.map((a) => ({
          ...a,
          status: "done",
          detail: "Processed uploaded content.",
        }))
      );
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
                : a
            )
          );
          if (agent === "reader_agent") setPaperProgress(null);
        },
        onAgentDone(agent, detail) {
          setAgents((prev) =>
            prev.map((a) =>
              a.agent === agent
                ? { ...a, status: "done", detail, finishedAt: Date.now() }
                : a
            )
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
          listSessions()
            .then((data) => setSessions(data.sessions))
            .catch(() => {});
        },
        onError(message) {
          setError(message);
          setIsRunning(false);
        },
      }
    );

    cleanupRef.current = cleanup;
  }

  useEffect(() => {
    return () => {
      cleanupRef.current?.();
    };
  }, []);

  function handleSessionOpen(sessionId: string) {
    setError(null);
    setReport(null);
    setAgents(makeInitialAgents());
    getSession(sessionId)
      .then(setReport)
      .catch((err) =>
        setError(err instanceof Error ? err.message : "Failed to load session.")
      );
  }

  async function handleSessionDelete(sessionId: string) {
    setDeletingId(sessionId);
    try {
      await deleteSession(sessionId);
      setSessions((prev) => prev.filter((s) => s.session_id !== sessionId));
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
    <div className="app-shell">
      {/* Fixed Brand Topbar */}
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
              <polygon points="12 2 2 7 12 12 22 7 12 2" />
              <polyline points="2 17 12 22 22 17" />
              <polyline points="2 12 12 17 22 12" />
            </svg>
          </div>
          <div>
            <span className="brand-name">MARA</span>
            <span className="brand-subtitle">RESEARCH SYSTEM</span>
          </div>
        </div>

        <div className="topbar-center">
          {sessions.length > 0 && (
            <select
              className="session-selector"
              value={report?.session_id || ""}
              onChange={(e) => e.target.value && handleSessionOpen(e.target.value)}
            >
              <option value="">📂 History ({sessions.length} sessions)</option>
              {sessions.map((s) => (
                <option key={s.session_id} value={s.session_id}>
                  {s.query.slice(0, 32)} — {relativeDate(s.generated_at)}
                </option>
              ))}
            </select>
          )}
        </div>

        <div className="topbar-actions">
          {report && (
            <button
              className="button button-secondary"
              onClick={handleExportReport}
              style={{ height: 36, padding: "0 14px", fontSize: 13 }}
            >
              ↓ Export Session
            </button>
          )}
        </div>
      </header>

      {/* Main Content Area */}
      <main className="main-content">
        {/* Hero Section */}
        <section className="hero">
          <div className="eyebrow">AUTONOMOUS MULTI-AGENT INTELLIGENCE</div>
          <h1 className="hero-title">
            Autonomous <span className="hero-title-accent">Research Synthesis</span>
          </h1>
          <p className="hero-description">
            Seven specialized agents discover literature, audit citations, identify contradictions, and construct PRISMA-compliant reviews in real-time.
          </p>

          <div className="query-panel">
            <div className="query-mode-switch">
              <button
                type="button"
                className={`query-mode-button ${mode === "search" ? "active" : ""}`}
                onClick={() => setMode("search")}
              >
                🔍 Discovery Search
              </button>
              <button
                type="button"
                className={`query-mode-button ${mode === "document" ? "active" : ""}`}
                onClick={() => setMode("document")}
              >
                📄 Document Deep-Dive
              </button>
            </div>

            <form onSubmit={handleSubmit}>
              {mode === "search" ? (
                <>
                  <div className="query-input-wrap">
                    <textarea
                      className="query-input"
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                      placeholder="What scientific topic, question, or hypothesis do you want to investigate?"
                    />
                  </div>

                  <div className="query-controls">
                    <select
                      className="control-select"
                      value={queryType}
                      onChange={(e) => setQueryType(e.target.value as QueryType)}
                    >
                      {QUERY_OPTIONS.map((opt) => (
                        <option key={opt.value} value={opt.value}>
                          {opt.label}
                        </option>
                      ))}
                    </select>

                    <input
                      className="control-select"
                      type="number"
                      min={1}
                      max={15}
                      value={maxResults}
                      onChange={(e) => setMaxResults(Number(e.target.value))}
                      style={{ width: 90 }}
                      title="Max Papers"
                    />

                    <button
                      type="submit"
                      disabled={isRunning}
                      className="button button-primary"
                      style={{ marginLeft: "auto" }}
                    >
                      {isRunning ? "Running Pipeline..." : "▶ Begin Research"}
                    </button>
                  </div>
                </>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                  <div style={{ display: "flex", gap: 8 }}>
                    <button
                      type="button"
                      className={`button ${docMethod === "pdf" ? "button-primary" : "button-secondary"}`}
                      style={{ flex: 1, height: 38, fontSize: 13 }}
                      onClick={() => setDocMethod("pdf")}
                    >
                      📎 Upload PDF / TXT
                    </button>
                    <button
                      type="button"
                      className={`button ${docMethod === "text" ? "button-primary" : "button-secondary"}`}
                      style={{ flex: 1, height: 38, fontSize: 13 }}
                      onClick={() => setDocMethod("text")}
                    >
                      ✍ Paste Text
                    </button>
                  </div>

                  <input
                    className="control-select"
                    style={{ width: "100%", background: "var(--bg-elevated)", height: 42, padding: "0 14px" }}
                    placeholder="Document Title (e.g. Attention Is All You Need)"
                    value={docTitle}
                    onChange={(e) => setDocTitle(e.target.value)}
                  />

                  {docMethod === "pdf" ? (
                    <PdfDropzone
                      selectedFile={selectedFile}
                      onFileSelect={setSelectedFile}
                      disabled={isRunning}
                    />
                  ) : (
                    <div className="query-input-wrap">
                      <textarea
                        className="query-input"
                        value={docContent}
                        onChange={(e) => setDocContent(e.target.value)}
                        placeholder="Paste document text, abstract, or excerpt here..."
                        style={{ minHeight: 140 }}
                      />
                    </div>
                  )}

                  <button
                    type="submit"
                    disabled={isRunning}
                    className="button button-primary"
                    style={{ alignSelf: "flex-end" }}
                  >
                    {isRunning ? "Analyzing..." : "▶ Analyze Document"}
                  </button>
                </div>
              )}
            </form>
          </div>
        </section>

        {/* Horizontal Agent Timeline Mesh */}
        {(isRunning || allDone || report) && (
          <AgentTimeline agents={agents} paperProgress={paperProgress} />
        )}

        {/* Error Alert */}
        {error && (
          <div
            className="card card-padding"
            style={{
              borderColor: "#dc2626",
              background: "rgba(220, 38, 38, 0.08)",
              marginTop: 24,
              color: "#dc2626",
              fontWeight: 500,
            }}
          >
            ⚠️ {error}
          </div>
        )}

        {/* Results Area */}
        <section className="results-section">
          {!report && !isRunning && (
            <div className="empty-state">
              <div>
                <div style={{ fontSize: "2.8rem", marginBottom: 12 }}>🔬</div>
                <h3 className="card-title" style={{ color: "var(--color-text-secondary)" }}>
                  Awaiting Autonomous Execution
                </h3>
                <p className="caption" style={{ marginTop: 6 }}>
                  Enter a research question above or load a past session from the topbar
                </p>
              </div>
            </div>
          )}

          {isRunning && !report && (
            <div className="card card-padding" style={{ textAlign: "center", padding: "64px 20px" }}>
              <div style={{ display: "inline-block", width: 44, height: 44, borderRadius: "50%", border: "3px solid var(--color-primary)", borderTopColor: "transparent", animation: "spin 1s linear infinite", marginBottom: 16 }} />
              <h3 className="card-title">Agents Are Collaborating</h3>
              <p className="caption" style={{ marginTop: 6 }}>
                Synthesizing literature, validating citations, and running analysis
              </p>
            </div>
          )}

          {report && (
            <ResultTabs report={report} onExport={handleExportReport} />
          )}
        </section>
      </main>
    </div>
  );
}
