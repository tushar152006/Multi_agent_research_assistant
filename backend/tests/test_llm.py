import unittest
from unittest.mock import AsyncMock

import httpx

from backend.core.llm import (
    GroqService,
    HeuristicLLMService,
    OllamaService,
    build_llm_service,
)


class LLMServiceTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_build_llm_service_returns_heuristic_by_default(self) -> None:
        service = build_llm_service(
            provider="heuristic",
            ollama_base_url="http://localhost:11434",
            ollama_model="llama3.1:8b",
        )

        self.assertIsInstance(service, HeuristicLLMService)

    async def test_ollama_service_reads_response_body(self) -> None:
        response = httpx.Response(
            200,
            json={"response": "Local summary from Ollama."},
            request=httpx.Request("POST", "http://localhost:11434/api/generate"),
        )
        client = AsyncMock()
        client.post = AsyncMock(return_value=response)
        service = OllamaService(client=client)

        result = await service.generate("Test prompt")

        self.assertEqual(result, "Local summary from Ollama.")

    async def test_groq_service_reads_chat_completions(self) -> None:
        response = httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "Ultra-fast response from Groq.",
                        }
                    }
                ]
            },
            request=httpx.Request(
                "POST", "https://api.groq.com/openai/v1/chat/completions"
            ),
        )
        client = AsyncMock()
        client.post = AsyncMock(return_value=response)
        service = GroqService(api_key="gsk_test123", client=client)

        result = await service.generate("Synthesize these findings")

        self.assertEqual(result, "Ultra-fast response from Groq.")
        client.post.assert_awaited_once()

    def test_build_llm_service_selects_groq(self) -> None:
        from backend.core.llm import GroqService

        service = build_llm_service(
            provider="groq",
            groq_api_key="gsk_mock_test_key",
            groq_model="llama-3.3-70b-versatile",
        )
        self.assertIsInstance(service, GroqService)
        self.assertEqual(service.api_key, "gsk_mock_test_key")
        self.assertEqual(service.model, "llama-3.3-70b-versatile")


if __name__ == "__main__":
    unittest.main()
