"""Rule-based structural chunking for PDF and DOCX. No token limits or AI."""

from __future__ import annotations

import re
import statistics
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable


HEADING_NUMBER = re.compile(r"^(?P<number>(?:\d+|[IVXLC]+)(?:\.\d+)*)(?:[.\)]|\s)[ \t]*(?P<title>\S.*)$", re.I)
SECTION_HEADING = re.compile(
    r"^(?:SECTION|CHAPTER|ARTICLE|PART|ANNEX|APPENDIX)\s+"
    r"(?P<number>\d+(?:\.\d+)*|[A-Z]+)"
    r"(?:\s*[:\-–]\s*\S.*)?$",
)
MULTI_SPACE = re.compile(r"[ \t]+")


def clean(text: str) -> str:
    return MULTI_SPACE.sub(" ", text.replace("\xa0", " ")).strip()


@dataclass
class Block:
    kind: str  # heading, paragraph, table
    text: str
    page: int | None = None
    level: int | None = None
    rows: list[list[str]] | None = None


def numbered_level(text: str) -> int | None:
    section = SECTION_HEADING.match(text)
    if section:
        number = section.group("number")
        return min(number.count(".") + 1, 6)
    match = HEADING_NUMBER.match(text)
    if not match or len(text) > 120:
        return None
    number = match.group("number")
    if number.isdigit() or re.fullmatch(r"[IVXLC]+", number, re.I):
        return 1
    return min(number.count(".") + 1, 6)


def docx_blocks(path: Path) -> list[Block]:
    from docx import Document
    from docx.table import Table
    from docx.text.paragraph import Paragraph
    from docx.oxml.ns import qn

    document = Document(path)
    blocks: list[Block] = []
    for child in document.element.body.iterchildren():
        if child.tag == qn("w:p"):
            paragraph = Paragraph(child, document)
            value = clean(paragraph.text)
            if not value:
                continue
            style_name = paragraph.style.name if paragraph.style else ""
            style_id = paragraph.style.style_id if paragraph.style else ""
            style_match = re.search(r"(?:heading|title)\s*([1-6])", f"{style_name} {style_id}", re.I)
            level = int(style_match.group(1)) if style_match else numbered_level(value)
            blocks.append(Block("heading" if level else "paragraph", value, level=level))
        elif child.tag == qn("w:tbl"):
            table = Table(child, document)
            rows = [[clean(cell.text) for cell in row.cells] for row in table.rows]
            rows = [row for row in rows if any(row)]
            if rows:
                blocks.append(Block("table", "\n".join(" | ".join(row) for row in rows), rows=rows))
    return blocks


def _line_heading(text: str, size: float, baseline: float, bold: bool) -> int | None:
    section = SECTION_HEADING.match(text)
    if section:
        return min(section.group("number").count(".") + 1, 6)
    if len(text) > 120 or len(text.split()) > 18 or text.endswith((".", ",", ";", ":")):
        return None
    numbered = numbered_level(text)
    if numbered and (bold or size >= baseline * 1.02 or len(text) < 75):
        return numbered
    if size >= baseline * 1.28:
        return 1
    if size >= baseline * 1.13 and bold:
        return 2
    if bold and len(text) < 75 and len(text.split()) >= 2 and text == text.upper() and any(c.isalpha() for c in text):
        return 2
    return None


def pdf_blocks(path: Path) -> list[Block]:
    import pdfplumber

    blocks: list[Block] = []
    with pdfplumber.open(path) as pdf:
        sizes = [float(c.get("size", 0)) for p in pdf.pages for c in p.chars if c.get("text", "").strip()]
        baseline = statistics.median(sizes) if sizes else 10.0
        for page_number, page in enumerate(pdf.pages, 1):
            tables = page.find_tables()
            table_boxes = [table.bbox for table in tables]

            def in_table(obj: dict) -> bool:
                center_x = (obj["x0"] + obj["x1"]) / 2
                center_y = (obj["top"] + obj["bottom"]) / 2
                return any(x0 <= center_x <= x1 and y0 <= center_y <= y1 for x0, y0, x1, y1 in table_boxes)

            text_page = page.filter(lambda obj: obj.get("object_type") != "char" or not in_table(obj))
            words = text_page.extract_words(extra_attrs=["size", "fontname"], use_text_flow=False)
            # Rebuild visual lines. Separate columns remain a PDF limitation.
            lines: list[dict[str, Any]] = []
            for word in sorted(words, key=lambda w: (round(w["top"] / 3), w["x0"])):
                top = float(word["top"])
                line = next((line for line in reversed(lines[-4:]) if abs(line["top"] - top) <= 2.5), None)
                if line is None:
                    line = {"top": top, "words": []}
                    lines.append(line)
                line["words"].append(word)

            items: list[tuple[float, float, Block]] = []
            for line in lines:
                line_words = sorted(line["words"], key=lambda w: w["x0"])
                value = clean(" ".join(w["text"] for w in line_words))
                if not value:
                    continue
                size = max(float(w.get("size", baseline)) for w in line_words)
                bold = any("bold" in str(w.get("fontname", "")).lower() for w in line_words)
                level = _line_heading(value, size, baseline, bold)
                bottom = max(float(w["bottom"]) for w in line_words)
                items.append((line["top"], bottom, Block("heading" if level else "paragraph", value, page_number, level)))
            for table in tables:
                rows = [[clean(cell or "") for cell in row] for row in table.extract()]
                rows = [row for row in rows if any(row)]
                if rows:
                    items.append((table.bbox[1], table.bbox[3], Block("table", "\n".join(" | ".join(row) for row in rows), page_number, rows=rows)))
            previous_bottom: float | None = None
            for top, bottom, block in sorted(items, key=lambda item: item[0]):
                # Merge close lines, while preserving visible paragraph gaps.
                if (block.kind == "paragraph" and blocks and blocks[-1].kind == "paragraph"
                        and blocks[-1].page == page_number and previous_bottom is not None
                        and top - previous_bottom <= baseline * 0.65):
                    blocks[-1].text += " " + block.text
                else:
                    blocks.append(block)
                previous_bottom = bottom
    return blocks


def make_chunks(blocks: list[Block], filename: str) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    headings: list[tuple[int, str]] = []
    current: list[Block] = []

    def flush() -> None:
        nonlocal current
        if not current:
            return
        pages = sorted({block.page for block in current if block.page is not None})
        chunks.append({
            "id": f"{Path(filename).stem}-{len(chunks) + 1:03d}",
            "file": filename,
            "section_path": [title for _, title in headings],
            "heading": headings[-1][1] if headings else None,
            "pages": pages,
            "page_start": pages[0] if pages else None,
            "page_end": pages[-1] if pages else None,
            "text": "\n\n".join(block.text for block in current),
            "blocks": [asdict(block) for block in current],
        })
        current = []

    for block in blocks:
        if block.kind == "heading":
            flush()
            level = block.level or 1
            headings = [(n, title) for n, title in headings if n < level]
            headings.append((level, block.text))
            # A heading can contain substantive information (e.g. a submission
            # email) even when another heading follows immediately. Preserve it
            # as source content as well as in the section path.
            current.append(block)
        else:
            current.append(block)
    flush()
    return chunks


def chunk_file(path: str | Path, *, semantic: bool = False, threshold: float = 0.85,
               embedder: Any = None, on_blocks: Callable[[list[Block]], None] | None = None,
               on_progress: Callable[[str], None] | None = None) -> dict[str, Any]:
    path = Path(path)
    suffix = path.suffix.lower()
    if on_progress:
        on_progress("Đang đọc nội dung PDF/DOCX")
    if suffix == ".pdf":
        blocks = pdf_blocks(path)
    elif suffix == ".docx":
        blocks = docx_blocks(path)
    else:
        raise ValueError("Only PDF and DOCX files are supported")
    if on_blocks is not None:
        if on_progress:
            on_progress("Đang tạo tóm tắt tài liệu")
        on_blocks(blocks)
    if on_progress:
        on_progress("Đang chia tài liệu thành các đoạn")
    chunks = make_chunks(blocks, path.name)
    if semantic:
        from business.semantic import split_semantic

        if on_progress:
            on_progress("Đang chia đoạn theo ngữ nghĩa")
        chunks = split_semantic(chunks, threshold=threshold, embedder=embedder)
    from business.labels import attach_labels

    if on_progress:
        on_progress("Đang tạo tag cho các đoạn")
    chunks = attach_labels(chunks, embedder=embedder)
    return {"file": path.name, "format": suffix[1:], "mode": "semantic" if semantic else "structural", "chunk_count": len(chunks), "chunks": chunks}
