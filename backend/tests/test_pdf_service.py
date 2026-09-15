import unittest
from pathlib import Path

from backend.services.pdf_service import PdfService


class PdfServiceTestCase(unittest.TestCase):
    def test_normalize_text_collapses_spacing(self) -> None:
        service = PdfService()

        result = service.normalize_text("Line 1\r\n\r\n\r\nLine   2\t\ttext")

        self.assertEqual(result, "Line 1\n\nLine 2 text")

    def test_extract_text_from_file_reads_utf8_text(self) -> None:
        service = PdfService()
        fixtures_dir = Path("backend/tests/.fixtures")
        fixtures_dir.mkdir(parents=True, exist_ok=True)
        file_path = fixtures_dir / "sample_reader_text.txt"
        file_path.write_text("Abstract\n\nSample paper text", encoding="utf-8")

        try:
            result = service.extract_text_from_file(file_path)
        finally:
            if file_path.exists():
                file_path.unlink()

        self.assertEqual(result, "Abstract\n\nSample paper text")

    def test_segment_sections_identifies_academic_headings(self) -> None:
        service = PdfService()
        sample_doc = (
            "Abstract\nThis paper proposes a new method for evaluation.\n\n"
            "Introduction\nRecent advances in deep learning have transformed AI.\n\n"
            "Methodology\nWe deploy a three-tier pipeline with cross-attention.\n\n"
            "Results\nOur model achieves 94.2% accuracy on the benchmark.\n\n"
            "Limitations\nEvaluation is restricted to English language corpora.\n"
        )
        sections = service.segment_sections(sample_doc)

        self.assertIn("abstract", sections)
        self.assertIn("introduction", sections)
        self.assertIn("methodology", sections)
        self.assertIn("results", sections)
        self.assertIn("discussion", sections)
        self.assertIn("94.2%", sections["results"])

    def test_extract_structured_document_from_raw_bytes(self) -> None:
        service = PdfService()
        raw_bytes = b"Abstract\nGrounding in empirical science.\n\nResults\nPrecision reaches 98%."
        doc = service.extract_structured_document(raw_bytes)

        self.assertEqual(len(doc.pages), 1)
        self.assertEqual(doc.pages[0].page_number, 1)
        self.assertIn("abstract", doc.sections)
        self.assertIn("results", doc.sections)


if __name__ == "__main__":
    unittest.main()
