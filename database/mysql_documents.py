"""Persist uploaded PDF/DOCX bytes and summaries in Railway MySQL."""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from uuid import uuid4

from database.mysql_connection import connect

PART_SIZE = 1024 * 1024
_schema_lock = threading.Lock()
_schema_ready = False


def _ensure_schema(connection) -> None:
    global _schema_ready
    if _schema_ready:
        return
    with _schema_lock:
        if _schema_ready:
            return
        with connection.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS uploaded_documents (
                    id CHAR(32) PRIMARY KEY,
                    kind VARCHAR(16) NOT NULL,
                    filename VARCHAR(255) NOT NULL,
                    summary_md TEXT NOT NULL,
                    size_bytes INT UNSIGNED NOT NULL,
                    added_at VARCHAR(40) NOT NULL,
                    INDEX documents_by_kind (kind, added_at, id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS uploaded_document_parts (
                    document_id CHAR(32) NOT NULL,
                    part_number INT UNSIGNED NOT NULL,
                    content MEDIUMBLOB NOT NULL,
                    PRIMARY KEY (document_id, part_number),
                    CONSTRAINT fk_uploaded_document_parts
                        FOREIGN KEY (document_id) REFERENCES uploaded_documents(id)
                        ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
        connection.commit()
        _schema_ready = True


def save_document(kind: str, filename: str, content: bytes, summary_md: str) -> dict:
    if kind not in {"library", "rfp"}:
        raise ValueError("Loại tài liệu không hợp lệ")
    document_id = uuid4().hex
    added_at = datetime.now(timezone.utc).isoformat()
    with connect() as connection:
        _ensure_schema(connection)
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO uploaded_documents (id, kind, filename, summary_md, size_bytes, added_at) "
                    "VALUES (%s, %s, %s, %s, %s, %s)",
                    (document_id, kind, filename, summary_md, len(content), added_at),
                )
                for part_number, offset in enumerate(range(0, len(content), PART_SIZE)):
                    cursor.execute(
                        "INSERT INTO uploaded_document_parts (document_id, part_number, content) VALUES (%s, %s, %s)",
                        (document_id, part_number, content[offset:offset + PART_SIZE]),
                    )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
    return {"id": document_id, "filename": filename, "description_md": summary_md,
            "size_bytes": len(content), "added_at": added_at}


def list_documents(kind: str) -> list[dict]:
    with connect() as connection:
        _ensure_schema(connection)
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id, filename, summary_md, size_bytes, added_at FROM uploaded_documents "
                "WHERE kind = %s ORDER BY added_at, id", (kind,),
            )
            rows = cursor.fetchall()
    return [dict(zip(("id", "filename", "description_md", "size_bytes", "added_at"), row)) for row in rows]


def get_document(kind: str, document_id: str) -> dict | None:
    with connect() as connection:
        _ensure_schema(connection)
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id, filename, summary_md, size_bytes, added_at FROM uploaded_documents "
                "WHERE kind = %s AND id = %s", (kind, document_id),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            cursor.execute(
                "SELECT content FROM uploaded_document_parts WHERE document_id = %s ORDER BY part_number",
                (document_id,),
            )
            content = b"".join(part[0] for part in cursor.fetchall())
    return {**dict(zip(("id", "filename", "description_md", "size_bytes", "added_at"), row)), "content": content}


def update_summary(kind: str, document_id: str, summary_md: str) -> bool:
    with connect() as connection:
        _ensure_schema(connection)
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE uploaded_documents SET summary_md = %s WHERE kind = %s AND id = %s",
                (summary_md, kind, document_id),
            )
            updated = cursor.rowcount > 0
            if not updated:
                cursor.execute(
                    "SELECT 1 FROM uploaded_documents WHERE kind = %s AND id = %s",
                    (kind, document_id),
                )
                updated = cursor.fetchone() is not None
        connection.commit()
    return updated


def delete_document(kind: str, document_id: str) -> bool:
    with connect() as connection:
        _ensure_schema(connection)
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM uploaded_documents WHERE kind = %s AND id = %s", (kind, document_id))
            deleted = cursor.rowcount > 0
        connection.commit()
    return deleted
