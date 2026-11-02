"""Optional embedding-based splits inside structural sections."""

from __future__ import annotations

import math
import re
from functools import lru_cache
from typing import Any


MODEL_ID = "intfloat/multilingual-e5-small"
SENTENCE_END = re.compile(r"(?<=[.!?。！？])\s+")


@lru_cache(maxsize=1)
def local_model():
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise RuntimeError("Chưa cài embedding. Chạy: python -m pip install -r requirements.txt") from exc
    return SentenceTransformer(MODEL_ID, device="cpu")


def _units(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Use sentences as semantic units and keep tables atomic."""
    result = []
    for source_index, block in enumerate(blocks):
        if block["kind"] != "paragraph":
            result.append({**block, "_source_index": source_index})
            continue
        sentences = SENTENCE_END.split(block["text"])
        for sentence in sentences:
            if sentence.strip():
                result.append({**block, "text": sentence.strip(), "_source_index": source_index})
    return result


def _cosine(left: Any, right: Any) -> float:
    a, b = [float(x) for x in left], [float(x) for x in right]
    dot = sum(x * y for x, y in zip(a, b))
    norm = math.sqrt(sum(x * x for x in a) * sum(y * y for y in b))
    return dot / norm if norm else 0.0


def _build_chunk(base: dict[str, Any], blocks: list[dict[str, Any]], index: int, score: float | None) -> dict[str, Any]:
    restored = []
    for block in blocks:
        source_index = block["_source_index"]
        clean_block = {key: value for key, value in block.items() if key != "_source_index"}
        if restored and block["kind"] == "paragraph" and restored[-1][0] == source_index:
            restored[-1][1]["text"] += " " + block["text"]
        else:
            restored.append((source_index, clean_block))
    output_blocks = [block for _, block in restored]
    pages = sorted({block["page"] for block in output_blocks if block["page"] is not None})
    return {
        **base,
        "id": f"{base['id']}-s{index:02d}",
        "pages": pages,
        "page_start": pages[0] if pages else None,
        "page_end": pages[-1] if pages else None,
        "text": "\n\n".join(block["text"] for block in output_blocks),
        "blocks": output_blocks,
        "split_similarity": round(score, 4) if score is not None else None,
    }


def split_semantic(chunks: list[dict[str, Any]], *, threshold: float = 0.85, embedder: Any = None) -> list[dict[str, Any]]:
    if not 0.5 <= threshold <= 0.95:
        raise ValueError("Ngưỡng ngữ nghĩa phải nằm trong khoảng 0.50–0.95")
    # E5 recommends the query prefix for symmetric similarity comparisons.
    model = embedder or local_model()
    output = []
    for chunk in chunks:
        units = _units(chunk["blocks"])
        sentences = [(i, block) for i, block in enumerate(units) if block["kind"] == "paragraph"]
        if len(sentences) < 2:
            output.append(_build_chunk(chunk, units, 1, None))
            continue
        vectors = model.encode(["query: " + block["text"] for _, block in sentences], normalize_embeddings=True)
        scores = [_cosine(vectors[j - 1], vectors[j]) for j in range(1, len(sentences))]
        start = 0
        segment_number = 1
        for j, score in enumerate(scores, 1):
            # A local dip avoids fragmenting a topic on every slightly dissimilar sentence.
            local_dip = (j == 1 or score <= scores[j - 2]) and (j == len(scores) or score <= scores[j])
            if score < threshold and local_dip:
                boundary = sentences[j][0]
                output.append(_build_chunk(chunk, units[start:boundary], segment_number, None if segment_number == 1 else previous_score))
                start = boundary
                segment_number += 1
                previous_score = score
        output.append(_build_chunk(chunk, units[start:], segment_number, None if segment_number == 1 else previous_score))
    return output
