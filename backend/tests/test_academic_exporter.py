import os
import unittest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient

from backend.api.main import app
from backend.core.config import get_settings
from backend.models.schemas import (
    MethodologySummary,
    PaperSummary,
    ReaderResponse,
    ResearchResponse,
    ResultsSummary,
)
from backend.services.academic_exporter import AcademicExporterService
from backend.storage.session_store import SessionStore


class AcademicExporterTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.env_patcher = patch.dict(os.environ, {"LLM_PROVIDER": "heuristic"})
        cls.env_patcher.start()
        get_settings.cache_clear()
        cls.client = TestClient(app)
        cls.store = SessionStore(get_settings().local_storage_path)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.env_patcher.stop()
        get_settings.cache_clear()

    def setUp(self) -> None:
        self.exporter = AcademicExporterService()
        self.sample_report = ResearchResponse(
            query="multi agent scientific literature review",
            query_type="deep_analysis",
            summary="This is an executive summary of findings.",
            papers=[
                PaperSummary(
                    title="Deep Learning Agents in Science",
                    authors=["Alice Walker", "Bob Marley"],
                    source="arXiv",
                    external_id="arxiv:2403.00123v1",
                    abstract="Studying multi-agent collaborative workflows in year 2024.",
                    relevance_score=92,
                )
            ],
            reader_outputs=[
                ReaderResponse(
                    title="Deep Learning Agents in Science",
                    problem="Scale",
                    methodology=MethodologySummary(approach="Agents", datasets=["D1"], metrics=["acc"]),
                    results=ResultsSummary(primary_findings=["Works well"], metrics={"acc": "95%"}),
                    limitations=["Compute cost"],
                    future_work=[],
                    extracted_sections={},
                )
            ],
            session_id="test-export-session-1234",
            execution_trace=[],
        )

    def test_generate_bibtex_creates_valid_entry(self) -> None:
        bibtex = self.exporter.generate_bibtex(self.sample_report)
        self.assertIn("@article{", bibtex)
        self.assertIn("Deep Learning Agents in Science", bibtex)
        self.assertIn("Alice Walker and Bob Marley", bibtex)
        self.assertIn("arXiv", bibtex)
        self.assertIn("2024", bibtex)

    def test_generate_markdown_report_structure(self) -> None:
        md = self.exporter.generate_markdown_report(self.sample_report)
        self.assertIn("# Systematic Literature Review:", md)
        self.assertIn("## 1. Executive Summary", md)
        self.assertIn("## 7. BibTeX References", md)
        self.assertIn("Deep Learning Agents in Science", md)

    def test_export_endpoints(self) -> None:
        import asyncio
        asyncio.run(self.store.save_report(self.sample_report))

        # Test BibTeX endpoint
        bib_res = self.client.get("/api/v1/research/test-export-session-1234/export/bibtex")
        self.assertEqual(bib_res.status_code, 200)
        self.assertEqual(bib_res.headers["content-type"], "application/x-bibtex")
        self.assertIn("@article{", bib_res.text)

        # Test Markdown endpoint
        md_res = self.client.get("/api/v1/research/test-export-session-1234/export/markdown")
        self.assertEqual(md_res.status_code, 200)
        self.assertEqual(md_res.headers["content-type"], "text/markdown; charset=utf-8")
        self.assertIn("# Systematic Literature Review:", md_res.text)


if __name__ == "__main__":
    unittest.main()
