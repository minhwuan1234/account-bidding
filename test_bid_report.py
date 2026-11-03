import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from bid_report import generate_report
from library_store import add_file


SAMPLES = Path(__file__).parent / "samples"


class BidReportTests(unittest.TestCase):
    def test_report_keeps_only_grounded_requirements_and_existing_files(self):
        with TemporaryDirectory() as folder:
            db = Path(folder) / "library.sqlite3"
            saved = add_file("portfolio.pdf", (SAMPLES / "sample.pdf").read_bytes(), "Company portfolio and prototype projects.", db)
            documents = [{"file": "rfq.docx", "chunks": [
                {"id": "scope", "file": "rfq.docx", "text": "The project needs a prototype.",
                 "labels": {"topics": ["Project"]}, "requirement_tier": "considerable", "section_path": [], "pages": []},
                {"id": "req", "file": "rfq.docx", "text": "Submit a company portfolio.",
                 "labels": {"topics": ["Company portfolio"]}, "requirement_tier": "approved", "section_path": [], "pages": []},
            ]}]

            def requester(body):
                self.assertFalse(body["store"])
                self.assertEqual(body["text"]["format"]["type"], "json_schema")
                data = json.loads(body["input"])
                self.assertEqual(len(data["source_chunks"]), 2)
                answer = {
                    "title": "Prototype bid", "buyer": "", "source_language": "English", "overview": "Dự án prototype.",
                    "scope": [{"heading": "Mục tiêu", "detail": "Làm prototype.", "source_chunk_ids": ["scope"]}],
                    "scope_table": [{"item": "Prototype", "detail": "Làm prototype.", "source_chunk_ids": ["scope"]}],
                    "submission": "Nộp portfolio.", "evaluation_criteria": [], "deadlines": [],
                    "requirements": [
                        {"title": "Company portfolio", "detail": "Nộp portfolio", "category": "Giấy tờ", "tag": "Company portfolio",
                         "source_chunk_ids": ["req"], "file_ids": [saved["id"], "invented"], "reason": "Mô tả phù hợp"},
                        {"title": "Invented", "detail": "Không có nguồn", "category": "Khác", "tag": "Company portfolio",
                         "source_chunk_ids": ["missing"], "file_ids": [], "reason": ""},
                    ],
                    "questions": [],
                }
                return {"status": "completed", "model": "gpt-6-luna", "usage": {"input_tokens": 1000, "output_tokens": 200}, "output": [{"content": [{"type": "output_text", "text": json.dumps(answer)}]}]}

            report = generate_report(documents, [], db_path=db, requester=requester)
            self.assertEqual(len(report["requirements"]), 1)
            self.assertEqual(report["requirements"][0]["file_ids"], [saved["id"]])
            self.assertEqual(report["requirements"][0]["status"], "review")
            self.assertEqual(report["scope"][0]["source_chunk_ids"], ["scope"])
            self.assertEqual(report["scope_table"][0]["item"], "Prototype")
            self.assertAlmostEqual(report["usage"]["estimated_cost_usd"], 0.0002)
