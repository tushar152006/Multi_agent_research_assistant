import unittest

from backend.services.arxiv_service import ArxivService


SAMPLE_ARXIV_XML = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2401.12345v1</id>
    <title>
      Multi-Agent Planning for Research
    </title>
    <summary>
      This paper studies collaborative agent systems for research workflows.
    </summary>
    <author><name>Jane Doe</name></author>
    <author><name>John Roe</name></author>
  </entry>
</feed>
"""


class ArxivServiceTestCase(unittest.TestCase):
    def test_parse_response_extracts_papers(self) -> None:
        service = ArxivService()

        papers = service.parse_response(SAMPLE_ARXIV_XML)

        self.assertEqual(len(papers), 1)
        self.assertEqual(papers[0].title, "Multi-Agent Planning for Research")
        self.assertEqual(papers[0].authors, ["Jane Doe", "John Roe"])
        self.assertIn("collaborative agent systems", papers[0].summary)
        self.assertEqual(papers[0].entry_id, "http://arxiv.org/abs/2401.12345v1")


if __name__ == "__main__":
    unittest.main()
