import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from description import describe_file
from library_match import match_library
from library_store import add_file, get_file, list_files, update_description


SAMPLES = Path(__file__).parent / "samples"


class FakeEmbedder:
    def encode(self, texts, normalize_embeddings=False):
        return [[1.0, 0.0] if "prototype" in text.lower() else [0.0, 1.0] for text in texts]


class LibraryTests(unittest.TestCase):
    def test_markdown_description_is_generated_from_content(self):
        description = describe_file(SAMPLES / "sample.docx")
        self.assertTrue(description.startswith("# sample.docx"))
        self.assertIn("prototype", description.lower())

    def test_store_file_and_description(self):
        with TemporaryDirectory() as folder:
            db = Path(folder) / "library.sqlite3"
            payload = (SAMPLES / "sample.pdf").read_bytes()
            saved = add_file("sample.pdf", payload, "# Prototype\nEvidence of a working prototype.", db)
            self.assertEqual(len(list_files(db)), 1)
            self.assertEqual(get_file(saved["id"], db)["content"], payload)
            self.assertTrue(update_description(saved["id"], "# Updated description", db))
            self.assertEqual(list_files(db)[0]["description_md"], "# Updated description")

    def test_auto_and_manual_choose_stored_file(self):
        chunk = {"id": "a", "file": "request.docx", "pages": [], "section_path": [],
                 "labels": {"topics": ["Prototype"]}, "requirement_tier": "approved",
                 "blocks": [{"kind": "paragraph", "text": "The supplier must deliver a working prototype."}]}
        with TemporaryDirectory() as folder:
            db = Path(folder) / "library.sqlite3"
            saved = add_file("sample.pdf", (SAMPLES / "sample.pdf").read_bytes(), "# Prototype\nShows a working prototype.", db)
            auto = match_library([chunk], db_path=db, embedder=FakeEmbedder())
            self.assertEqual(auto["requirements"][0]["selected_files"][0]["id"], saved["id"])
            self.assertEqual(auto["counts"]["matched"], 1)
            manual = match_library([chunk], mode="manual", manual_ids=[saved["id"]], db_path=db, embedder=FakeEmbedder())
            self.assertEqual(manual["requirements"][0]["selected_files"][0]["id"], saved["id"])


if __name__ == "__main__":
    unittest.main()
