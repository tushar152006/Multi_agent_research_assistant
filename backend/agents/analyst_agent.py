from __future__ import annotations

import re
from collections import Counter, defaultdict

from backend.agents.base_agent import BaseAgent
from backend.core.config import get_settings
from backend.core.llm import LLMService, build_llm_service
from backend.models.schemas import (
    AnalystRequest,
    AnalystResponse,
    ConflictSummary,
    InnovationSummary,
    ReaderResponse,
)


class AnalystAgent(BaseAgent[AnalystRequest, AnalystResponse]):
    """Hybrid synthesis agent: heuristic extraction + optional Ollama narrative."""

    name = "analyst_agent"

    def __init__(self, llm_service: LLMService | None = None) -> None:
        settings = get_settings()
        self._llm_provider = settings.llm_provider
        self.llm_service = llm_service or build_llm_service(
            provider=settings.llm_provider,
            ollama_base_url=settings.ollama_base_url,
            ollama_model=settings.ollama_model,
        )

    async def run(self, payload: AnalystRequest) -> AnalystResponse:
        papers = payload.papers

        themes = self._extract_themes(papers)
        innovations = self._extract_innovations(papers)
        consensus = self._extract_consensus(papers)
        conflicts = self._extract_conflicts(papers)
        gaps = self._extract_gaps(papers)
        applications = self._extract_applications(papers)

        # Optionally enrich themes with an Ollama-generated synthesis
        if self._llm_provider == "ollama" and themes:
            llm_themes = await self._generate_llm_themes(payload, themes, gaps)
            if llm_themes:
                themes = llm_themes

        return AnalystResponse(
            query=payload.query,
            themes=themes,
            innovations=innovations,
            consensus=consensus,
            conflicts=conflicts,
            gaps=gaps,
            practical_applications=applications,
        )

    async def _generate_llm_themes(
        self,
        payload: AnalystRequest,
        heuristic_themes: list[str],
        gaps: list[str],
    ) -> list[str] | None:
        paper_titles = [p.title for p in payload.papers[:5]]
        prompt = (
            "You are a research analyst synthesizing insights from academic papers.\n"
            f"Research query: {payload.query}\n"
            f"Papers analyzed: {paper_titles}\n"
            f"Initial themes detected: {heuristic_themes}\n"
            f"Research gaps identified: {gaps[:3]}\n"
            "Provide 3-5 refined, concise research themes (one per line, no numbering) "
            "that best capture the findings across these papers."
        )
        try:
            raw = await self.llm_service.generate(prompt)
            lines = [line.strip() for line in raw.splitlines() if line.strip()]
            refined = [l for l in lines if 10 <= len(l) <= 200][:5]
            return refined if refined else None
        except Exception:
            return None

    def _extract_themes(self, papers: list[ReaderResponse]) -> list[str]:
        phrase_counter: Counter[str] = Counter()

        for paper in papers:
            phrase_counter.update(self._collect_theme_candidates(paper))

        themes = [
            phrase
            for phrase, _count in phrase_counter.most_common()
            if len(phrase) > 8
        ]
        return themes[:5]

    def _extract_innovations(
        self,
        papers: list[ReaderResponse],
    ) -> list[InnovationSummary]:
        innovations: list[InnovationSummary] = []

        for paper in papers:
            innovation = (
                paper.methodology.approach
                or paper.problem
                or (paper.results.primary_findings[0] if paper.results.primary_findings else "")
            )
            impact = (
                paper.results.primary_findings[0]
                if paper.results.primary_findings
                else "The paper reports a meaningful contribution but impact details are limited."
            )
            innovations.append(
                InnovationSummary(
                    paper_title=paper.title,
                    innovation=innovation,
                    impact=impact,
                )
            )

        return innovations[:5]

    def _extract_consensus(self, papers: list[ReaderResponse]) -> list[str]:
        metric_counter: Counter[str] = Counter()
        dataset_counter: Counter[str] = Counter()
        limitation_counter: Counter[str] = Counter()

        for paper in papers:
            metric_counter.update(paper.methodology.metrics)
            dataset_counter.update(item.lower() for item in paper.methodology.datasets)
            limitation_counter.update(self._normalize_phrases(paper.limitations))

        consensus: list[str] = []
        for metric, count in metric_counter.items():
            if count >= 2:
                consensus.append(
                    f"Multiple papers evaluate performance with the `{metric}` metric."
                )
        for dataset, count in dataset_counter.items():
            if count >= 2:
                consensus.append(
                    f"Multiple papers rely on the dataset or benchmark `{dataset}`."
                )
        for limitation, count in limitation_counter.items():
            if count >= 2:
                consensus.append(
                    f"Several papers acknowledge a shared limitation: {limitation}."
                )

        if not consensus and papers:
            consensus.append(
                "The papers broadly align on pursuing automated, structured research workflows."
            )

        return consensus[:5]

    def _extract_conflicts(self, papers: list[ReaderResponse]) -> list[ConflictSummary]:
        grouped_metrics: dict[str, list[tuple[str, float, str]]] = defaultdict(list)

        for paper in papers:
            for metric_name, raw_value in paper.results.metrics.items():
                numeric_value = self._parse_metric_value(raw_value)
                if numeric_value is not None:
                    grouped_metrics[metric_name].append(
                        (paper.title, numeric_value, raw_value)
                    )

        conflicts: list[ConflictSummary] = []
        for metric_name, values in grouped_metrics.items():
            if len(values) < 2:
                continue
            spread = max(value for _title, value, _raw in values) - min(
                value for _title, value, _raw in values
            )
            if spread >= 10:
                conflicts.append(
                    ConflictSummary(
                        topic=metric_name,
                        description=(
                            f"Reported `{metric_name}` outcomes vary noticeably across papers, "
                            f"suggesting dataset, scope, or evaluation differences."
                        ),
                        papers=[title for title, _value, _raw in values],
                    )
                )

        return conflicts[:5]

    def _extract_gaps(self, papers: list[ReaderResponse]) -> list[str]:
        gaps: list[str] = []
        future_work_items = [
            item
            for paper in papers
            for item in paper.future_work
        ]
        limitation_items = [
            item
            for paper in papers
            for item in paper.limitations
        ]

        for sentence in future_work_items[:3]:
            gaps.append(f"Open direction highlighted by the papers: {sentence}")
        for sentence in limitation_items[:2]:
            gaps.append(f"Unresolved limitation across the literature: {sentence}")

        if not gaps:
            gaps.append(
                "The current paper set does not yet provide enough structured evidence to identify strong research gaps."
            )

        return gaps[:5]

    def _extract_applications(self, papers: list[ReaderResponse]) -> list[str]:
        applications: list[str] = []

        for paper in papers:
            for finding in paper.results.primary_findings[:2]:
                applications.append(
                    f"{paper.title}: {finding}"
                )

        if not applications and papers:
            applications.append(
                "The analyzed papers point toward workflow automation, retrieval quality improvement, and research productivity tooling."
            )

        return applications[:5]

    def _collect_theme_candidates(self, paper: ReaderResponse) -> list[str]:
        candidates: list[str] = []
        for text in [
            paper.problem,
            paper.methodology.approach,
            *paper.results.primary_findings,
        ]:
            candidates.extend(self._extract_key_phrases(text))
        return candidates

    @staticmethod
    def _extract_key_phrases(text: str) -> list[str]:
        if not text:
            return []

        stop_words = {
            "this",
            "that",
            "with",
            "from",
            "their",
            "paper",
            "study",
            "using",
            "into",
            "for",
            "and",
            "the",
            "our",
            "are",
            "was",
            "were",
            "have",
            "has",
            "had",
        }
        words = [
            word.lower()
            for word in re.findall(r"[a-zA-Z][a-zA-Z\-]+", text)
            if len(word) > 3 and word.lower() not in stop_words
        ]

        phrases = [
            " ".join(words[index : index + 2])
            for index in range(len(words) - 1)
        ]
        return phrases[:8]

    @staticmethod
    def _normalize_phrases(items: list[str]) -> list[str]:
        return [
            re.sub(r"\s+", " ", item.strip().lower())
            for item in items
            if item.strip()
        ]

    @staticmethod
    def _parse_metric_value(value: str) -> float | None:
        match = re.search(r"([0-9]+(?:\.[0-9]+)?)", value)
        if not match:
            return None
        return float(match.group(1))
