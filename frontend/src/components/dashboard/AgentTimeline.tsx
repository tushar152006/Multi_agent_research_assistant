"use client";

import type { AgentEvent } from "@/lib/websocket";
import type { PaperProgress } from "@/lib/types";

interface AgentTimelineProps {
  agents: AgentEvent[];
  paperProgress: PaperProgress | null;
}

const AGENT_COLORS: Record<string, string> = {
  research_agent: "var(--color-primary)",
  reader_agent: "var(--color-accent)",
  citation_auditor: "var(--color-primary)",
  contradiction_agent: "var(--color-accent)",
  analyst_agent: "var(--color-primary)",
  critic_agent: "var(--color-accent)",
  builder_agent: "var(--color-primary)",
};

const AGENT_ICONS: Record<string, string> = {
  research_agent: "🔍",
  reader_agent: "📖",
  citation_auditor: "🛡️",
  contradiction_agent: "⚡",
  analyst_agent: "🔮",
  critic_agent: "⚖️",
  builder_agent: "🛠️",
};

export function AgentTimeline({ agents, paperProgress }: AgentTimelineProps) {
  return (
    <div className="timeline-section" style={{ marginTop: 24 }}>
      <div className="section-kicker">COLLABORATIVE AGENT MESH</div>
      <div className="agent-timeline-scroll">
        <div className="agent-timeline">
          {agents.map((a, i) => {
            const isIdle = a.status === "idle";
            const isRunning = a.status === "running";
            const isDone = a.status === "done";
            const agentColor = AGENT_COLORS[a.agent] || "var(--color-primary)";
            const icon = AGENT_ICONS[a.agent] || "🤖";

            return (
              <div key={a.agent} className="agent-step">
                <div className="agent-node-column">
                  <div
                    className={`agent-node ${isRunning ? "running" : ""} ${isDone ? "done" : ""}`}
                    style={{ "--agent-color": agentColor } as React.CSSProperties}
                  >
                    {isDone ? (
                      <span className="agent-check" style={{ fontSize: 18 }}>✓</span>
                    ) : (
                      <span style={{ fontSize: 18 }}>{icon}</span>
                    )}
                  </div>
                  <span className="agent-label">{a.label}</span>
                  <span className="agent-status" style={{ color: isRunning ? agentColor : undefined }}>
                    {isRunning ? "RUNNING" : isDone ? "COMPLETE" : "WAITING"}
                  </span>
                </div>

                {i < agents.length - 1 && (
                  <div
                    className={`agent-connector ${isDone ? "done" : ""} ${isRunning ? "running" : ""}`}
                    style={{ "--agent-color": agentColor } as React.CSSProperties}
                  />
                )}
              </div>
            );
          })}
        </div>
      </div>

      {paperProgress && (
        <div className="paper-progress card" style={{ marginTop: 16, padding: "12px 16px" }}>
          <div className="paper-progress-header">
            <span>Reading Paper {paperProgress.index} of {paperProgress.total}: <strong>{paperProgress.title}</strong></span>
            <span className="paper-progress-value">{Math.round((paperProgress.index / paperProgress.total) * 100)}%</span>
          </div>
          <div className="progress-track">
            <div
              className="progress-fill"
              style={{ width: `${(paperProgress.index / paperProgress.total) * 100}%` }}
            />
          </div>
        </div>
      )}
    </div>
  );
}
