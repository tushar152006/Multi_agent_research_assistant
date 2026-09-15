from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from backend.core.citation_grounding import (
    GroundedClaim,
    GroundedChunk,
    GroundingVerificationResult,
    CitationGroundingEngine,
    extract_grounded_chunks,
)


class CitationAuditor:
    """Converts synthesis findings into grounded and audited claims."""

    def __init__(
        self,
        engine: CitationGroundingEngine | None = None,
    ) -> None:
        self.engine = engine or CitationGroundingEngine()

    def collect_chunks(self, reader_outputs: Any) -> list[GroundedChunk]:
        chunks = extract_grounded_chunks(reader_outputs)

        unique_chunks: dict[str, GroundedChunk] = {}
        for chunk in chunks:
            unique_chunks[chunk.chunk_id] = chunk

        return list(unique_chunks.values())

    def audit(
        self,
        reader_outputs: Any,
        findings: Iterable[dict[str, str] | object],
    ) -> GroundingVerificationResult:
        source_chunks = self.collect_chunks(reader_outputs)
        claims = self.build_claims(findings, source_chunks)
        return self.engine.verify_synthesis(claims, source_chunks)

    def build_claims(
        self,
        findings: Iterable[dict[str, str] | object],
        source_chunks: list[GroundedChunk],
    ) -> list[GroundedClaim]:
        claims: list[GroundedClaim] = []

        for finding in findings:
            claim_text, category = self._read_finding(finding)
            if not claim_text.strip():
                continue
            claims.append(
                self.engine.anchor_claim(
                    claim=claim_text,
                    category=category,
                    candidate_chunks=source_chunks,
                )
            )

        return claims

    def qualify_analysis(
        self,
        analysis: Any,
        audit_result: GroundingVerificationResult,
    ) -> Any:
        """Explicitly qualify any consensus or theme finding that lacks verified grounding proof."""
        unsupported = set(audit_result.unsupported_claims)
        if not unsupported or not hasattr(analysis, "consensus"):
            return analysis

        qualified_consensus: list[str] = []
        for item in getattr(analysis, "consensus", []):
            if item in unsupported:
                qualified_consensus.append(f"[Unverified Evidence] {item}")
            else:
                qualified_consensus.append(item)

        qualified_themes: list[str] = []
        for theme in getattr(analysis, "themes", []):
            if theme in unsupported:
                qualified_themes.append(f"[Preliminary] {theme}")
            else:
                qualified_themes.append(theme)

        return analysis.model_copy(
            update={
                "consensus": qualified_consensus,
                "themes": qualified_themes,
            }
        )

    def _read_finding(
        self,
        finding: dict[str, str] | object,
    ) -> tuple[str, str]:
        if isinstance(finding, dict):
            claim_text = (
                finding.get("claim_text")
                or finding.get("claim")
                or finding.get("text")
                or ""
            )
            category = finding.get("category") or "theme"
            return str(claim_text), str(category)

        claim_text = (
            getattr(finding, "claim_text", None)
            or getattr(finding, "claim", None)
            or getattr(finding, "text", None)
            or ""
        )
        category = getattr(finding, "category", None) or "theme"

        return str(claim_text), str(category)
