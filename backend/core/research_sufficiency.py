from __future__ import annotations

import logging
from typing import Sequence

from pydantic import BaseModel, Field

from backend.core.citation_grounding import GroundingVerificationResult
from backend.core.contradiction_matrix import ContradictionMatrixResult
from backend.models.schemas import AnalystResponse, CriticResponse, PaperSummary

logger = logging.getLogger(__name__)


class SufficiencyVerdict(BaseModel):
    """Decision produced by the ResearchSufficiencyJudge."""

    is_sufficient: bool
    confidence: float = Field(ge=0.0, le=1.0)
    missing_aspects: list[str] = Field(default_factory=list)
    recommended_queries: list[str] = Field(default_factory=list)
    stop_reason: str
    iteration: int


class ResearchSufficiencyJudge:
    """Evaluates whether current research evidence is scientifically sufficient or requires targeted follow-up."""

    def __init__(
        self,
        min_papers: int = 2,
        min_precision: float = 0.65,
        max_iterations: int = 3,
        max_total_papers: int = 8,
    ) -> None:
        self.min_papers = min_papers
        self.min_precision = min_precision
        self.max_iterations = max_iterations
        self.max_total_papers = max_total_papers

    def evaluate(
        self,
        query: str,
        iteration: int,
        papers: Sequence[PaperSummary],
        analysis: AnalystResponse | None = None,
        critique: CriticResponse | None = None,
        grounding_audit: GroundingVerificationResult | None = None,
        contradiction_matrix: ContradictionMatrixResult | None = None,
    ) -> SufficiencyVerdict:
        """Inspect evidence volume, grounding precision, and literature gaps to decide next step."""
        missing_aspects: list[str] = []
        recommended_queries: list[str] = []

        # 1. Check Hard Iteration & Resource Limits
        if iteration >= self.max_iterations:
            return SufficiencyVerdict(
                is_sufficient=True,
                confidence=0.75,
                stop_reason="max_iterations_reached",
                iteration=iteration,
            )

        if len(papers) >= self.max_total_papers:
            return SufficiencyVerdict(
                is_sufficient=True,
                confidence=0.80,
                stop_reason="max_papers_budget_reached",
                iteration=iteration,
            )

        # 2. Check Minimal Corpus Feasibility
        if len(papers) < self.min_papers:
            rec_query = f"{query} empirical benchmarks evaluation"
            return SufficiencyVerdict(
                is_sufficient=False,
                confidence=0.30,
                missing_aspects=["Insufficient paper corpus size for peer synthesis."],
                recommended_queries=[rec_query],
                stop_reason="insufficient_papers",
                iteration=iteration,
            )

        # 3. Check Grounding Precision
        if grounding_audit is not None:
            if grounding_audit.grounding_precision < self.min_precision:
                missing_aspects.append(
                    f"Grounding precision is {grounding_audit.grounding_precision * 100:.1f}%, "
                    f"below threshold of {self.min_precision * 100:.1f}%."
                )
                if grounding_audit.unsupported_claims:
                    unanchored = grounding_audit.unsupported_claims[0]
                    recommended_queries.append(f"{query} {unanchored[:40]}")

        # 4. Check Analyst Gaps & Conflicts
        if analysis is not None:
            if not analysis.themes:
                missing_aspects.append("No prominent scientific themes were extracted.")
                recommended_queries.append(f"{query} methodology architecture")

            if analysis.gaps and len(papers) < 5:
                gap = analysis.gaps[0]
                cleaned_gap = gap.replace("Open direction highlighted by the papers:", "").strip()
                missing_aspects.append(f"Major open literature gap: {cleaned_gap[:80]}")
                if not recommended_queries:
                    recommended_queries.append(f"{query} {cleaned_gap[:50]}")

        # 5. Check Contradiction Matrix Density
        if contradiction_matrix and contradiction_matrix.key_open_debates:
            debate = contradiction_matrix.key_open_debates[0]
            missing_aspects.append(f"Unresolved empirical debate: {debate[:80]}")
            if len(recommended_queries) < 2:
                recommended_queries.append(f"{query} {debate[:50]}")

        # Final Decision Synthesis
        is_sufficient = len(missing_aspects) == 0 or len(recommended_queries) == 0
        confidence = 0.90 if is_sufficient else 0.50

        return SufficiencyVerdict(
            is_sufficient=is_sufficient,
            confidence=confidence,
            missing_aspects=missing_aspects,
            recommended_queries=recommended_queries,
            stop_reason="evidence_sufficient" if is_sufficient else "evidence_needs_expansion",
            iteration=iteration,
        )
