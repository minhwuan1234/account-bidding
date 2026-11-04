import os
import unittest
from unittest.mock import MagicMock, patch

from database.mysql_connection import check_connection, connection_options


class MySQLConnectionTests(unittest.TestCase):
    def test_railway_url_decodes_credentials(self):
        with patch.dict(os.environ, {"MYSQL_URL": "mysql://user:p%40ss@mysql.railway.internal:3307/bids"}):
            options = connection_options()
        self.assertEqual(options["host"], "mysql.railway.internal")
        self.assertEqual(options["port"], 3307)
        self.assertEqual(options["password"], "p@ss")
        self.assertEqual(options["database"], "bids")

    def test_status_probes_database_without_exposing_credentials(self):
        connection = MagicMock()
        connection.__enter__.return_value = connection
        cursor = connection.cursor.return_value.__enter__.return_value
        with patch("database.mysql_connection.connection_options", return_value={"host": "example"}), \
             patch("database.mysql_connection.connect", return_value=connection):
            self.assertEqual(check_connection(), {"configured": True, "connected": True})
        cursor.execute.assert_called_once_with("SELECT 1")

    def test_missing_configuration_is_not_connected(self):
        with patch("database.mysql_connection.connection_options", return_value=None):
            self.assertEqual(check_connection(), {"configured": False, "connected": False})
