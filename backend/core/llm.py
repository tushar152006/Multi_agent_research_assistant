from __future__ import annotations

from abc import ABC, abstractmethod

import httpx


class LLMService(ABC):
    """Abstract interface for optional text generation backends."""

    @abstractmethod
    async def generate(self, prompt: str, max_tokens: int = 120) -> str:
        """Generate text for a prompt."""


class HeuristicLLMService(LLMService):
    """Placeholder provider used when no local model is configured."""

    async def generate(self, prompt: str, max_tokens: int = 120) -> str:
        raise RuntimeError("Heuristic provider does not support text generation.")


class OllamaService(LLMService):
    """Minimal Ollama client for local text generation."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3.1:8b",
        timeout: float = 120.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self._client = client

    async def generate(self, prompt: str, max_tokens: int = 120) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": 0.2,
                "top_p": 0.9,
            },
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


class GroqService(LLMService):
    """Ultra-fast Groq LLM client using httpx targeting OpenAI-compatible chat API."""

    GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(
        self,
        api_key: str,
        model: str = "openai/gpt-oss-120b",
        timeout: float = 30.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.api_key = api_key.strip()
        self.model = model
        self.timeout = timeout
        self._client = client

    async def generate(self, prompt: str, max_tokens: int = 250) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a precise, rigorous scientific research assistant. Respond directly without conversational filler.",
                },
                {"role": "user", "content": prompt},
            ],
            "max_tokens": max_tokens,
            "temperature": 0.2,
        }

        if self._client is not None:
            response = await self._client.post(
                self.GROQ_API_URL,
                headers=headers,
                json=payload,
            )
        else:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.GROQ_API_URL,
                    headers=headers,
                    json=payload,
                )

        response.raise_for_status()
        body = response.json()
        choices = body.get("choices", [])
        if not choices:
            return ""
        return str(choices[0].get("message", {}).get("content", "")).strip()


def build_llm_service(
    provider: str,
    ollama_base_url: str = "http://localhost:11434",
    ollama_model: str = "llama3.1:latest",
    groq_api_key: str | None = None,
    groq_model: str = "openai/gpt-oss-120b",
) -> LLMService:
    normalized = (provider or "").strip().lower()

    if normalized == "groq" and groq_api_key:
        return GroqService(api_key=groq_api_key, model=groq_model)

    if normalized == "ollama":
        return OllamaService(
            base_url=ollama_base_url,
            model=ollama_model,
        )

    # If groq is requested or key exists in environment
    if groq_api_key:
        return GroqService(api_key=groq_api_key, model=groq_model)

    return HeuristicLLMService()
