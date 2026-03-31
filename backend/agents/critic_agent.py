from __future__ import annotations

from backend.agents.base_agent import BaseAgent
from backend.core.config import get_settings
from backend.core.llm import LLMService, build_llm_service
from backend.models.schemas import (
    CriticRequest,
    CriticResponse,
    CritiqueItem,
)


class CriticAgent(BaseAgent[CriticRequest, CriticResponse]):
    """Free-first critic with optional Ollama-assisted summary."""

    name = "critic_agent"

    def __init__(self, llm_service: LLMService | None = None) -> None:
        settings = get_settings()
        self.review_mode = settings.llm_provider
        self.llm_service = llm_service or build_llm_service(
            provider=settings.llm_provider,
            ollama_base_url=settings.ollama_base_url,
            ollama_model=settings.ollama_model,
        )

    async def run(self, payload: CriticRequest) -> CriticResponse:
        critiques = self._build_heuristic_critiques(payload)
        llm_summary: str | None = None

        if self.review_mode == "ollama":
            llm_summary = await self._generate_llm_summary(payload, critiques)

        return CriticResponse(
            query=payload.query,
            critiques=critiques,
            overall_confidence=self._calculate_confidence(critiques),
            review_mode=self.review_mode,
            llm_summary=llm_summary,
        )

    def _build_heuristic_critiques(
        self,
        payload: CriticRequest,
    ) -> list[CritiqueItem]:
        analysis = payload.analysis
        critiques: list[CritiqueItem] = []

        if analysis.conflicts:
            for conflict in analysis.conflicts[:2]:
                critiques.append(
                    CritiqueItem(
                        category="methodology",
                        issue=f"Conflicting evidence detected around `{conflict.topic}`.",
                        severity="medium",
                        evidence=conflict.description,
                        impact=(
                            "The synthesized conclusion may be unstable across datasets or evaluation setups."
                        ),
                    )
                )

        if analysis.gaps:
            critiques.append(
                CritiqueItem(
                    category="coverage",
                    issue="The analyzed literature still contains unresolved research gaps.",
                    severity="medium",
                    evidence=analysis.gaps[0],
                    impact=(
                        "Recommendations built on the current evidence may miss important unexplored conditions."
                    ),
                )
            )

        if not analysis.conflicts and len(analysis.innovations) < 2:
            critiques.append(
                CritiqueItem(
                    category="evidence",
                    issue="The evidence base is narrow.",
                    severity="high",
                    evidence=(
                        "The analysis is supported by too few strong innovations to establish broad conclusions."
                    ),
                    impact=(
                        "The system may overgeneralize from a small sample of papers."
                    ),
                )
            )

        if any("limited" in gap.lower() for gap in analysis.gaps):
            critiques.append(
                CritiqueItem(
                    category="generalization",
                    issue="Generalization risk remains high.",
                    severity="high",
                    evidence="Several extracted gaps point to limited evaluation scope.",
                    impact=(
                        "Real-world performance may diverge from the reported literature results."
                    ),
                )
            )

        if not critiques:
            critiques.append(
                CritiqueItem(
                    category="confidence",
                    issue="No major heuristic red flags were detected.",
                    severity="low",
                    evidence="The current synthesis is internally consistent at the heuristic level.",
                    impact="The analysis looks directionally useful, but still benefits from deeper review.",
                )
            )

        return critiques[:5]

    async def _generate_llm_summary(
        self,
        payload: CriticRequest,
        critiques: list[CritiqueItem],
    ) -> str | None:
        prompt = self._build_llm_prompt(payload, critiques)
        try:
            summary = await self.llm_service.generate(prompt)
        except Exception:
            return None
        return summary or None

    @staticmethod
    def _build_llm_prompt(
        payload: CriticRequest,
        critiques: list[CritiqueItem],
    ) -> str:
        critique_lines = "\n".join(
            f"- [{item.severity}] {item.category}: {item.issue} Evidence: {item.evidence}"
            for item in critiques
        )
        return (
            "You are a rigorous research critic.\n"
            f"User query: {payload.query}\n"
            f"Themes: {payload.analysis.themes}\n"
            f"Consensus: {payload.analysis.consensus}\n"
            f"Conflicts: {payload.analysis.conflicts}\n"
            f"Gaps: {payload.analysis.gaps}\n"
            f"Heuristic critiques:\n{critique_lines}\n"
            "Write a short critique summary with the biggest risks and what should be validated next."
        )

    @staticmethod
    def _calculate_confidence(critiques: list[CritiqueItem]) -> float:
        penalty = 0.0
        for critique in critiques:
            if critique.severity == "high":
                penalty += 0.2
            elif critique.severity == "medium":
                penalty += 0.1
            else:
                penalty += 0.03
        return max(0.2, min(0.95, 0.9 - penalty))
