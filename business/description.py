"""Create an extractive Markdown description of a stored PDF/DOCX."""

from __future__ import annotations

import re
from pathlib import Path

from business.chunker import Block, docx_blocks, pdf_blocks
from business.semantic import SENTENCE_END


SALIENT = re.compile(
    r"\b(?:service|project|experience|capabilit|portfolio|deliver|develop|design|"
    r"proposal|qualification|certificate|contract|report|work|prototype|"
    r"dịch vụ|dự án|kinh nghiệm|năng lực|thiết kế|phát triển|sản phẩm|"
    r"báo cáo|hợp đồng|chứng chỉ|hồ sơ)\w*\b",
    re.I,
)


def describe_file(path: str | Path) -> str:
    path = Path(path)
    if path.suffix.lower() == ".pdf":
        blocks = pdf_blocks(path)
    elif path.suffix.lower() == ".docx":
        blocks = docx_blocks(path)
    else:
        raise ValueError("Chỉ hỗ trợ PDF và DOCX")
    return describe_blocks(blocks, path.name)


def describe_blocks(blocks: list[Block], filename: str) -> str:
    """Summarize blocks already extracted by chunking without reading the file again."""
    headings = []
    snippets = []
    for block in blocks:
        if block.kind == "heading" and block.text not in headings:
            headings.append(block.text)
        elif block.kind == "table" and block.rows:
            for row in block.rows:
                value = " | ".join(cell for cell in row if cell).strip()
                if value:
                    snippets.append(value)
        else:
            snippets.extend(sentence.strip() for sentence in SENTENCE_END.split(block.text) if sentence.strip())
    clean = []
    seen = set()
    for text in snippets:
        key = text.casefold()
        if key not in seen and len(text) >= 12:
            clean.append(text)
            seen.add(key)
    salient = [text for text in clean if SALIENT.search(text)]
    selected = []
    for text in (salient[:8] + clean[:5]):
        if text not in selected:
            selected.append(text)
    lines = [f"# {filename}"]
    if headings:
        lines += ["", "## Các mục trong file"] + [f"- {text[:160]}" for text in headings[:12]]
    if selected:
        lines += ["", "## Nội dung đại diện"] + [f"- {text[:300]}" for text in selected]
    if len(lines) == 1:
        lines += ["", "Không trích được chữ. File có thể cần OCR hoặc kiểm tra thủ công."]
    return "\n".join(lines)[:4000]
