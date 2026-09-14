from __future__ import annotations

import asyncio
import logging
from typing import Sequence

from backend.agents.base_agent import BaseAgent
from backend.core.config import get_settings
from backend.core.contradiction_matrix import (
    ContradictionMatrixEngine,
    ContradictionMatrixResult,
)
from backend.core.llm import LLMService, build_llm_service
from backend.models.schemas import ReaderResponse

logger = logging.getLogger(__name__)


class ContradictionAgent(BaseAgent[Sequence[ReaderResponse], ContradictionMatrixResult]):
    """Agent responsible for cross-paper contradiction and tension matrix generation."""

    name = "contradiction_agent"

    def __init__(
        self,
        engine: ContradictionMatrixEngine | None = None,
        llm_service: LLMService | None = None,
        llm_provider: str | None = None,
    ) -> None:
        settings = get_settings()
        self.engine = engine or ContradictionMatrixEngine()
        self._llm_provider = llm_provider or settings.llm_provider
        self.llm_service = llm_service or build_llm_service(
            provider=self._llm_provider,
            ollama_base_url=settings.ollama_base_url,
            ollama_model=settings.ollama_model,
        )

    async def run(
        self,
        reader_outputs: Sequence[ReaderResponse],
    ) -> ContradictionMatrixResult:
        """Analyze reader outputs across all ingested papers and build contradiction matrix."""
        logger.info(
            "Running ContradictionAgent across %d papers.", len(reader_outputs)
        )
        matrix = self.engine.build_matrix(reader_outputs)

        # If an LLM provider is active and tensions were detected, enrich key debates
        if self._llm_provider == "ollama" and matrix.tensions:
            try:
                enriched_debates = await self._enrich_debates_with_llm(matrix)
                if enriched_debates:
                    matrix.key_open_debates = enriched_debates
            except Exception:
                logger.warning(
                    "LLM debate enrichment failed; falling back to deterministic synthesis.",
                    exc_info=True,
                )

        return matrix

    async def _enrich_debates_with_llm(
        self,
        matrix: ContradictionMatrixResult,
    ) -> list[str] | None:
        tensions_summary = "\n".join(
            f"- [{t.severity.value}] {t.paper_a} vs {t.paper_b}: {t.topic}. Root cause: {t.root_cause}"
            for t in matrix.tensions[:5]
        )
        prompt = (
            "You are a meta-scientific reviewer. Synthesize the following empirical tensions "
            "between research papers into 3-5 concise, piercing open debate questions for researchers:\n\n"
            f"{tensions_summary}\n\n"
            "Output each debate question on a new line starting with '- '."
        )
        try:
            response = await asyncio.wait_for(
                self.llm_service.generate(prompt, max_tokens=100),
                timeout=30.0,
            )
            lines = [
                line.lstrip("- *").strip()
                for line in response.splitlines()
                if line.strip().startswith(("-", "*"))
            ]
            return lines if lines else None
        except (Exception, asyncio.CancelledError, asyncio.TimeoutError) as exc:
            logger.warning("LLM debate generation timed out or failed: %s", exc)
            return None
