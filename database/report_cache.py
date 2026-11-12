"""Persist reusable generated reports, keyed by file and analysis versions."""
from __future__ import annotations

import json
from database.backend import use_mysql
from database.bid_store import _sqlite
from database.mysql_connection import connect as mysql_connect


def _schema(connection, mysql):
    query = ("CREATE TABLE IF NOT EXISTS report_cache (cache_key CHAR(64) PRIMARY KEY, report_json LONGTEXT NOT NULL) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4" if mysql else
             "CREATE TABLE IF NOT EXISTS report_cache (cache_key TEXT PRIMARY KEY, report_json TEXT NOT NULL)")
    if mysql:
        with connection.cursor() as cursor:
            cursor.execute(query)
        connection.commit()
    else:
        connection.execute(query)


def get_report(key):
    mysql = use_mysql()
    with (mysql_connect() if mysql else _sqlite()) as connection:
        _schema(connection, mysql)
        if mysql:
            with connection.cursor() as cursor:
                cursor.execute('SELECT report_json FROM report_cache WHERE cache_key=%s', (key,))
                row = cursor.fetchone()
                value = row[0] if row else None
        else:
            row = connection.execute('SELECT report_json FROM report_cache WHERE cache_key=?', (key,)).fetchone()
            value = row[0] if row else None
    return json.loads(value) if value else None


def save_report(key, report):
    mysql = use_mysql()
    value = json.dumps(report, ensure_ascii=False)
    with (mysql_connect() if mysql else _sqlite()) as connection:
        _schema(connection, mysql)
        if mysql:
            with connection.cursor() as cursor:
                cursor.execute('INSERT INTO report_cache (cache_key, report_json) VALUES (%s,%s) ON DUPLICATE KEY UPDATE report_json=VALUES(report_json)', (key, value))
            connection.commit()
        else:
            connection.execute('INSERT INTO report_cache (cache_key, report_json) VALUES (?,?) ON CONFLICT(cache_key) DO UPDATE SET report_json=excluded.report_json', (key, value))
