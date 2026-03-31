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


if __name__ == "__main__":
    unittest.main()
