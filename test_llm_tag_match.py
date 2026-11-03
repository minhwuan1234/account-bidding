import json
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from library_store import add_file
from llm_tag_match import api_key, approved_tag_groups, has_api_key, match_one_tag


SAMPLES = Path(__file__).parent / "samples"


class LLMTagTests(unittest.TestCase):
    def test_server_reads_named_secret_from_environment(self):
        with patch.dict(os.environ, {"OPEN_AI_API_KEY": "test-key", "OPENAI_API_KEY": ""}):
            self.assertTrue(has_api_key())

    def test_local_key_file_is_read_without_restart(self):
        with TemporaryDirectory() as folder:
            config = Path(folder) / "local_api_key.py"
            with patch.dict(os.environ, {"OPEN_AI_API_KEY": "", "OPENAI_API_KEY": ""}), \
                 patch("llm_tag_match.__file__", str(Path(folder) / "llm_tag_match.py")):
                config.write_text('OPEN_AI_API_KEY = "first-key"\n', encoding="utf-8")
                self.assertEqual(api_key(), "first-key")
                config.write_text('OPEN_AI_API_KEY = "second-key"\n', encoding="utf-8")
                self.assertEqual(api_key(), "second-key")

    def test_only_approved_chunks_group_under_tag(self):
        chunks = [
            {"id": "a", "file": "a.docx", "text": "First text", "labels": {"topics": ["Scope"]}, "requirement_tier": "approved"},
            {"id": "b", "file": "a.docx", "text": "Second text", "labels": {"topics": ["Scope"]}, "requirement_tier": "approved"},
            {"id": "c", "file": "a.docx", "text": "Rejected", "labels": {"topics": ["Other"]}, "requirement_tier": "reject"},
        ]
        groups = approved_tag_groups(chunks)
        self.assertEqual(len(groups), 1)
        self.assertIn("First text", groups[0]["full_text"])
        self.assertIn("Second text", groups[0]["full_text"])
        self.assertNotIn("Rejected", groups[0]["full_text"])

    def test_model_file_ids_are_validated_and_text_kept(self):
        chunk = {"id": "a", "file": "rfp.docx", "text": "The supplier must deliver a working prototype.",
                 "pages": [], "section_path": [], "labels": {"topics": ["Prototype"]}, "requirement_tier": "approved",
                 "blocks": [{"kind": "paragraph", "text": "The supplier must deliver a working prototype."}]}
        with TemporaryDirectory() as folder:
            db = Path(folder) / "library.sqlite3"
            saved = add_file("sample.pdf", (SAMPLES / "sample.pdf").read_bytes(), "Shows a prototype.", db)

            def requester(body):
                self.assertFalse(body["store"])
                self.assertEqual(body["text"]["format"]["type"], "json_schema")
                answer = {"matches": [
                    {"file_id": saved["id"], "verdict": "match", "reason": "Có prototype."},
                    {"file_id": "invented", "verdict": "match", "reason": "Invalid ID."},
                ]}
                return {"status": "completed", "model": "gpt-6-luna", "usage": {"input_tokens": 1000, "output_tokens": 200}, "output": [{"content": [{"type": "output_text", "text": json.dumps(answer)}]}]}

            result = match_one_tag([chunk], db_path=db, requester=requester)
            self.assertEqual(result["tag"], "Prototype")
            self.assertIn("must deliver", result["full_text"])
            self.assertEqual([item["file_id"] for item in result["suggestions"]], [saved["id"]])
            self.assertNotIn("comparison", result)
            self.assertEqual(result["usage"]["input_tokens"], 1000)
            self.assertAlmostEqual(result["usage"]["estimated_cost_usd"], 0.0002)


if __name__ == "__main__":
    unittest.main()
