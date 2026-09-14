"use client";

import { useState } from "react";
import type { ResearchResponse } from "@/lib/types";
import { AGENT_LABELS } from "@/lib/websocket";
import { Card, CardHeader, CardTitle, CardContent, Badge } from "../ui/Card";
import { exportBibtex, exportMarkdown } from "@/lib/api";
import { MermaidViewer } from "../ui/MermaidViewer";

const SOURCE_COLORS: Record<string, string> = {
  arXiv: "var(--color-primary)",
  "Semantic Scholar": "var(--color-accent)",
  Web: "var(--color-primary)",
  Upload: "var(--color-accent)",
};

export type Tab =
  | "overview"
  | "papers"
  | "analysis"
  | "tensions"
  | "graph"
  | "prisma"
  | "innovations"
  | "critique"
  | "plan"
  | "architecture";

interface ResultTabsProps {
  report: ResearchResponse;
  onExport: () => void;
}

export function ResultTabs({ report, onExport }: ResultTabsProps) {
  const [tab, setTab] = useState<Tab>("overview");
  const [exporting, setExporting] = useState(false);
  const [exportingBibtex, setExportingBibtex] = useState(false);
  const [exportingMd, setExportingMd] = useState(false);

  const tabs: { id: Tab; label: string }[] = [
    { id: "overview", label: "Overview" },
    { id: "papers", label: `Papers (${report.papers.length})` },
    { id: "analysis", label: "Analysis" },
    {
      id: "tensions",
      label: `Contradictions (${report.contradiction_matrix?.tensions?.length ?? 0})`,
    },
    { id: "graph", label: "Evidence Graph" },
    { id: "prisma", label: "PRISMA Audit" },
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

  async function handleExportBibtex() {
    if (!report.session_id) return;
    setExportingBibtex(true);
    try {
      await exportBibtex(report.session_id);
    } finally {
      setExportingBibtex(false);
    }
  }

  async function handleExportMarkdown() {
    if (!report.session_id) return;
    setExportingMd(true);
    try {
      await exportMarkdown(report.session_id);
    } finally {
      setExportingMd(false);
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      {/* Header with academic export toolbar */}
      <div className="flex-between" style={{ flexWrap: "wrap", gap: 12 }}>
        <div style={{ fontSize: "0.85rem", color: "var(--muted)" }}>
          Session:{" "}
          <code style={{ color: "var(--accent)", fontSize: "0.8rem" }}>
            {report.session_id?.slice(0, 8) ?? "—"}
          </code>
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <button
            className={`btn-icon ${!exporting ? "btn-icon-success" : ""}`}
            onClick={handleExport}
            disabled={exporting || !report.session_id}
            title="Download full raw JSON"
          >
            {exporting ? "↓ Exporting…" : "↓ JSON"}
          </button>
          <button
            className={`btn-icon ${!exportingBibtex ? "btn-icon-success" : ""}`}
            onClick={handleExportBibtex}
            disabled={exportingBibtex || !report.session_id}
            title="Download BibTeX citation entries (.bib)"
          >
            {exportingBibtex ? "↓ Exporting…" : "↓ BibTeX (.bib)"}
          </button>
          <button
            className={`btn-icon ${!exportingMd ? "btn-icon-success" : ""}`}
            onClick={handleExportMarkdown}
            disabled={exportingMd || !report.session_id}
            title="Download Systematic Literature Review report (.md)"
          >
            {exportingMd ? "↓ Exporting…" : "↓ Review (.md)"}
          </button>
        </div>
      </div>


      {/* Tab navigation bar */}
      <div className="result-tabs-scroll">
        <div className="result-tabs">
          {tabs.map((t) => {
            const TAB_COLORS: Record<string, string> = {
              overview: "var(--color-primary)",
              papers: "var(--color-accent)",
              analysis: "var(--color-primary)",
              tensions: "var(--color-accent)",
              graph: "var(--color-primary)",
              prisma: "var(--color-accent)",
              innovations: "var(--color-primary)",
              critique: "var(--color-accent)",
              plan: "var(--color-primary)",
              architecture: "var(--color-accent)",
            };
            const tabColor = TAB_COLORS[t.id] || "var(--color-primary)";

            return (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className={`result-tab ${tab === t.id ? "active" : ""}`}
                style={{ "--tab-color": tabColor } as React.CSSProperties}
              >
                {t.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Tab content */}
      <div className="animate-fade-in" key={tab}>
        {tab === "overview" && (
          <Card>
            <CardHeader>
              <div className="flex-between">
                <CardTitle>Research Overview</CardTitle>
                <Badge variant="accent">
                  {report.query_type?.toString().replace(/_/g, " ")}
                </Badge>
              </div>
            </CardHeader>
            <CardContent>
              <p
                style={{
                  fontSize: "1.05rem",
                  lineHeight: 1.8,
                  marginBottom: 20,
                }}
              >
                {report.summary}
              </p>
              <div className="flex-row" style={{ flexWrap: "wrap", gap: 10 }}>
                <Badge>{report.papers.length} Papers</Badge>
                <Badge>{report.reader_outputs.length} Read</Badge>
                {report.critique && (
                  <Badge
                    variant={
                      report.critique.overall_confidence > 0.8
                        ? "default"
                        : "accent"
                    }
                  >
                    {Math.round(report.critique.overall_confidence * 100)}%
                    Confidence
                  </Badge>
                )}
                {report.critique?.review_mode && (
                  <Badge>Mode: {report.critique.review_mode}</Badge>
                )}
              </div>

              {/* Execution trace */}
              {report.execution_trace.length > 0 && (
                <div style={{ marginTop: 24 }}>
                  <strong
                    style={{
                      fontSize: "0.85rem",
                      color: "var(--muted)",
                      textTransform: "uppercase",
                      letterSpacing: "0.05em",
                    }}
                  >
                    Execution Trace
                  </strong>
                  <div
                    style={{
                      marginTop: 10,
                      display: "flex",
                      flexDirection: "column",
                      gap: 8,
                    }}
                  >
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
                        <span style={{ fontWeight: 600 }}>
                          {AGENT_LABELS[step.agent_name] ?? step.agent_name}
                        </span>
                        <span style={{ color: "var(--muted)" }}>
                          {step.detail}
                        </span>
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
            {report.papers.length === 0 ? (
              <Card>
                <CardContent style={{ paddingTop: 24, textAlign: "center" }}>
                  <p className="text-muted">
                    No external papers discovered (Document Ingestion Mode).
                  </p>
                </CardContent>
              </Card>
            ) : (
              report.papers.map((paper) => (
                <Card key={paper.external_id}>
                  <CardContent style={{ paddingTop: 16 }}>
                    <div
                      className="flex-between"
                      style={{ alignItems: "flex-start", gap: 12 }}
                    >
                      <strong style={{ fontSize: "1.05rem", lineHeight: 1.4 }}>
                        {paper.title}
                      </strong>
                      <div style={{ display: "flex", gap: 6, flexShrink: 0 }}>
                        <Badge variant="accent">{paper.relevance_score}</Badge>
                        <span
                          style={{
                            fontSize: "0.75rem",
                            fontWeight: 700,
                            color:
                              SOURCE_COLORS[paper.source] ?? "var(--muted)",
                            padding: "2px 8px",
                            borderRadius: 999,
                            border: `1px solid ${
                              SOURCE_COLORS[paper.source] ?? "var(--border)"
                            }22`,
                            background: `${
                              SOURCE_COLORS[paper.source] ?? "var(--muted)"
                            }18`,
                            alignSelf: "flex-start",
                          }}
                        >
                          {paper.source}
                        </span>
                      </div>
                    </div>
                    <p
                      style={{
                        fontSize: "0.85rem",
                        color: "var(--muted)",
                        marginTop: 4,
                      }}
                    >
                      {paper.authors.join(", ")}
                    </p>
                    <p
                      style={{
                        fontSize: "0.9rem",
                        marginTop: 10,
                        lineHeight: 1.6,
                        color: "var(--text)",
                      }}
                    >
                      {paper.abstract}
                    </p>
                  </CardContent>
                </Card>
              ))
            )}
          </div>
        )}

        {tab === "analysis" && report.analysis && (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <Card>
              <CardHeader>
                <CardTitle>Key Research Themes</CardTitle>
              </CardHeader>
              <CardContent>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                  {report.analysis.themes.map((t, i) => (
                    <span
                      key={i}
                      style={{
                        padding: "6px 14px",
                        background: "rgba(97, 45, 83, 0.08)",
                        color: "var(--color-primary)",
                        borderRadius: 999,
                        fontSize: "0.85rem",
                        border: "1px solid rgba(97, 45, 83, 0.25)",
                      }}
                    >
                      {t}
                    </span>
                  ))}
                </div>
              </CardContent>
            </Card>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: 16,
              }}
            >
              <Card>
                <CardHeader>
                  <CardTitle>Consensus</CardTitle>
                </CardHeader>
                <CardContent>
                  <ul
                    style={{
                      paddingLeft: 18,
                      display: "flex",
                      flexDirection: "column",
                      gap: 8,
                    }}
                  >
                    {report.analysis.consensus.map((c, i) => (
                      <li
                        key={i}
                        style={{
                          fontSize: "0.9rem",
                          color: "var(--text)",
                          lineHeight: 1.6,
                        }}
                      >
                        {c}
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
              <Card>
                <CardHeader>
                  <CardTitle>Research Gaps</CardTitle>
                </CardHeader>
                <CardContent>
                  <ul
                    style={{
                      paddingLeft: 18,
                      display: "flex",
                      flexDirection: "column",
                      gap: 8,
                    }}
                  >
                    {report.analysis.gaps.map((g, i) => (
                      <li
                        key={i}
                        style={{
                          fontSize: "0.9rem",
                          color: "var(--text)",
                          lineHeight: 1.6,
                        }}
                      >
                        {g}
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            </div>

            {report.analysis.practical_applications.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle>Practical Applications</CardTitle>
                </CardHeader>
                <CardContent>
                  <ul
                    style={{
                      paddingLeft: 18,
                      display: "flex",
                      flexDirection: "column",
                      gap: 8,
                    }}
                  >
                    {report.analysis.practical_applications.map((a, i) => (
                      <li key={i} style={{ fontSize: "0.9rem", lineHeight: 1.6 }}>
                        {a}
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            )}
          </div>
        )}

        {tab === "tensions" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
                gap: 12,
              }}
            >
              <Card>
                <CardContent style={{ padding: 16 }}>
                  <div style={{ fontSize: "0.75rem", color: "var(--muted)", textTransform: "uppercase", fontWeight: 700 }}>
                    Pairs Evaluated
                  </div>
                  <div style={{ fontSize: "1.6rem", fontWeight: 800, marginTop: 4, color: "var(--foreground)" }}>
                    {report.contradiction_matrix?.total_pairs_checked ?? 0}
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent style={{ padding: 16 }}>
                  <div style={{ fontSize: "0.75rem", color: "var(--muted)", textTransform: "uppercase", fontWeight: 700 }}>
                    Tensions Detected
                  </div>
                  <div style={{ fontSize: "1.6rem", fontWeight: 800, marginTop: 4, color: "var(--color-primary)" }}>
                    {report.contradiction_matrix?.tensions?.length ?? 0}
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent style={{ padding: 16 }}>
                  <div style={{ fontSize: "0.75rem", color: "var(--muted)", textTransform: "uppercase", fontWeight: 700 }}>
                    Matrix Tension Density
                  </div>
                  <div style={{ fontSize: "1.6rem", fontWeight: 800, marginTop: 4, color: "var(--color-accent)" }}>
                    {report.contradiction_matrix ? `${Math.round(report.contradiction_matrix.matrix_density * 100)}%` : "0%"}
                  </div>
                </CardContent>
              </Card>

              {report.contradiction_matrix?.most_controversial_paper && (
                <Card>
                  <CardContent style={{ padding: 16 }}>
                    <div style={{ fontSize: "0.75rem", color: "var(--muted)", textTransform: "uppercase", fontWeight: 700 }}>
                      Highest Tension Paper
                    </div>
                    <div style={{ fontSize: "0.88rem", fontWeight: 700, marginTop: 6, color: "var(--accent)", lineHeight: 1.4 }} title={report.contradiction_matrix.most_controversial_paper}>
                      {report.contradiction_matrix.most_controversial_paper.slice(0, 45)}
                      {report.contradiction_matrix.most_controversial_paper.length > 45 ? "…" : ""}
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>

            {report.contradiction_matrix?.key_open_debates && report.contradiction_matrix.key_open_debates.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle>⚖️ Key Open Scientific Debates</CardTitle>
                </CardHeader>
                <CardContent>
                  <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                    {report.contradiction_matrix.key_open_debates.map((debate, i) => (
                      <div
                        key={i}
                        style={{
                          padding: 12,
                          background: "var(--surface-strong)",
                          borderRadius: "var(--radius-md)",
                          borderLeft: "4px solid var(--color-primary)",
                          fontSize: "0.88rem",
                          lineHeight: 1.5,
                        }}
                      >
                        {debate}
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            <Card>
              <CardHeader>
                <CardTitle>⚡ Pairwise Contradiction Matrix</CardTitle>
              </CardHeader>
              <CardContent>
                {report.contradiction_matrix?.tensions && report.contradiction_matrix.tensions.length > 0 ? (
                  <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                    {report.contradiction_matrix.tensions.map((pair, idx) => {
                      const severityColors: Record<string, { bg: string; text: string; border: string }> = {
                        direct_empirical: { bg: "rgba(97, 45, 83, 0.15)", text: "var(--color-primary)", border: "var(--color-primary)" },
                        methodological_disagreement: { bg: "rgba(133, 57, 83, 0.15)", text: "var(--color-accent)", border: "var(--color-accent)" },
                        qualitative_conflict: { bg: "rgba(133, 57, 83, 0.1)", text: "var(--color-accent)", border: "var(--color-accent)" },
                        limitation_collision: { bg: "rgba(44, 44, 44, 0.1)", text: "var(--color-text-primary)", border: "var(--color-border)" },
                      };
                      const color = severityColors[pair.severity] || severityColors.direct_empirical;
                      return (
                        <div
                          key={idx}
                          style={{
                            padding: 18,
                            background: "var(--surface-strong)",
                            borderRadius: "var(--radius-md)",
                            border: `1px solid var(--border)`,
                            borderLeft: `4px solid ${color.border}`,
                            display: "flex",
                            flexDirection: "column",
                            gap: 12,
                          }}
                        >
                          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 8 }}>
                            <span style={{ fontWeight: 700, fontSize: "0.95rem" }}>
                              {pair.topic}
                            </span>
                            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                              <span
                                style={{
                                  fontSize: "0.75rem",
                                  padding: "3px 8px",
                                  borderRadius: 999,
                                  background: color.bg,
                                  color: color.text,
                                  fontWeight: 700,
                                  textTransform: "uppercase",
                                }}
                              >
                                {pair.severity.replace("_", " ")}
                              </span>
                              <span style={{ fontSize: "0.78rem", color: "var(--muted)", fontWeight: 600 }}>
                                Confidence: {Math.round(pair.confidence * 100)}%
                              </span>
                            </div>
                          </div>

                          <div
                            style={{
                              display: "grid",
                              gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
                              gap: 12,
                            }}
                          >
                            <div style={{ padding: 12, background: "rgba(44, 44, 44, 0.04)", borderRadius: "var(--radius-sm)", border: "1px solid var(--border)" }}>
                              <div style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--color-primary)", marginBottom: 4 }}>
                                Paper A: {pair.paper_a}
                              </div>
                              <div style={{ fontSize: "0.85rem", lineHeight: 1.5 }}>
                                {pair.claim_a}
                              </div>
                            </div>

                            <div style={{ padding: 12, background: "rgba(44, 44, 44, 0.04)", borderRadius: "var(--radius-sm)", border: "1px solid var(--border)" }}>
                              <div style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--color-accent)", marginBottom: 4 }}>
                                Paper B: {pair.paper_b}
                              </div>
                              <div style={{ fontSize: "0.85rem", lineHeight: 1.5 }}>
                                {pair.claim_b}
                              </div>
                            </div>
                          </div>

                          <div style={{ fontSize: "0.84rem", lineHeight: 1.5, background: "rgba(44, 44, 44, 0.03)", padding: 10, borderRadius: "var(--radius-sm)" }}>
                            <div>
                              <strong style={{ color: "var(--color-primary)" }}>Root Cause: </strong>
                              {pair.root_cause}
                            </div>
                            <div style={{ marginTop: 4 }}>
                              <strong style={{ color: "var(--color-accent)" }}>Resolution Hypothesis: </strong>
                              {pair.resolution_hypothesis}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div style={{ padding: 24, textAlign: "center", color: "var(--muted)" }}>
                    No significant empirical or methodological contradictions detected across the ingested papers.
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        )}

        {tab === "graph" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
                gap: 12,
              }}
            >
              <Card>
                <CardContent style={{ padding: 16 }}>
                  <div style={{ fontSize: "0.75rem", color: "var(--muted)", textTransform: "uppercase", fontWeight: 700 }}>
                    Graph Entities
                  </div>
                  <div style={{ fontSize: "1.6rem", fontWeight: 800, marginTop: 4, color: "var(--accent)" }}>
                    {report.evidence_graph?.nodes?.length ?? 0}
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent style={{ padding: 16 }}>
                  <div style={{ fontSize: "0.75rem", color: "var(--muted)", textTransform: "uppercase", fontWeight: 700 }}>
                    Relational Edges
                  </div>
                  <div style={{ fontSize: "1.6rem", fontWeight: 800, marginTop: 4, color: "var(--color-primary)" }}>
                    {report.evidence_graph?.edges?.length ?? 0}
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent style={{ padding: 16 }}>
                  <div style={{ fontSize: "0.75rem", color: "var(--muted)", textTransform: "uppercase", fontWeight: 700 }}>
                    Central Concepts
                  </div>
                  <div style={{ fontSize: "0.85rem", fontWeight: 600, marginTop: 6, color: "var(--foreground)" }}>
                    {report.evidence_graph?.central_concepts?.slice(0, 3).join(", ") || "None"}
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Mermaid Concept Graph */}
            <Card>
              <CardHeader>
                <CardTitle>🕸️ Multi-Paper Evidence & Concept Graph</CardTitle>
              </CardHeader>
              <CardContent>
                <MermaidViewer
                  chart={report.evidence_graph?.mermaid_diagram || "graph LR\n  A[No Evidence Graph Generated]"}
                />
              </CardContent>
            </Card>

            {/* Relational Edge Feed */}
            <Card>
              <CardHeader>
                <CardTitle>🔗 Extracted Entity Relationships</CardTitle>
              </CardHeader>
              <CardContent>
                {report.evidence_graph?.edges && report.evidence_graph.edges.length > 0 ? (
                  <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                    {report.evidence_graph.edges.slice(0, 20).map((edge, i) => (
                      <div
                        key={i}
                        style={{
                          padding: 12,
                          background: "var(--surface-strong)",
                          borderRadius: "var(--radius-md)",
                          border: "1px solid var(--border)",
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "center",
                          fontSize: "0.85rem",
                          flexWrap: "wrap",
                          gap: 8,
                        }}
                      >
                        <div>
                          <span style={{ fontWeight: 700, color: "var(--color-primary)" }}>{edge.source}</span>
                          <span style={{ margin: "0 8px", color: "var(--muted)" }}>→</span>
                          <span style={{ fontWeight: 700, color: "var(--color-accent)" }}>{edge.target}</span>
                        </div>
                        <span
                          style={{
                            fontSize: "0.75rem",
                            padding: "3px 8px",
                            borderRadius: 999,
                            background: edge.relation === "contradicts" ? "rgba(220,38,38,0.12)" : "rgba(44,44,44,0.06)",
                            color: edge.relation === "contradicts" ? "#dc2626" : "var(--muted)",
                            fontWeight: 600,
                          }}
                        >
                          {edge.label}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div style={{ padding: 20, textAlign: "center", color: "var(--muted)" }}>
                    No relational edges extracted.
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        )}

        {tab === "prisma" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            {/* Summary metrics */}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
                gap: 12,
              }}
            >
              <Card>
                <CardContent style={{ padding: 16 }}>
                  <div style={{ fontSize: "0.75rem", color: "var(--muted)", textTransform: "uppercase", fontWeight: 700 }}>
                    1. Identified
                  </div>
                  <div style={{ fontSize: "1.6rem", fontWeight: 800, marginTop: 4, color: "var(--accent)" }}>
                    {report.prisma_flow?.total_identified ?? 0}
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent style={{ padding: 16 }}>
                  <div style={{ fontSize: "0.75rem", color: "var(--muted)", textTransform: "uppercase", fontWeight: 700 }}>
                    2. Duplicates Removed
                  </div>
                  <div style={{ fontSize: "1.6rem", fontWeight: 800, marginTop: 4, color: "var(--color-accent)" }}>
                    {report.prisma_flow?.duplicates_removed ?? 0}
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent style={{ padding: 16 }}>
                  <div style={{ fontSize: "0.75rem", color: "var(--muted)", textTransform: "uppercase", fontWeight: 700 }}>
                    3. Screened
                  </div>
                  <div style={{ fontSize: "1.6rem", fontWeight: 800, marginTop: 4, color: "var(--foreground)" }}>
                    {report.prisma_flow?.records_screened ?? 0}
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent style={{ padding: 16 }}>
                  <div style={{ fontSize: "0.75rem", color: "var(--muted)", textTransform: "uppercase", fontWeight: 700 }}>
                    4. Included in Synthesis
                  </div>
                  <div style={{ fontSize: "1.6rem", fontWeight: 800, marginTop: 4, color: "var(--color-primary)" }}>
                    {report.prisma_flow?.studies_included ?? 0}
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* PRISMA Mermaid Flowchart */}
            <Card>
              <CardHeader>
                <CardTitle>📋 PRISMA 2020 Systematic Flowchart</CardTitle>
              </CardHeader>
              <CardContent>
                <MermaidViewer
                  chart={report.prisma_flow?.mermaid_flowchart || "graph TD\n  A[No PRISMA Flowchart Available]"}
                />
              </CardContent>
            </Card>

            {/* PRISMA Screening Audit Trail */}
            <Card>
              <CardHeader>
                <CardTitle>🔍 Paper Screening & Eligibility Audit Trail</CardTitle>
              </CardHeader>
              <CardContent>
                {report.prisma_flow?.audit_trail && report.prisma_flow.audit_trail.length > 0 ? (
                  <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                    {report.prisma_flow.audit_trail.map((item, idx) => (
                      <div
                        key={idx}
                        style={{
                          padding: 14,
                          background: "var(--surface-strong)",
                          borderRadius: "var(--radius-md)",
                          border: "1px solid var(--border)",
                          display: "flex",
                          flexDirection: "column",
                          gap: 6,
                        }}
                      >
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 8 }}>
                          <span style={{ fontWeight: 700, fontSize: "0.9rem" }}>{item.paper_title}</span>
                          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                            <span
                              style={{
                                fontSize: "0.72rem",
                                padding: "2px 8px",
                                borderRadius: 999,
                                background: item.status === "included" ? "rgba(22, 163, 74, 0.12)" : "rgba(220, 38, 38, 0.12)",
                                color: item.status === "included" ? "#15803d" : "#dc2626",
                                fontWeight: 700,
                                textTransform: "uppercase",
                              }}
                            >
                              {item.status}
                            </span>
                            <span style={{ fontSize: "0.75rem", color: "var(--muted)" }}>
                              Relevance: {item.relevance_score}%
                            </span>
                          </div>
                        </div>
                        <div style={{ fontSize: "0.82rem", color: "var(--muted)", lineHeight: 1.4 }}>
                          <strong>Evaluation: </strong>
                          {item.reason}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div style={{ padding: 20, textAlign: "center", color: "var(--muted)" }}>
                    No audit records available.
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        )}

        {tab === "innovations" && report.analysis && (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            {report.analysis.innovations.length > 0 ? (
              <>
                <Card>
                  <CardHeader>
                    <CardTitle>🔬 Paper Innovations</CardTitle>
                  </CardHeader>
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
                          <p
                            style={{
                              fontSize: "0.8rem",
                              color: "var(--accent)",
                              fontWeight: 700,
                              marginBottom: 6,
                              textTransform: "uppercase",
                              letterSpacing: "0.04em",
                            }}
                          >
                            {inn.paper_title.slice(0, 50)}
                            {inn.paper_title.length > 50 ? "…" : ""}
                          </p>
                          <p
                            style={{
                              fontSize: "0.9rem",
                              lineHeight: 1.6,
                              marginBottom: 8,
                            }}
                          >
                            {inn.innovation}
                          </p>
                          <p
                            style={{
                              fontSize: "0.82rem",
                              color: "var(--color-primary)",
                              lineHeight: 1.5,
                            }}
                          >
                            <strong>Impact: </strong>
                            {inn.impact}
                          </p>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>

                {report.analysis.conflicts.length > 0 && (
                  <Card>
                    <CardHeader>
                      <CardTitle>⚡ Conflicting Evidence</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div
                        style={{
                          display: "flex",
                          flexDirection: "column",
                          gap: 10,
                        }}
                      >
                        {report.analysis.conflicts.map((conflict, i) => (
                          <div
                            key={i}
                            style={{
                              padding: 12,
                              background: "rgba(133, 57, 83, 0.06)",
                              border: "1px solid rgba(133, 57, 83, 0.25)",
                              borderRadius: "var(--radius-sm)",
                            }}
                          >
                            <p style={{ fontWeight: 600, marginBottom: 4 }}>
                              {conflict.topic}
                            </p>
                            <p
                              style={{
                                fontSize: "0.88rem",
                                color: "var(--muted)",
                              }}
                            >
                              {conflict.description}
                            </p>
                            {conflict.papers.length > 0 && (
                              <div
                                style={{
                                  marginTop: 8,
                                  display: "flex",
                                  flexWrap: "wrap",
                                  gap: 4,
                                }}
                              >
                                {conflict.papers.map((p, j) => (
                                  <span
                                    key={j}
                                    style={{
                                      fontSize: "0.75rem",
                                      padding: "2px 8px",
                                      background: "rgba(97, 45, 83, 0.08)",
                                      color: "var(--color-primary)",
                                      borderRadius: 999,
                                      border: "1px solid rgba(97, 45, 83, 0.2)",
                                    }}
                                  >
                                    {p.slice(0, 30)}
                                    {p.length > 30 ? "…" : ""}
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
                  <p className="text-muted">
                    No innovation summaries were extracted for this query.
                  </p>
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
                    <Badge
                      variant={
                        report.critique.overall_confidence > 0.8
                          ? "default"
                          : "accent"
                      }
                    >
                      {Math.round(report.critique.overall_confidence * 100)}%
                      Confidence
                    </Badge>
                  </div>
                </div>
              </CardHeader>
              {report.critique.llm_summary && (
                <CardContent>
                  <p
                    style={{
                      fontStyle: "italic",
                      color: "var(--muted)",
                      lineHeight: 1.7,
                      padding: "12px 16px",
                      background: "var(--surface-strong)",
                      borderRadius: "var(--radius-sm)",
                      borderLeft: "3px solid var(--accent)",
                    }}
                  >
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
                    <Badge
                      variant={c.severity === "high" ? "accent" : "default"}
                    >
                      {c.severity}
                    </Badge>
                  </div>
                  <p style={{ fontWeight: 600, marginBottom: 6 }}>{c.issue}</p>
                  <p
                    style={{
                      fontSize: "0.88rem",
                      color: "var(--muted)",
                      marginBottom: 6,
                    }}
                  >
                    <strong>Evidence:</strong> {c.evidence}
                  </p>
                  <p
                    style={{
                      fontSize: "0.88rem",
                      color: "var(--muted)",
                    }}
                  >
                    <strong>Impact:</strong> {c.impact}
                  </p>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {tab === "plan" && report.implementation_plan && (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <Card style={{ border: "1px solid rgba(97, 45, 83, 0.35)", background: "var(--color-surface-elevated)" }}>
              <CardHeader>
                <CardTitle style={{ color: "var(--color-primary)" }}>Project Idea</CardTitle>
              </CardHeader>
              <CardContent>
                <p style={{ fontSize: "1.1rem", lineHeight: 1.7 }}>
                  {report.implementation_plan.project_idea}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Value Proposition</CardTitle>
              </CardHeader>
              <CardContent>
                <p style={{ lineHeight: 1.7 }}>
                  {report.implementation_plan.value_proposition}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>MVP Roadmap</CardTitle>
              </CardHeader>
              <CardContent>
                <div
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    gap: 12,
                  }}
                >
                  {report.implementation_plan?.mvp_roadmap.map((phase, pi) => (
                    <div
                      key={pi}
                      style={{
                        padding: 14,
                        background: "var(--surface-strong)",
                        borderRadius: "var(--radius-md)",
                        border: "1px solid var(--border)",
                      }}
                    >
                      <div className="flex-between" style={{ marginBottom: 8 }}>
                        <strong style={{ color: "var(--accent-secondary)" }}>
                          {phase.name}
                        </strong>
                        <span
                          style={{ fontSize: "0.82rem", color: "var(--muted)" }}
                        >
                          {phase.duration}
                        </span>
                      </div>
                      <ul
                        style={{
                          paddingLeft: 18,
                          margin: 0,
                          display: "flex",
                          flexDirection: "column",
                          gap: 4,
                        }}
                      >
                        {phase.goals.map((g, gi) => (
                          <li
                            key={gi}
                            style={{ fontSize: "0.88rem", lineHeight: 1.6 }}
                          >
                            {g}
                          </li>
                        ))}
                      </ul>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Challenges &amp; Mitigations</CardTitle>
              </CardHeader>
              <CardContent>
                <div
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    gap: 10,
                  }}
                >
                  {report.implementation_plan?.challenges.map((ch, ci) => (
                    <div
                      key={ci}
                      style={{
                        padding: 12,
                        background: "rgba(239,68,68,0.08)",
                        borderRadius: "var(--radius-sm)",
                        border: "1px solid rgba(239,68,68,0.2)",
                      }}
                    >
                      <p
                        style={{
                          fontWeight: 600,
                          marginBottom: 4,
                          fontSize: "0.9rem",
                        }}
                      >
                        ⚠ {ch.challenge}
                      </p>
                      <p
                        style={{ fontSize: "0.88rem", color: "var(--muted)" }}
                      >
                        {ch.mitigation}
                      </p>
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
              <CardHeader>
                <CardTitle>🏗 System Architecture</CardTitle>
              </CardHeader>
              <CardContent>
                <p
                  style={{
                    lineHeight: 1.7,
                    marginBottom: 20,
                    borderLeft: "3px solid var(--accent)",
                    paddingLeft: 14,
                    color: "var(--muted)",
                    fontStyle: "italic",
                  }}
                >
                  {report.implementation_plan?.architecture.summary}
                </p>
                <strong
                  style={{
                    fontSize: "0.85rem",
                    color: "var(--muted)",
                    textTransform: "uppercase",
                    letterSpacing: "0.05em",
                  }}
                >
                  Components
                </strong>
                <div
                  style={{
                    marginTop: 10,
                    display: "flex",
                    flexDirection: "column",
                    gap: 8,
                  }}
                >
                  {report.implementation_plan?.architecture.components.map(
                    (comp, i) => (
                      <div
                        key={i}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 10,
                          padding: "10px 14px",
                          background: "var(--surface-strong)",
                          borderRadius: "var(--radius-sm)",
                          border: "1px solid var(--border)",
                        }}
                      >
                        <span
                          style={{ color: "var(--accent)", fontSize: "1rem" }}
                        >
                          ⬡
                        </span>
                        <span style={{ fontSize: "0.9rem" }}>{comp}</span>
                      </div>
                    ),
                  )}
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>🔄 Data Flow</CardTitle>
              </CardHeader>
              <CardContent>
                <div
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    gap: 0,
                  }}
                >
                  {report.implementation_plan?.architecture.data_flow.map(
                    (step, i) => (
                      <div
                        key={i}
                        style={{
                          display: "flex",
                          gap: 14,
                          alignItems: "flex-start",
                        }}
                      >
                        <div
                          style={{
                            display: "flex",
                            flexDirection: "column",
                            alignItems: "center",
                            flexShrink: 0,
                          }}
                        >
                          <div
                            style={{
                              width: 28,
                              height: 28,
                              borderRadius: "50%",
                              background: "rgba(97, 45, 83, 0.1)",
                              border: "1px solid rgba(97, 45, 83, 0.3)",
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "center",
                              fontSize: "0.75rem",
                              fontWeight: 700,
                              color: "var(--color-primary)",
                            }}
                          >
                            {i + 1}
                          </div>
                          {i <
                            (report.implementation_plan?.architecture.data_flow
                              .length || 0) -
                              1 && (
                            <div
                              style={{
                                width: 2,
                                height: 24,
                                background: "rgba(97, 45, 83, 0.25)",
                                margin: "2px 0",
                              }}
                            />
                          )}
                        </div>
                        <p style={{ fontSize: "0.9rem", lineHeight: 1.6, paddingTop: 4 }}>
                          {step}
                        </p>
                      </div>
                    ),
                  )}
                </div>
              </CardContent>
            </Card>
            {/* Data Requirements */}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: 16,
              }}
            >
              <Card>
                <CardHeader>
                  <CardTitle>📦 Datasets</CardTitle>
                </CardHeader>
                <CardContent>
                  <ul
                    style={{
                      paddingLeft: 18,
                      display: "flex",
                      flexDirection: "column",
                      gap: 6,
                    }}
                  >
                    {report.implementation_plan?.data_requirements.datasets.map(
                      (d, i) => (
                        <li key={i} style={{ fontSize: "0.88rem" }}>
                          {d}
                        </li>
                      ),
                    )}
                  </ul>
                </CardContent>
              </Card>
              <Card>
                <CardHeader>
                  <CardTitle>🔒 Privacy</CardTitle>
                </CardHeader>
                <CardContent>
                  <ul
                    style={{
                      paddingLeft: 18,
                      display: "flex",
                      flexDirection: "column",
                      gap: 6,
                    }}
                  >
                    {report.implementation_plan?.data_requirements.privacy_considerations.map(
                      (p, i) => (
                        <li key={i} style={{ fontSize: "0.88rem" }}>
                          {p}
                        </li>
                      ),
                    )}
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
