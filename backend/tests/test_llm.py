import unittest
from unittest.mock import AsyncMock

import httpx

from backend.core.llm import HeuristicLLMService, OllamaService, build_llm_service


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


if __name__ == "__main__":
    unittest.main()
