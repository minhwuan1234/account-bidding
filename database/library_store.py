"""Local SQLite library of reusable documents and their Markdown descriptions."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from database.backend import use_mysql
from database.tag_store import database_path


MAX_FILE_BYTES = 30 * 1024 * 1024
MAX_DESCRIPTION = 4000


def _connect(path: Path | None = None) -> sqlite3.Connection:
    target = path or database_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(target)
    connection.row_factory = sqlite3.Row
    connection.execute("""
        CREATE TABLE IF NOT EXISTS library_files (
            id TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            description_md TEXT NOT NULL,
            content BLOB NOT NULL,
            size_bytes INTEGER NOT NULL,
            added_at TEXT NOT NULL
        )
    """)
    return connection


def add_file(filename: str, content: bytes, description_md: str, path: Path | None = None) -> dict:
    filename = Path(filename).name
    if Path(filename).suffix.lower() not in (".pdf", ".docx"):
        raise ValueError("Chỉ hỗ trợ PDF và DOCX")
    if not content or len(content) > MAX_FILE_BYTES:
        raise ValueError("File rỗng hoặc vượt quá 30 MB")
    description_md = description_md.strip()
    if not description_md or len(description_md) > MAX_DESCRIPTION:
        raise ValueError("Mô tả Markdown phải có 1–4000 ký tự")
    if path is None and use_mysql():
        from database.mysql_documents import save_document
        return save_document("library", filename, content, description_md)
    file_id = uuid4().hex
    added_at = datetime.now(timezone.utc).isoformat()
    with _connect(path) as connection:
        connection.execute(
            "INSERT INTO library_files (id, filename, description_md, content, size_bytes, added_at) VALUES (?, ?, ?, ?, ?, ?)",
            (file_id, filename, description_md, content, len(content), added_at),
        )
    return {"id": file_id, "filename": filename, "description_md": description_md, "size_bytes": len(content), "added_at": added_at}


def list_files(path: Path | None = None) -> list[dict]:
    if path is None and use_mysql():
        from database.mysql_documents import list_documents
        return list_documents("library")
    with _connect(path) as connection:
        rows = connection.execute(
            "SELECT id, filename, description_md, size_bytes, added_at FROM library_files ORDER BY added_at, id"
        ).fetchall()
    return [dict(row) for row in rows]


def get_file(file_id: str, path: Path | None = None) -> dict | None:
    if path is None and use_mysql():
        from database.mysql_documents import get_document
        return get_document("library", file_id)
    with _connect(path) as connection:
        row = connection.execute("SELECT * FROM library_files WHERE id = ?", (file_id,)).fetchone()
    return dict(row) if row else None


def update_description(file_id: str, description_md: str, path: Path | None = None) -> bool:
    description_md = description_md.strip()
    if not description_md or len(description_md) > MAX_DESCRIPTION:
        raise ValueError("Mô tả Markdown phải có 1–4000 ký tự")
    if path is None and use_mysql():
        from database.mysql_documents import update_summary
        return update_summary("library", file_id, description_md)
    with _connect(path) as connection:
        cursor = connection.execute("UPDATE library_files SET description_md = ? WHERE id = ?", (description_md, file_id))
    return cursor.rowcount > 0


def delete_file(file_id: str, path: Path | None = None) -> bool:
    """Remove one library entry by its ID, including its stored file contents."""
    if path is None and use_mysql():
        from database.mysql_documents import delete_document
        return delete_document("library", file_id)
    with _connect(path) as connection:
        connection.execute("CREATE TABLE IF NOT EXISTS library_checklists (file_id TEXT PRIMARY KEY, items_json TEXT NOT NULL)")
        connection.execute("DELETE FROM library_checklists WHERE file_id = ?", (file_id,))
        cursor = connection.execute("DELETE FROM library_files WHERE id = ?", (file_id,))
    return cursor.rowcount > 0
