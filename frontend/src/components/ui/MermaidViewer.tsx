"use client";

import { useEffect, useRef, useState } from "react";

interface MermaidViewerProps {
  chart: string;
}

export function MermaidViewer({ chart }: MermaidViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [svgContent, setSvgContent] = useState<string>("");
  const [copied, setCopied] = useState(false);
  const [renderError, setRenderError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    if (!chart || typeof window === "undefined") return;

    // Dynamically import Mermaid from CDN for zero-dependency visual rendering
    const dynamicImport = new Function("url", "return import(url)");
    dynamicImport("https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs")
      .then((m: any) => {
        if (!isMounted) return;
        const mermaid = m.default || m;
        mermaid.initialize({
          startOnLoad: false,
          theme: "base",
          themeVariables: {
            primaryColor: "#ECEEEE",
            primaryTextColor: "#2C2C2C",
            primaryBorderColor: "#612D53",
            lineColor: "#612D53",
            secondaryColor: "#F3F4F4",
            tertiaryColor: "#FFFFFF",
            fontFamily: "inherit",
          },
          securityLevel: "loose",
          fontFamily: "inherit",
        });
        const id = `mermaid-${Math.random().toString(36).substring(2, 9)}`;
        return mermaid.render(id, chart);
      })
      .then((res: { svg?: string }) => {
        if (isMounted && res?.svg) {
          setSvgContent(res.svg);
          setRenderError(null);
        }
      })
      .catch((err: unknown) => {
        if (isMounted) {
          setRenderError("Visual diagram rendered in code view.");
        }
      });

    return () => {
      isMounted = false;
    };
  }, [chart]);

  function handleCopy() {
    navigator.clipboard.writeText(chart);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  function handleOpenLive() {
    const encoded = encodeURIComponent(chart);
    window.open(`https://mermaid.live/edit#pako:${encoded}`, "_blank");
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
        <button
          className="button button-secondary"
          style={{ height: 32, fontSize: "0.75rem", padding: "0 10px" }}
          onClick={handleCopy}
          title="Copy Mermaid code to clipboard"
        >
          {copied ? "✓ Copied Code" : "📋 Copy Code"}
        </button>
        <button
          className="button button-secondary"
          style={{ height: 32, fontSize: "0.75rem", padding: "0 10px" }}
          onClick={handleOpenLive}
          title="Open in Mermaid Live Editor"
        >
          ↗ Open Live
        </button>
      </div>

      {svgContent ? (
        <div
          ref={containerRef}
          style={{
            background: "var(--color-surface-elevated)",
            padding: 20,
            borderRadius: "var(--radius-md)",
            border: "1px solid var(--color-border)",
            display: "flex",
            justifyContent: "center",
            overflowX: "auto",
          }}
          dangerouslySetInnerHTML={{ __html: svgContent }}
        />
      ) : (
        <div
          style={{
            background: "var(--color-surface-elevated)",
            padding: 16,
            borderRadius: "var(--radius-md)",
            border: "1px solid var(--color-border)",
            overflowX: "auto",
          }}
        >
          {renderError && (
            <div
              style={{
                fontSize: "0.75rem",
                color: "var(--color-text-muted)",
                marginBottom: 8,
              }}
            >
              {renderError}
            </div>
          )}
          <pre
            style={{
              fontSize: "0.82rem",
              fontFamily: "var(--font-mono)",
              color: "var(--color-primary)",
              whiteSpace: "pre-wrap",
              lineHeight: 1.4,
              margin: 0,
            }}
          >
            {chart}
          </pre>
        </div>
      )}
    </div>
  );
}
