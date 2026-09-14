from __future__ import annotations

import re
from collections import Counter
from enum import Enum
from typing import Sequence

from pydantic import BaseModel, Field

from backend.models.schemas import ReaderResponse


class ContradictionSeverity(str, Enum):
    DIRECT_EMPIRICAL = "direct_empirical"
    METHODOLOGICAL_DISAGREEMENT = "methodological_disagreement"
    QUALITATIVE_CONFLICT = "qualitative_conflict"
    LIMITATION_COLLISION = "limitation_collision"


class ContradictionPair(BaseModel):
    """Pairwise tension or conflict between two research papers."""

    paper_a: str
    paper_b: str
    topic: str
    claim_a: str
    claim_b: str
    severity: ContradictionSeverity
    confidence: float = Field(ge=0.0, le=1.0)
    root_cause: str
    resolution_hypothesis: str


class ContradictionMatrixResult(BaseModel):
    """Aggregated contradiction graph and tension matrix across all ingested papers."""

    papers_analyzed: list[str] = Field(default_factory=list)
    total_pairs_checked: int = 0
    tensions: list[ContradictionPair] = Field(default_factory=list)
    matrix_density: float = 0.0
    most_controversial_paper: str | None = None
    key_open_debates: list[str] = Field(default_factory=list)


POSITIVE_POLARITY_TERMS = {
    "outperforms",
    "superior",
    "improves",
    "surpasses",
    "effective",
    "higher",
    "state-of-the-art",
    "sota",
    "beneficial",
    "robust",
    "efficient",
    "enhances",
    "scalable",
    "reduces",
}

NEGATIVE_POLARITY_TERMS = {
    "underperforms",
    "inferior",
    "degrades",
    "fails",
    "ineffective",
    "lower",
    "insufficient",
    "unsuitable",
    "brittle",
    "vulnerable",
    "struggles",
    "bottleneck",
    "limited",
    "overhead",
}


def _normalize_metric_key(key: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]", "", key).lower()
    mapping = {
        "acc": "accuracy",
        "accuracies": "accuracy",
        "prec": "precision",
        "rec": "recall",
        "f1score": "f1",
        "f1": "f1",
        "latency": "latency",
        "throughput": "throughput",
        "loss": "loss",
        "bleu": "bleu",
        "rouge": "rouge",
    }
    return mapping.get(cleaned, cleaned)


def _parse_numeric_value(val: str) -> float | None:
    if not val:
        return None
    match = re.search(r"[-+]?\d*\.?\d+", val)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def _tokenize_meaningful(text: str) -> set[str]:
    words = re.findall(r"[a-zA-Z0-9_-]+", text.lower())
    stopwords = {
        "the", "a", "an", "is", "are", "was", "were", "and", "or", "in",
        "on", "at", "for", "with", "by", "of", "to", "from", "as", "our",
        "we", "this", "that", "these", "those", "can", "may", "paper",
        "approach", "method", "study", "results", "using", "used", "which",
    }
    return {w for w in words if len(w) > 2 and w not in stopwords}


class ContradictionMatrixEngine:
    """Algorithmic contradiction detection and tension matrix builder."""

    def __init__(self, empirical_metric_threshold: float = 3.0) -> None:
        self.empirical_metric_threshold = empirical_metric_threshold

    def build_matrix(
        self,
        reader_outputs: Sequence[ReaderResponse],
    ) -> ContradictionMatrixResult:
        titles = [p.title for p in reader_outputs]
        n = len(reader_outputs)
        if n < 2:
            return ContradictionMatrixResult(
                papers_analyzed=titles,
                total_pairs_checked=0,
                tensions=[],
                matrix_density=0.0,
                most_controversial_paper=None,
                key_open_debates=[],
            )

        total_pairs = (n * (n - 1)) // 2
        tensions: list[ContradictionPair] = []

        for i in range(n):
            for j in range(i + 1, n):
                pair_tensions = self._compare_paper_pair(
                    reader_outputs[i], reader_outputs[j]
                )
                tensions.extend(pair_tensions)

        # Calculate matrix statistics
        density = round(len(tensions) / max(1, total_pairs), 3)

        # Most controversial paper
        paper_involvement: Counter[str] = Counter()
        for t in tensions:
            paper_involvement[t.paper_a] += 1
            paper_involvement[t.paper_b] += 1

        most_controversial = (
            paper_involvement.most_common(1)[0][0] if paper_involvement else None
        )

        # Synthesize key open debates
        debates: list[str] = []
        seen_topics: set[str] = set()
        for t in tensions:
            topic_key = t.topic.lower().strip()
            if topic_key not in seen_topics:
                seen_topics.add(topic_key)
                debates.append(
                    f"Discrepancy on '{t.topic}': '{t.paper_a}' vs '{t.paper_b}' (Root cause: {t.root_cause})"
                )

        return ContradictionMatrixResult(
            papers_analyzed=titles,
            total_pairs_checked=total_pairs,
            tensions=tensions,
            matrix_density=density,
            most_controversial_paper=most_controversial,
            key_open_debates=debates,
        )

    def _compare_paper_pair(
        self,
        paper_a: ReaderResponse,
        paper_b: ReaderResponse,
    ) -> list[ContradictionPair]:
        tensions: list[ContradictionPair] = []

        # 1. Direct empirical metric discrepancies
        empirical = self._check_empirical_metric_discrepancies(paper_a, paper_b)
        tensions.extend(empirical)

        # 2. Limitation-vs-Methodology / Claim collisions
        limitation_clashes = self._check_limitation_collisions(paper_a, paper_b)
        tensions.extend(limitation_clashes)

        # 3. Qualitative claim polarity conflicts
        polarity_conflicts = self._check_qualitative_claim_conflicts(paper_a, paper_b)
        tensions.extend(polarity_conflicts)

        return tensions

    def _check_empirical_metric_discrepancies(
        self,
        paper_a: ReaderResponse,
        paper_b: ReaderResponse,
    ) -> list[ContradictionPair]:
        pairs: list[ContradictionPair] = []
        metrics_a = paper_a.results.metrics or {}
        metrics_b = paper_b.results.metrics or {}

        # Shared or overlapping datasets with preserved casing
        ds_a_map = {d.lower().strip(): d for d in paper_a.methodology.datasets}
        ds_b_map = {d.lower().strip(): d for d in paper_b.methodology.datasets}
        shared_keys = set(ds_a_map.keys()).intersection(ds_b_map.keys())
        shared_datasets = [ds_a_map[k] for k in shared_keys]

        normalized_a = {
            _normalize_metric_key(k): (k, v) for k, v in metrics_a.items()
        }
        normalized_b = {
            _normalize_metric_key(k): (k, v) for k, v in metrics_b.items()
        }

        shared_metric_keys = set(normalized_a.keys()).intersection(
            normalized_b.keys()
        )

        for norm_key in shared_metric_keys:
            raw_key_a, raw_val_a = normalized_a[norm_key]
            raw_key_b, raw_val_b = normalized_b[norm_key]

            num_a = _parse_numeric_value(raw_val_a)
            num_b = _parse_numeric_value(raw_val_b)

            if num_a is not None and num_b is not None:
                delta = abs(num_a - num_b)
                if delta >= self.empirical_metric_threshold:
                    # Root cause attribution
                    if shared_datasets:
                        ds_name = ", ".join(shared_datasets)
                        root_cause = (
                            f"Discrepancy on shared benchmark ({ds_name}). "
                            "Likely driven by differing evaluation protocols or model hyperparameters."
                        )
                        resolution = (
                            f"Conduct controlled replication on benchmark '{ds_name}' "
                            "using unified preprocessing and evaluation scripts."
                        )
                        confidence = 0.92
                    elif ds_a_map and ds_b_map:
                        root_cause = (
                            f"Dataset divergence: '{paper_a.title}' evaluated on {list(ds_a_map.values())}, "
                            f"whereas '{paper_b.title}' evaluated on {list(ds_b_map.values())}."
                        )
                        resolution = (
                            "Evaluate both approaches across both datasets to quantify domain sensitivity."
                        )
                        confidence = 0.82
                    else:
                        root_cause = "Differing experimental benchmarks or task formulation."
                        resolution = "Benchmark both pipelines on a standardized evaluation suite."
                        confidence = 0.75

                    pairs.append(
                        ContradictionPair(
                            paper_a=paper_a.title,
                            paper_b=paper_b.title,
                            topic=f"{norm_key.title()} (Delta: {delta:.2f})",
                            claim_a=f"Reports {raw_key_a} = {raw_val_a}",
                            claim_b=f"Reports {raw_key_b} = {raw_val_b}",
                            severity=ContradictionSeverity.DIRECT_EMPIRICAL,
                            confidence=confidence,
                            root_cause=root_cause,
                            resolution_hypothesis=resolution,
                        )
                    )
        return pairs

    def _check_limitation_collisions(
        self,
        paper_a: ReaderResponse,
        paper_b: ReaderResponse,
    ) -> list[ContradictionPair]:
        pairs: list[ContradictionPair] = []

        # Compare Paper A limitations against Paper B approach
        b_approach_tokens = _tokenize_meaningful(paper_b.methodology.approach)
        for lim in paper_a.limitations:
            lim_tokens = _tokenize_meaningful(lim)
            overlap = lim_tokens.intersection(b_approach_tokens)
            if len(overlap) >= 3:
                pairs.append(
                    ContradictionPair(
                        paper_a=paper_a.title,
                        paper_b=paper_b.title,
                        topic=f"Methodology Clash: {', '.join(sorted(overlap)[:3])}",
                        claim_a=f"Identifies limitation: {lim}",
                        claim_b=f"Relies on approach: {paper_b.methodology.approach}",
                        severity=ContradictionSeverity.LIMITATION_COLLISION,
                        confidence=0.85,
                        root_cause="Paper A highlights vulnerability in Paper B's core architectural pattern.",
                        resolution_hypothesis="Investigate whether Paper B mitigates the specific failure conditions noted in Paper A.",
                    )
                )

        # Compare Paper B limitations against Paper A approach
        a_approach_tokens = _tokenize_meaningful(paper_a.methodology.approach)
        for lim in paper_b.limitations:
            lim_tokens = _tokenize_meaningful(lim)
            overlap = lim_tokens.intersection(a_approach_tokens)
            if len(overlap) >= 3:
                pairs.append(
                    ContradictionPair(
                        paper_a=paper_b.title,
                        paper_b=paper_a.title,
                        topic=f"Methodology Clash: {', '.join(sorted(overlap)[:3])}",
                        claim_a=f"Identifies limitation: {lim}",
                        claim_b=f"Relies on approach: {paper_a.methodology.approach}",
                        severity=ContradictionSeverity.LIMITATION_COLLISION,
                        confidence=0.85,
                        root_cause="Paper B highlights vulnerability in Paper A's core architectural pattern.",
                        resolution_hypothesis="Investigate whether Paper A mitigates the specific failure conditions noted in Paper B.",
                    )
                )

        return pairs

    def _check_qualitative_claim_conflicts(
        self,
        paper_a: ReaderResponse,
        paper_b: ReaderResponse,
    ) -> list[ContradictionPair]:
        pairs: list[ContradictionPair] = []
        findings_a = paper_a.results.primary_findings or []
        findings_b = paper_b.results.primary_findings or []

        for fa in findings_a:
            tokens_a = _tokenize_meaningful(fa)
            has_pos_a = any(t in POSITIVE_POLARITY_TERMS for t in tokens_a)
            has_neg_a = any(t in NEGATIVE_POLARITY_TERMS for t in tokens_a)

            for fb in findings_b:
                tokens_b = _tokenize_meaningful(fb)
                has_pos_b = any(t in POSITIVE_POLARITY_TERMS for t in tokens_b)
                has_neg_b = any(t in NEGATIVE_POLARITY_TERMS for t in tokens_b)

                shared_concepts = tokens_a.intersection(tokens_b) - (
                    POSITIVE_POLARITY_TERMS | NEGATIVE_POLARITY_TERMS
                )

                # Conflicting polarity on shared entity/topic
                is_conflicting = (has_pos_a and has_neg_b) or (
                    has_neg_a and has_pos_b
                )

                if is_conflicting and len(shared_concepts) >= 2:
                    topic_str = ", ".join(sorted(shared_concepts)[:3])
                    pairs.append(
                        ContradictionPair(
                            paper_a=paper_a.title,
                            paper_b=paper_b.title,
                            topic=f"Qualitative Conflict: {topic_str}",
                            claim_a=fa,
                            claim_b=fb,
                            severity=ContradictionSeverity.QUALITATIVE_CONFLICT,
                            confidence=0.78,
                            root_cause=f"Opposing polarity regarding '{topic_str}'.",
                            resolution_hypothesis="Isolate environmental variables and benchmark under standardized evaluation metrics.",
                        )
                    )
        return pairs
