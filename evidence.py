"""Read candidate evidence from local PDF/DOCX files with source locations."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from chunker import docx_blocks, make_chunks, pdf_blocks
from semantic import SENTENCE_END


def evidence_units(path: str | Path) -> list[dict[str, Any]]:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        blocks = pdf_blocks(path)
    elif suffix == ".docx":
        blocks = docx_blocks(path)
    else:
        raise ValueError("Chỉ hỗ trợ PDF và DOCX")
    units = []
    for chunk in make_chunks(blocks, path.name):
        for block in chunk["blocks"]:
            if block["kind"] == "table" and block["rows"]:
                texts = [" | ".join(cell for cell in row if cell) for row in block["rows"]]
            else:
                texts = SENTENCE_END.split(block["text"])
            for text in texts:
                text = text.strip()
                if not text:
                    continue
                units.append({
                    "file": path.name,
                    "text": text,
                    "section_path": chunk["section_path"],
                    "page": block["page"],
                    "kind": block["kind"],
                })
    return units
