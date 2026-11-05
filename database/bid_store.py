"""Persist bid workspaces and their report/file selections."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from database.backend import use_mysql
from database.mysql_connection import connect as mysql_connect
from database.tag_store import database_path


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sqlite(path: Path | None = None) -> sqlite3.Connection:
    target = path or database_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(target)
    connection.row_factory = sqlite3.Row
    connection.execute("""
        CREATE TABLE IF NOT EXISTS bid_history (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            document_count INTEGER NOT NULL,
            missing_count INTEGER NOT NULL,
            documents_json TEXT NOT NULL,
            matches_json TEXT NOT NULL,
            report_json TEXT NOT NULL
        )
    """)
    return connection


def _mysql_schema(connection) -> None:
    with connection.cursor() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bid_history (
                id CHAR(32) PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                status VARCHAR(24) NOT NULL,
                created_at VARCHAR(40) NOT NULL,
                updated_at VARCHAR(40) NOT NULL,
                document_count INT UNSIGNED NOT NULL,
                missing_count INT UNSIGNED NOT NULL,
                documents_json LONGTEXT NOT NULL,
                matches_json LONGTEXT NOT NULL,
                report_json LONGTEXT NOT NULL,
                INDEX bids_by_date (created_at, id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
    connection.commit()


def _decode(row: dict, full: bool = False) -> dict:
    item = {"id": row["id"], "title": row["title"], "status": row["status"],
            "created_at": row["created_at"], "updated_at": row["updated_at"],
            "document_count": row["document_count"], "missing_count": row["missing_count"]}
    if full:
        item.update(documents=json.loads(row["documents_json"]),
                    matches=json.loads(row["matches_json"]), report=json.loads(row["report_json"]))
    return item


def create_bid(title: str, path: Path | None = None) -> dict:
    title = title.strip()[:255]
    if not title:
        raise ValueError("Thiếu tên bid")
    bid_id, now = uuid4().hex, _now()
    values = (bid_id, title, "processing", now, now, 0, 0, "[]", "null", "null")
    if path is None and use_mysql():
        with mysql_connect() as connection:
            _mysql_schema(connection)
            with connection.cursor() as cursor:
                cursor.execute("INSERT INTO bid_history VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", values)
            connection.commit()
    else:
        with _sqlite(path) as connection:
            connection.execute("INSERT INTO bid_history VALUES (?,?,?,?,?,?,?,?,?,?)", values)
    return {"id": bid_id, "title": title, "status": "processing", "created_at": now,
            "updated_at": now, "document_count": 0, "missing_count": 0}


def list_bids(path: Path | None = None) -> list[dict]:
    if path is None and use_mysql():
        with mysql_connect() as connection:
            _mysql_schema(connection)
            with connection.cursor() as cursor:
                cursor.execute("SELECT id,title,status,created_at,updated_at,document_count,missing_count "
                               "FROM bid_history ORDER BY created_at DESC, id DESC")
                columns = [entry[0] for entry in cursor.description]
                rows = [dict(zip(columns, values)) for values in cursor.fetchall()]
    else:
        with _sqlite(path) as connection:
            rows = [dict(row) for row in connection.execute(
                "SELECT id,title,status,created_at,updated_at,document_count,missing_count "
                "FROM bid_history ORDER BY created_at DESC, id DESC")]
    return [_decode(row) for row in rows]


def get_bid(bid_id: str, path: Path | None = None) -> dict | None:
    if path is None and use_mysql():
        with mysql_connect() as connection:
            _mysql_schema(connection)
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM bid_history WHERE id = %s", (bid_id,))
                values = cursor.fetchone()
                row = dict(zip((entry[0] for entry in cursor.description), values)) if values else None
    else:
        with _sqlite(path) as connection:
            record = connection.execute("SELECT * FROM bid_history WHERE id = ?", (bid_id,)).fetchone()
            row = dict(record) if record else None
    return _decode(row, True) if row else None


def update_bid(bid_id: str, *, title: str, status: str, documents: list,
               matches: dict | None, report: dict | None, path: Path | None = None) -> dict | None:
    title = title.strip()[:255]
    if not title or status not in {"processing", "complete", "partial", "error"}:
        raise ValueError("Dữ liệu bid không hợp lệ")
    if not isinstance(documents, list) or (matches is not None and not isinstance(matches, dict)) or (
            report is not None and not isinstance(report, dict)):
        raise ValueError("Dữ liệu bid không hợp lệ")
    missing_count = sum(not entry.get("file_ids") for entry in (report or {}).get("requirements", []))
    updated_at = _now()
    values = (title, status, updated_at, len(documents), missing_count, json.dumps(documents, ensure_ascii=False),
              json.dumps(matches, ensure_ascii=False), json.dumps(report, ensure_ascii=False), bid_id)
    if path is None and use_mysql():
        with mysql_connect() as connection:
            _mysql_schema(connection)
            with connection.cursor() as cursor:
                cursor.execute("UPDATE bid_history SET title=%s,status=%s,updated_at=%s,"
                               "document_count=%s,missing_count=%s,documents_json=%s,matches_json=%s,"
                               "report_json=%s WHERE id=%s", values)
                found = cursor.rowcount > 0
            connection.commit()
    else:
        with _sqlite(path) as connection:
            cursor = connection.execute("UPDATE bid_history SET title=?,status=?,updated_at=?,"
                                        "document_count=?,missing_count=?,documents_json=?,matches_json=?,"
                                        "report_json=? WHERE id=?", values)
            found = cursor.rowcount > 0
    return {"id": bid_id, "title": title, "status": status, "updated_at": updated_at,
            "document_count": len(documents), "missing_count": missing_count} if found else None
