"""Library use cases between HTTP requests and persistent storage."""

from __future__ import annotations

import tempfile
from pathlib import Path

from business.description import describe_file
from database.library_store import add_file, delete_file, list_files, update_description


def add_document(filename: str, content: bytes) -> dict:
    """Describe and save one document in the current SQLite library."""
    filename = Path(filename).name
    if Path(filename).suffix.lower() not in {".pdf", ".docx"}:
        raise ValueError("Chỉ hỗ trợ PDF và DOCX")
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / filename
        path.write_bytes(content)
        description = describe_file(path)
    return add_file(filename, content, description)


def list_documents() -> list[dict]:
    return list_files()


def update_document_description(file_id: str, description_md: str) -> bool:
    return update_description(file_id, description_md)


def delete_document(file_id: str) -> bool:
    return delete_file(file_id)
