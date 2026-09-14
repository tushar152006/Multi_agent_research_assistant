import os
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient

from backend.api.main import app
from backend.core.config import get_settings


class PdfUploadTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.env_patcher = patch.dict(os.environ, {"LLM_PROVIDER": "heuristic"})
        cls.env_patcher.start()
        get_settings.cache_clear()
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.env_patcher.stop()
        get_settings.cache_clear()

    def test_upload_pdf_extracts_text_and_runs_pipeline(self) -> None:
        raw_text_content = b"Attention Is All You Need. The dominant sequence transduction models are based on complex recurrent or convolutional neural networks that include an encoder and a decoder. The best performing models also connect the encoder and decoder through an attention mechanism. We propose a new simple network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely."

        response = self.client.post(
            "/api/v1/research/upload-pdf?title=Attention%20Paper",
            content=raw_text_content,
            headers={"Content-Type": "application/pdf"},
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["query"], "Document: Attention Paper")
        self.assertIsNotNone(data["session_id"])
        self.assertTrue(len(data["reader_outputs"]) > 0)
        self.assertIsNotNone(data["analysis"])
        self.assertIsNotNone(data["critique"])
        self.assertIsNotNone(data["implementation_plan"])

    def test_upload_empty_pdf_rejected(self) -> None:
        response = self.client.post(
            "/api/v1/research/upload-pdf",
            content=b"",
            headers={"Content-Type": "application/pdf"},
        )
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
