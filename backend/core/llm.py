from __future__ import annotations

from abc import ABC, abstractmethod

import httpx


class LLMService(ABC):
    """Abstract interface for optional text generation backends."""

    @abstractmethod
    async def generate(self, prompt: str) -> str:
        """Generate text for a prompt."""


class HeuristicLLMService(LLMService):
    """Placeholder provider used when no local model is configured."""

    async def generate(self, prompt: str) -> str:
        raise RuntimeError("Heuristic provider does not support text generation.")


class OllamaService(LLMService):
    """Minimal Ollama client for local text generation."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3.1:8b",
        timeout: float = 60.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self._client = client

    async def generate(self, prompt: str) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }

        if self._client is not None:
            response = await self._client.post(
                f"{self.base_url}/api/generate",
                json=payload,
            )
        else:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                )

        response.raise_for_status()
        body = response.json()
        return str(body.get("response", "")).strip()


def build_llm_service(
    provider: str,
    ollama_base_url: str,
    ollama_model: str,
) -> LLMService:
    normalized = provider.strip().lower()
    if normalized == "ollama":
        return OllamaService(
            base_url=ollama_base_url,
            model=ollama_model,
        )
    return HeuristicLLMService()
