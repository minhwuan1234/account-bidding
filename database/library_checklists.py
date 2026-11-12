"""Structured, separately stored checklists for library documents."""
from __future__ import annotations

import json
import hashlib

from database.backend import use_mysql
from database.library_store import _connect, get_file
from database.mysql_connection import connect as mysql_connect


def checklist_revision(items):
    if items is None:
        return None
    value = json.dumps(items, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(value).hexdigest()


def _sqlite_schema(connection):
    connection.execute("CREATE TABLE IF NOT EXISTS library_checklists (file_id TEXT PRIMARY KEY, items_json TEXT NOT NULL)")


def _mysql_schema(connection):
    with connection.cursor() as cursor:
        cursor.execute("CREATE TABLE IF NOT EXISTS library_checklists (file_id CHAR(32) PRIMARY KEY, items_json LONGTEXT NOT NULL, CONSTRAINT checklist_document_fk FOREIGN KEY (file_id) REFERENCES uploaded_documents(id) ON DELETE CASCADE) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4")
    connection.commit()


def get_checklist(file_id, path=None):
    if path is None and use_mysql():
        from database.mysql_documents import _ensure_schema
        with mysql_connect() as connection:
            _ensure_schema(connection)
            _mysql_schema(connection)
            with connection.cursor() as cursor:
                cursor.execute("SELECT items_json FROM library_checklists WHERE file_id=%s", (file_id,))
                row = cursor.fetchone()
    else:
        with _connect(path) as connection:
            _sqlite_schema(connection)
            row = connection.execute("SELECT items_json FROM library_checklists WHERE file_id=?", (file_id,)).fetchone()
    return json.loads(row[0]) if row else None


def save_checklist(file_id, items, path=None, *, create_only=False):
    if not isinstance(items, list) or len(items) > 200:
        raise ValueError("Checklist chỉ nhận tối đa 200 mục")
    clean = []
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("Mục checklist không hợp lệ")
        entry = {key: str(item.get(key, '')).strip() for key in ('label', 'value', 'source')}
        if not entry['label'] or any(len(value) > 4000 for value in entry.values()):
            raise ValueError("Mỗi mục cần tên và tối đa 4000 ký tự mỗi trường")
        clean.append(entry)
    if get_file(file_id, path) is None:
        return False
    value = json.dumps(clean, ensure_ascii=False)
    if path is None and use_mysql():
        from database.mysql_documents import _ensure_schema
        with mysql_connect() as connection:
            _ensure_schema(connection)
            _mysql_schema(connection)
            with connection.cursor() as cursor:
                if create_only:
                    cursor.execute("INSERT IGNORE INTO library_checklists (file_id,items_json) VALUES (%s,%s)", (file_id, value))
                    if not cursor.rowcount:
                        raise ValueError("Checklist đã tồn tại; không ghi đè")
                else:
                    cursor.execute("INSERT INTO library_checklists (file_id,items_json) VALUES (%s,%s) ON DUPLICATE KEY UPDATE items_json=VALUES(items_json)", (file_id, value))
            connection.commit()
    else:
        with _connect(path) as connection:
            _sqlite_schema(connection)
            if create_only:
                cursor = connection.execute("INSERT OR IGNORE INTO library_checklists (file_id,items_json) VALUES (?,?)", (file_id, value))
                if not cursor.rowcount:
                    raise ValueError("Checklist đã tồn tại; không ghi đè")
            else:
                connection.execute("INSERT INTO library_checklists (file_id,items_json) VALUES (?,?) ON CONFLICT(file_id) DO UPDATE SET items_json=excluded.items_json", (file_id, value))
    return True
