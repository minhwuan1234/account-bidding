import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from business.description import describe_file
from database.library_store import add_file, delete_file, get_file, list_files, update_description


SAMPLES = Path(__file__).parent / "samples"


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

    def test_delete_only_selected_file_when_names_repeat(self):
        with TemporaryDirectory() as folder:
            db = Path(folder) / "library.sqlite3"
            first = add_file("portfolio.pdf", b"first", "# First", db)
            second = add_file("portfolio.pdf", b"second", "# Second", db)
            self.assertTrue(delete_file(first["id"], db))
            self.assertEqual([file["id"] for file in list_files(db)], [second["id"]])
            self.assertIsNone(get_file(first["id"], db))
            self.assertFalse(delete_file(first["id"], db))

if __name__ == "__main__":
    unittest.main()
