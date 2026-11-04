"""Persist RFP uploads and create an extractive summary for each one."""

from __future__ import annotations

from pathlib import Path

from business.chunker import Block
from business.description import describe_blocks, describe_file
from database.input_store import save_input, update_input_summary


def receive_rfp(filename: str, content: bytes) -> dict:
    """Save bytes before queueing analysis so a queued upload is durable."""
    filename = Path(filename).name
    if Path(filename).suffix.lower() not in {".pdf", ".docx"}:
        raise ValueError("Chỉ hỗ trợ PDF và DOCX")
    if not content or len(content) > 30 * 1024 * 1024:
        raise ValueError("File rỗng hoặc vượt quá 30 MB")
    return save_input(filename, content, f"# {filename}\n\nĐang tạo tóm tắt nội dung tài liệu.")


def summarize_rfp(document_id: str, path: Path, blocks: list[Block] | None = None) -> str:
    try:
        summary = describe_blocks(blocks, path.name) if blocks is not None else describe_file(path)
    except Exception:
        summary = f"# {path.name}\n\nKhông trích xuất được nội dung. Cần kiểm tra file hoặc OCR."
    if not update_input_summary(document_id, summary):
        raise RuntimeError("Không cập nhật được tóm tắt tài liệu đã lưu")
    return summary


def mark_summary_unavailable(document_id: str, filename: str) -> None:
    update_input_summary(document_id, f"# {filename}\n\nKhông trích xuất được nội dung. Cần kiểm tra file hoặc OCR.")
