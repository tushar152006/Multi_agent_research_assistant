from __future__ import annotations

import re

from backend.agents.base_agent import BaseAgent
from backend.models.schemas import (
    MethodologySummary,
    ReaderRequest,
    ReaderResponse,
    ResultsSummary,
)
from backend.services.pdf_service import PdfService


class ReaderAgent(BaseAgent[ReaderRequest, ReaderResponse]):
    """Extract structured paper insights from normalized document text."""

    name = "reader_agent"

    def __init__(self, pdf_service: PdfService | None = None) -> None:
        self.pdf_service = pdf_service or PdfService()

    async def run(self, payload: ReaderRequest) -> ReaderResponse:
        normalized_text = self.pdf_service.normalize_text(payload.content)
        sections = self._extract_sections(normalized_text)

        return ReaderResponse(
            title=payload.title,
            problem=self._extract_problem(sections, normalized_text),
            methodology=self._extract_methodology(sections, normalized_text),
            results=self._extract_results(sections, normalized_text),
            limitations=self._extract_limitations(sections),
            future_work=self._extract_future_work(sections),
            extracted_sections=sections,
        )

    def _extract_sections(self, text: str) -> dict[str, str]:
        section_names = [
            "abstract",
            "introduction",
            "background",
            "related work",
            "method",
            "methodology",
            "approach",
            "experiment",
            "experiments",
            "results",
            "discussion",
            "limitations",
            "future work",
            "conclusion",
        ]
        positions: list[tuple[int, str]] = []

        for name in section_names:
            pattern = re.compile(
                rf"(?im)^(?:\d+(?:\.\d+)*)?\s*{re.escape(name)}\s*$"
            )
            match = pattern.search(text)
            if match:
                positions.append((match.start(), name))

        positions.sort()
        if not positions:
            return {"full_text": text}

        sections: dict[str, str] = {}
        for index, (start, name) in enumerate(positions):
            end = positions[index + 1][0] if index + 1 < len(positions) else len(text)
            content_start = text.find("\n", start)
            if content_start == -1:
                content_start = start
            section_body = text[content_start:end].strip()
            key = name.replace(" ", "_")
            sections[key] = section_body

        return sections

    def _extract_problem(self, sections: dict[str, str], text: str) -> str:
        candidate = (
            sections.get("abstract")
            or sections.get("introduction")
            or self._first_paragraph(text)
        )
        return self._first_sentence_block(candidate)

    def _extract_methodology(
        self,
        sections: dict[str, str],
        text: str,
    ) -> MethodologySummary:
        candidate = (
            sections.get("methodology")
            or sections.get("method")
            or sections.get("approach")
            or sections.get("experiments")
            or text
        )
        datasets = self._extract_keyword_matches(
            candidate,
            prefixes=("dataset", "datasets", "benchmark", "benchmarks"),
        )
        metrics = self._extract_metric_names(candidate)
        return MethodologySummary(
            approach=self._first_sentence_block(candidate),
            datasets=datasets,
            metrics=metrics,
        )

    def _extract_results(
        self,
        sections: dict[str, str],
        text: str,
    ) -> ResultsSummary:
        candidate = (
            sections.get("results")
            or sections.get("discussion")
            or sections.get("conclusion")
            or text
        )
        findings = self._extract_sentences(candidate, limit=3)
        return ResultsSummary(
            primary_findings=findings,
            metrics=self._extract_metric_values(candidate),
        )

    def _extract_limitations(self, sections: dict[str, str]) -> list[str]:
        candidate = sections.get("limitations") or sections.get("discussion", "")
        return self._extract_sentences(candidate, limit=3)

    def _extract_future_work(self, sections: dict[str, str]) -> list[str]:
        candidate = sections.get("future_work") or sections.get("conclusion", "")
        return self._extract_sentences(candidate, limit=3)

    @staticmethod
    def _first_paragraph(text: str) -> str:
        paragraphs = [chunk.strip() for chunk in text.split("\n\n") if chunk.strip()]
        return paragraphs[0] if paragraphs else ""

    @staticmethod
    def _first_sentence_block(text: str, max_sentences: int = 2) -> str:
        sentences = ReaderAgent._extract_sentences(text, limit=max_sentences)
        return " ".join(sentences)

    @staticmethod
    def _extract_sentences(text: str, limit: int = 3) -> list[str]:
        if not text:
            return []
        sentences = [
            sentence.strip()
            for sentence in re.split(r"(?<=[.!?])\s+", text)
            if len(sentence.strip()) > 20
        ]
        return sentences[:limit]

    @staticmethod
    def _extract_keyword_matches(
        text: str,
        prefixes: tuple[str, ...],
    ) -> list[str]:
        matches: list[str] = []
        for prefix in prefixes:
            pattern = re.compile(
                rf"(?i)\b{re.escape(prefix)}\b[:\s]+([A-Za-z0-9_,\- ]{{3,80}})"
            )
            for match in pattern.findall(text):
                cleaned = match.strip(" .,;:")
                if cleaned and cleaned not in matches:
                    matches.append(cleaned)
        return matches[:5]

    @staticmethod
    def _extract_metric_names(text: str) -> list[str]:
        known_metrics = [
            "accuracy",
            "precision",
            "recall",
            "f1",
            "f1-score",
            "auc",
            "bleu",
            "rouge",
            "latency",
        ]
        lowered = text.lower()
        return [metric for metric in known_metrics if metric in lowered]

    @staticmethod
    def _extract_metric_values(text: str) -> dict[str, str]:
        metrics: dict[str, str] = {}
        patterns = {
            "accuracy": r"(?i)\baccuracy\b[^0-9]{0,10}([0-9]+(?:\.[0-9]+)?%?)",
            "precision": r"(?i)\bprecision\b[^0-9]{0,10}([0-9]+(?:\.[0-9]+)?%?)",
            "recall": r"(?i)\brecall\b[^0-9]{0,10}([0-9]+(?:\.[0-9]+)?%?)",
            "f1": r"(?i)\bf1(?:-score)?\b[^0-9]{0,10}([0-9]+(?:\.[0-9]+)?%?)",
            "auc": r"(?i)\bauc\b[^0-9]{0,10}([0-9]+(?:\.[0-9]+)?%?)",
        }
        for name, pattern in patterns.items():
            match = re.search(pattern, text)
            if match:
                metrics[name] = match.group(1)
        return metrics
