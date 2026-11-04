"""Store every RFP analysis upload with its original bytes and summary."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from database.backend import use_mysql
from database.tag_store import database_path


def _connect(path: Path | None = None) -> sqlite3.Connection:
    target = path or database_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(target)
    connection.row_factory = sqlite3.Row
    connection.execute("""
        CREATE TABLE IF NOT EXISTS input_documents (
            id TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            summary_md TEXT NOT NULL,
            content BLOB NOT NULL,
            size_bytes INTEGER NOT NULL,
            added_at TEXT NOT NULL
        )
    """)
    return connection


def save_input(filename: str, content: bytes, summary_md: str, path: Path | None = None) -> dict:
    if path is None and use_mysql():
        from database.mysql_documents import save_document
        return save_document("rfp", filename, content, summary_md)
    document_id = uuid4().hex
    added_at = datetime.now(timezone.utc).isoformat()
    with _connect(path) as connection:
        connection.execute(
            "INSERT INTO input_documents (id, filename, summary_md, content, size_bytes, added_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (document_id, filename, summary_md, content, len(content), added_at),
        )
    return {"id": document_id, "filename": filename, "description_md": summary_md,
            "size_bytes": len(content), "added_at": added_at}


def list_inputs(path: Path | None = None) -> list[dict]:
    if path is None and use_mysql():
        from database.mysql_documents import list_documents
        return list_documents("rfp")
    with _connect(path) as connection:
        rows = connection.execute(
            "SELECT id, filename, summary_md AS description_md, size_bytes, added_at "
            "FROM input_documents ORDER BY added_at, id"
        ).fetchall()
    return [dict(row) for row in rows]


def get_input(document_id: str, path: Path | None = None) -> dict | None:
    if path is None and use_mysql():
        from database.mysql_documents import get_document
        return get_document("rfp", document_id)
    with _connect(path) as connection:
        row = connection.execute("SELECT * FROM input_documents WHERE id = ?", (document_id,)).fetchone()
    return dict(row) if row else None


def update_input_summary(document_id: str, summary_md: str, path: Path | None = None) -> bool:
    if path is None and use_mysql():
        from database.mysql_documents import update_summary
        return update_summary("rfp", document_id, summary_md)
    with _connect(path) as connection:
        cursor = connection.execute(
            "UPDATE input_documents SET summary_md = ? WHERE id = ?", (summary_md, document_id)
        )
    return cursor.rowcount > 0
