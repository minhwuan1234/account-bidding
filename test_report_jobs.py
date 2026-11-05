"""Check that report jobs expose progress while processing continues."""

import threading
import time
import unittest
from unittest.mock import patch

import business.report_jobs as report_jobs


class ReportJobTests(unittest.TestCase):
    def test_progress_and_result_are_available_by_polling(self):
        started = threading.Event()
        release = threading.Event()

        def slow_report(documents, matches, *, on_progress):
            on_progress("running", "Tài liệu cần nộp (phần 1)")
            started.set()
            self.assertTrue(release.wait(3))
            on_progress("done", "Tài liệu cần nộp (phần 1)")
            return {"title": "RFP mẫu"}

        try:
            with patch("business.report_jobs.generate_report", side_effect=slow_report):
                job_id = report_jobs.submit([{"chunks": [{"id": "one"}]}], [])
                self.assertTrue(started.wait(3))
                current = report_jobs.get(job_id)
                self.assertEqual(current["status"], "running")
                self.assertTrue(any(event["message"] == "Tài liệu cần nộp (phần 1)"
                                    for event in current["events"]))
                release.set()
                for _ in range(40):
                    current = report_jobs.get(job_id)
                    if current and current["status"] == "done":
                        break
                    time.sleep(0.02)
                self.assertEqual(current["result"], {"title": "RFP mẫu"})
        finally:
            release.set()


if __name__ == "__main__":
    unittest.main()
