from __future__ import annotations

import re
from enum import Enum
from typing import Sequence

from pydantic import BaseModel, Field

from backend.core.contradiction_matrix import ContradictionPair
from backend.models.schemas import AnalystResponse, ReaderResponse


class GraphNodeType(str, Enum):
    PAPER = "paper"
    DATASET = "dataset"
    METHOD = "method"
    METRIC = "metric"
    THEME = "theme"


class GraphRelation(str, Enum):
    EVALUATES_ON = "evaluates_on"
    PROPOSES_METHOD = "proposes_method"
    REPORTS_METRIC = "reports_metric"
    CONTRIBUTES_TO_THEME = "contributes_to_theme"
    CONTRADICTS = "contradicts"


class GraphNode(BaseModel):
    id: str
    label: str
    node_type: GraphNodeType
    properties: dict[str, str] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    source: str
    target: str
    relation: GraphRelation
    label: str
    weight: float = 1.0


class EvidenceGraphResult(BaseModel):
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)
    central_concepts: list[str] = Field(default_factory=list)
    mermaid_diagram: str = ""


def _sanitize_id(text: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_]", "_", text).strip("_")
    return cleaned[:30] if cleaned else "node"


class EvidenceGraphEngine:
    """Constructs multi-paper Knowledge and Evidence Graphs from extracted research data."""

    def build_graph(
        self,
        reader_outputs: Sequence[ReaderResponse],
        analysis: AnalystResponse | None = None,
        tensions: Sequence[ContradictionPair] | None = None,
    ) -> EvidenceGraphResult:
        nodes: dict[str, GraphNode] = {}
        edges: list[GraphEdge] = []

        # 1. Add paper nodes, dataset nodes, and methodology nodes
        for r in reader_outputs:
            paper_id = f"paper_{_sanitize_id(r.title)}"
            nodes[paper_id] = GraphNode(
                id=paper_id,
                label=r.title[:45] + ("…" if len(r.title) > 45 else ""),
                node_type=GraphNodeType.PAPER,
                properties={"title": r.title},
            )

            # Datasets
            for ds in r.methodology.datasets:
                if not ds.strip():
                    continue
                ds_id = f"ds_{_sanitize_id(ds)}"
                if ds_id not in nodes:
                    nodes[ds_id] = GraphNode(
                        id=ds_id,
                        label=ds,
                        node_type=GraphNodeType.DATASET,
                    )
                edges.append(
                    GraphEdge(
                        source=paper_id,
                        target=ds_id,
                        relation=GraphRelation.EVALUATES_ON,
                        label="evaluates on",
                    )
                )

            # Metrics
            for m_key, m_val in r.results.metrics.items():
                m_id = f"metric_{_sanitize_id(m_key)}"
                if m_id not in nodes:
                    nodes[m_id] = GraphNode(
                        id=m_id,
                        label=m_key.title(),
                        node_type=GraphNodeType.METRIC,
                    )
                edges.append(
                    GraphEdge(
                        source=paper_id,
                        target=m_id,
                        relation=GraphRelation.REPORTS_METRIC,
                        label=f"{m_val}",
                    )
                )

        # 2. Add Themes if analysis is available
        if analysis and analysis.themes:
            for theme in analysis.themes:
                theme_id = f"theme_{_sanitize_id(theme)}"
                if theme_id not in nodes:
                    nodes[theme_id] = GraphNode(
                        id=theme_id,
                        label=theme[:35] + ("…" if len(theme) > 35 else ""),
                        node_type=GraphNodeType.THEME,
                    )
                for r in reader_outputs:
                    paper_id = f"paper_{_sanitize_id(r.title)}"
                    edges.append(
                        GraphEdge(
                            source=paper_id,
                            target=theme_id,
                            relation=GraphRelation.CONTRIBUTES_TO_THEME,
                            label="contributes to",
                        )
                    )

        # 3. Add Contradiction edges
        if tensions:
            for t in tensions:
                p_a_id = f"paper_{_sanitize_id(t.paper_a)}"
                p_b_id = f"paper_{_sanitize_id(t.paper_b)}"
                if p_a_id in nodes and p_b_id in nodes:
                    edges.append(
                        GraphEdge(
                            source=p_a_id,
                            target=p_b_id,
                            relation=GraphRelation.CONTRADICTS,
                            label=f"Tension: {t.topic[:20]}",
                            weight=t.confidence,
                        )
                    )

        # Identify central concepts (nodes with highest in/out degree)
        degrees: dict[str, int] = {}
        for edge in edges:
            degrees[edge.source] = degrees.get(edge.source, 0) + 1
            degrees[edge.target] = degrees.get(edge.target, 0) + 1

        top_concepts = sorted(
            [n.label for n_id, n in nodes.items() if n.node_type != GraphNodeType.PAPER],
            key=lambda lbl: degrees.get(lbl, 0),
            reverse=True,
        )[:5]

        # Generate Mermaid Graph Diagram
        mermaid = self._generate_mermaid(nodes, edges)

        return EvidenceGraphResult(
            nodes=list(nodes.values()),
            edges=edges,
            central_concepts=top_concepts,
            mermaid_diagram=mermaid,
        )

    def _generate_mermaid(
        self,
        nodes: dict[str, GraphNode],
        edges: list[GraphEdge],
    ) -> str:
        lines = ["graph LR"]

        # Define node styles
        for n_id, node in list(nodes.items())[:25]:  # Bound to top 25 for visual clarity
            escaped_label = node.label.replace('"', "'")
            if node.node_type == GraphNodeType.PAPER:
                lines.append(f'  {n_id}["📄 {escaped_label}"]')
            elif node.node_type == GraphNodeType.DATASET:
                lines.append(f'  {n_id}[("📊 {escaped_label}")]')
            elif node.node_type == GraphNodeType.METRIC:
                lines.append(f'  {n_id}{{"🎯 {escaped_label}"}}')
            elif node.node_type == GraphNodeType.THEME:
                lines.append(f'  {n_id}(["💡 {escaped_label}"])')

        # Add edges
        for edge in edges[:35]:  # Bound to top 35 edges for readable diagram
            if edge.source in nodes and edge.target in nodes:
                escaped_label = edge.label.replace('"', "'")
                if edge.relation == GraphRelation.CONTRADICTS:
                    lines.append(
                        f'  {edge.source} -.->|"{escaped_label}"| {edge.target}'
                    )
                else:
                    lines.append(
                        f'  {edge.source} -->|"{escaped_label}"| {edge.target}'
                    )

        lines.append("  classDef paper fill:#2563eb,stroke:#1d4ed8,color:#fff;")
        lines.append("  classDef dataset fill:#10b981,stroke:#059669,color:#fff;")
        lines.append("  classDef metric fill:#8b5cf6,stroke:#7c3aed,color:#fff;")
        lines.append("  classDef theme fill:#f59e0b,stroke:#d97706,color:#fff;")

        return "\n".join(lines)
