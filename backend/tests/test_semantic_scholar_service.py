import unittest

from backend.services.semantic_scholar_service import SemanticScholarService


SAMPLE_SEMANTIC_SCHOLAR_RESPONSE = {
    "data": [
        {
            "title": "Scientific Discovery with Multi-Agent Systems",
            "abstract": "A study of agent collaboration for scientific workflows.",
            "paperId": "abc123",
            "url": "https://www.semanticscholar.org/paper/abc123",
            "authors": [{"name": "Jane Doe"}, {"name": "John Roe"}],
        }
    ]
}


class SemanticScholarServiceTestCase(unittest.TestCase):
    def test_parse_response_extracts_papers(self) -> None:
        service = SemanticScholarService()

        papers = service.parse_response(SAMPLE_SEMANTIC_SCHOLAR_RESPONSE)

        self.assertEqual(len(papers), 1)
        self.assertEqual(
            papers[0].title,
            "Scientific Discovery with Multi-Agent Systems",
        )
        self.assertEqual(papers[0].authors, ["Jane Doe", "John Roe"])
        self.assertEqual(papers[0].paper_id, "abc123")


if __name__ == "__main__":
    unittest.main()
