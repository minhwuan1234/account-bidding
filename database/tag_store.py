"""Local SQLite store for tags explicitly approved by the user."""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MODEL_ID = "intfloat/multilingual-e5-small"
DEFAULT_DB = Path(__file__).resolve().parent.parent / "data" / "tag_examples.sqlite3"


def database_path() -> Path:
    return Path(os.environ.get("STRUCTURAL_CHUNKER_DB", DEFAULT_DB))


def _connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.execute("""
        CREATE TABLE IF NOT EXISTS approved_tags (
            tag TEXT PRIMARY KEY COLLATE NOCASE,
            embedding TEXT NOT NULL,
            model_id TEXT NOT NULL,
            approved_at TEXT NOT NULL
        )
    """)
    return connection


def load_approved(path: Path | None = None) -> list[dict[str, Any]]:
    with _connect(path or database_path()) as connection:
        rows = connection.execute(
            "SELECT tag, embedding FROM approved_tags WHERE model_id = ?", (MODEL_ID,)
        ).fetchall()
    return [{"tag": tag, "embedding": json.loads(embedding)} for tag, embedding in rows]


def save_approved(tag: str, embedding: Any, path: Path | None = None) -> None:
    tag = tag.strip()
    if not tag or len(tag) > 160:
        raise ValueError("Tên tag phải có 1–160 ký tự")
    vector = [float(value) for value in embedding]
    with _connect(path or database_path()) as connection:
        connection.execute(
            "INSERT INTO approved_tags (tag, embedding, model_id, approved_at) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(tag) DO UPDATE SET embedding=excluded.embedding, "
            "model_id=excluded.model_id, approved_at=excluded.approved_at",
            (tag, json.dumps(vector), MODEL_ID, datetime.now(timezone.utc).isoformat()),
        )


def remove_approved(tag: str, path: Path | None = None) -> None:
    with _connect(path or database_path()) as connection:
        connection.execute("DELETE FROM approved_tags WHERE tag = ?", (tag,))
