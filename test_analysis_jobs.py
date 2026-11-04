"""Check that slow document analysis does not block job creation."""

import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import business.analysis_jobs as analysis_jobs


class AnalysisJobTests(unittest.TestCase):
    def test_submit_returns_while_analysis_is_running(self):
        started = threading.Event()
        release = threading.Event()

        def slow_analysis(path, *, semantic, threshold, on_blocks=None):
            self.assertEqual(Path(path).read_bytes(), b"sample document")
            started.set()
            self.assertTrue(release.wait(3))
            return {"file": Path(path).name, "chunk_count": 2}

        try:
            with patch("business.analysis_jobs.chunk_file", side_effect=slow_analysis), \
                 patch("business.analysis_jobs.receive_rfp", return_value={"id": "stored-doc"}), \
                 patch("business.analysis_jobs.summarize_rfp", return_value="# Summary"):
                job_id = analysis_jobs.submit("sample.docx", b"sample document", True, 0.85)
                self.assertTrue(started.wait(3))
                self.assertEqual(analysis_jobs.get(job_id)["status"], "running")
                release.set()
                for _ in range(30):
                    job = analysis_jobs.get(job_id)
                    if job and job["status"] == "done":
                        break
                    time.sleep(0.05)
                self.assertEqual(job["result"], {"file": "sample.docx", "chunk_count": 2,
                                                  "stored_document_id": "stored-doc"})
        finally:
            release.set()
