"""Uploads keep their bytes and extracted summary in local storage."""

import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from business.upload_service import receive_rfp, summarize_rfp
from database.input_store import get_input, list_inputs


SAMPLES = Path(__file__).parent / "samples"


class UploadStorageTests(unittest.TestCase):
    def test_rfp_file_and_summary_are_saved_together(self):
        with TemporaryDirectory() as folder:
            db = Path(folder) / "uploads.sqlite3"
            path = SAMPLES / "sample.docx"
            content = path.read_bytes()
            with patch.dict(os.environ, {"STRUCTURAL_CHUNKER_DB": str(db)}, clear=False):
                saved = receive_rfp(path.name, content)
                self.assertEqual(get_input(saved["id"])["content"], content)
                summary = summarize_rfp(saved["id"], path)
                self.assertIn("prototype", summary.lower())
                self.assertEqual(list_inputs()[0]["description_md"], summary)

    def test_railway_does_not_silently_fall_back_to_sqlite(self):
        with patch.dict(os.environ, {"RAILWAY_PROJECT_ID": "project", "MYSQL_URL": "",
                                  "MYSQLHOST": "", "MYSQLUSER": "", "MYSQLDATABASE": ""}):
            with self.assertRaisesRegex(RuntimeError, "MYSQL_URL"):
                receive_rfp("sample.pdf", b"pdf")
