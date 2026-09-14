from __future__ import annotations

from enum import Enum
from typing import Sequence

from pydantic import BaseModel, Field

from backend.models.schemas import PaperSummary, ReaderResponse


class PrismaStatus(str, Enum):
    INCLUDED = "included"
    EXCLUDED = "excluded"


class PrismaStage(str, Enum):
    IDENTIFICATION = "identification"
    SCREENING = "screening"
    ELIGIBILITY = "eligibility"
    INCLUDED = "included"


class PaperScreeningDecision(BaseModel):
    """Screening audit record according to the PRISMA 2020 statement."""

    paper_title: str
    source: str
    stage: PrismaStage
    status: PrismaStatus
    reason: str
    relevance_score: int = Field(ge=0, le=100)


class PrismaFlowResult(BaseModel):
    """PRISMA 2020 Flow metrics and audit trail for systematic reviews."""

    total_identified: int
    identification_by_source: dict[str, int] = Field(default_factory=dict)
    duplicates_removed: int
    records_screened: int
    records_excluded: int
    full_text_assessed: int
    studies_included: int
    audit_trail: list[PaperScreeningDecision] = Field(default_factory=list)
    mermaid_flowchart: str = ""


class PrismaReviewEngine:
    """Audit engine implementing the PRISMA 2020 Systematic Review protocol."""

    def __init__(self, relevance_cutoff: int = 50) -> None:
        self.relevance_cutoff = relevance_cutoff

    def generate_flow(
        self,
        raw_papers: Sequence[PaperSummary],
        screened_papers: Sequence[PaperSummary],
        reader_outputs: Sequence[ReaderResponse],
    ) -> PrismaFlowResult:
        """Generate PRISMA metrics, exclusion justifications, and Mermaid flowchart."""
        total_identified = len(raw_papers)
        source_counts: dict[str, int] = {}
        for p in raw_papers:
            source_counts[p.source] = source_counts.get(p.source, 0) + 1

        duplicates = max(0, total_identified - len(screened_papers))
        screened_count = len(screened_papers)

        audit_trail: list[PaperScreeningDecision] = []
        included_titles = {r.title.lower().strip() for r in reader_outputs}

        excluded_count = 0
        for p in screened_papers:
            p_norm = p.title.lower().strip()
            if p_norm in included_titles:
                audit_trail.append(
                    PaperScreeningDecision(
                        paper_title=p.title,
                        source=p.source,
                        stage=PrismaStage.INCLUDED,
                        status=PrismaStatus.INCLUDED,
                        reason="Meets relevance threshold and structured methodological extraction criteria.",
                        relevance_score=p.relevance_score,
                    )
                )
            else:
                excluded_count += 1
                reason = (
                    f"Relevance score ({p.relevance_score}) below threshold ({self.relevance_cutoff})"
                    if p.relevance_score < self.relevance_cutoff
                    else "Insufficient structured methodology or duplicate findings"
                )
                audit_trail.append(
                    PaperScreeningDecision(
                        paper_title=p.title,
                        source=p.source,
                        stage=PrismaStage.ELIGIBILITY,
                        status=PrismaStatus.EXCLUDED,
                        reason=reason,
                        relevance_score=p.relevance_score,
                    )
                )

        full_text_assessed = len(reader_outputs)
        studies_included = len(reader_outputs)

        # Generate PRISMA 2020 Mermaid flowchart
        mermaid = self._generate_mermaid_flowchart(
            total_identified=total_identified,
            duplicates=duplicates,
            screened=screened_count,
            excluded=excluded_count,
            assessed=full_text_assessed,
            included=studies_included,
            source_counts=source_counts,
        )

        return PrismaFlowResult(
            total_identified=total_identified,
            identification_by_source=source_counts,
            duplicates_removed=duplicates,
            records_screened=screened_count,
            records_excluded=excluded_count,
            full_text_assessed=full_text_assessed,
            studies_included=studies_included,
            audit_trail=audit_trail,
            mermaid_flowchart=mermaid,
        )

    def _generate_mermaid_flowchart(
        self,
        total_identified: int,
        duplicates: int,
        screened: int,
        excluded: int,
        assessed: int,
        included: int,
        source_counts: dict[str, int],
    ) -> str:
        sources_str = "<br/>".join(
            f"- {src}: {cnt}" for src, cnt in source_counts.items()
        )
        return (
            "graph TD\n"
            f'  subgraph Identification ["1. Identification"]\n'
            f'    A["Records Identified (n = {total_identified})<br/>{sources_str}"] --> B["Duplicates Removed (n = {duplicates})"]\n'
            f"  end\n"
            f'  subgraph Screening ["2. Screening"]\n'
            f'    B --> C["Records Screened (n = {screened})"]\n'
            f'    C --> D["Records Excluded (n = {excluded})"]\n'
            f"  end\n"
            f'  subgraph Eligibility ["3. Eligibility"]\n'
            f'    C --> E["Full-Text Assessed (n = {assessed})"]\n'
            f"  end\n"
            f'  subgraph Included ["4. Synthesis"]\n'
            f'    E --> F["Studies Included in Synthesis (n = {included})"]\n'
            f"  end\n"
            "  style F fill:#10b981,stroke:#059669,stroke-width:2px,color:#fff\n"
            "  style D fill:#f43f5e,stroke:#e11d48,stroke-width:1px,color:#fff\n"
        )
