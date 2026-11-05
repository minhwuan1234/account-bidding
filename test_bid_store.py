import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from database.bid_store import create_bid, get_bid, list_bids, update_bid


class BidStoreTests(unittest.TestCase):
    def test_bid_history_restores_report_and_selected_files(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "test.sqlite3"
            created = create_bid("RFP mẫu", path)
            self.assertEqual(list_bids(path)[0]["status"], "processing")
            documents = [{"file": "rfp.pdf", "chunks": [{"id": "rfp-1", "text": "Yêu cầu CV"}]}]
            report = {"title": "RFP mẫu", "requirements": [
                {"title": "CV", "file_ids": []}, {"title": "Portfolio", "file_ids": ["file-1"]}]}
            update_bid(created["id"], title="RFP mẫu", status="complete", documents=documents,
                       matches={"tag_matches": []}, report=report, path=path)
            self.assertEqual(list_bids(path)[0]["missing_count"], 1)
            restored = get_bid(created["id"], path)
            self.assertEqual(restored["documents"], documents)
            self.assertEqual(restored["report"], report)
            restored["report"]["requirements"][0]["file_ids"] = ["file-2"]
            update_bid(created["id"], title="RFP mẫu", status="complete",
                       documents=documents, matches=restored["matches"], report=restored["report"], path=path)
            self.assertEqual(list_bids(path)[0]["missing_count"], 0)
            self.assertEqual(get_bid(created["id"], path)["report"]["requirements"][0]["file_ids"], ["file-2"])


if __name__ == "__main__":
    unittest.main()
