"""Verify MySQL writes commit file metadata, summary, and binary parts."""

import unittest
from unittest.mock import MagicMock, patch

from database import mysql_documents


class MySQLDocumentTests(unittest.TestCase):
    def test_file_is_written_in_parts_and_transaction_commits(self):
        connection = MagicMock()
        connection.__enter__.return_value = connection
        cursor = connection.cursor.return_value.__enter__.return_value
        with patch("database.mysql_documents.connect", return_value=connection), \
             patch("database.mysql_documents._ensure_schema"), \
             patch.object(mysql_documents, "PART_SIZE", 4):
            saved = mysql_documents.save_document("rfp", "brief.pdf", b"abcdefghij", "# Brief")
        self.assertEqual(saved["size_bytes"], 10)
        self.assertEqual(saved["description_md"], "# Brief")
        self.assertEqual([call.args[1][2] for call in cursor.execute.call_args_list[1:]],
                         [b"abcd", b"efgh", b"ij"])
        connection.commit.assert_called_once()
        connection.rollback.assert_not_called()

    def test_failed_part_rolls_back(self):
        connection = MagicMock()
        connection.__enter__.return_value = connection
        cursor = connection.cursor.return_value.__enter__.return_value
        cursor.execute.side_effect = [None, RuntimeError("write failed")]
        with patch("database.mysql_documents.connect", return_value=connection), \
             patch("database.mysql_documents._ensure_schema"):
            with self.assertRaisesRegex(RuntimeError, "write failed"):
                mysql_documents.save_document("library", "book.pdf", b"bytes", "# Book")
        connection.rollback.assert_called_once()

    def test_unchanged_summary_still_counts_as_saved(self):
        connection = MagicMock()
        connection.__enter__.return_value = connection
        cursor = connection.cursor.return_value.__enter__.return_value
        cursor.rowcount = 0
        cursor.fetchone.return_value = (1,)
        with patch("database.mysql_documents.connect", return_value=connection), \
             patch("database.mysql_documents._ensure_schema"):
            self.assertTrue(mysql_documents.update_summary("library", "existing-id", "# Existing"))
        self.assertEqual(cursor.execute.call_count, 2)
        connection.commit.assert_called_once()
