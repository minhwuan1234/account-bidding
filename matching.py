"""Local first-pass requirement extraction and evidence matching."""

from __future__ import annotations

import re
from typing import Any

from semantic import SENTENCE_END, _cosine, local_model


REQUIREMENT_CUE = re.compile(
    r"\b(?:must|shall|required|requirement|submit|provide|include|attach|deliver|"
    r"deadline|no later than|at least|minimum|qualification|eligible|mandatory|"
    r"phải|bắt buộc|nộp|cung cấp|đính kèm|tối thiểu|hạn chót|yêu cầu)\b",
    re.I,
)
NUMBER = re.compile(r"\b\d+(?:[.,]\d+)*\b")


def requirement_units(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep only explicit candidate statements from approved chunks."""
    output = []
    seen = set()
    for chunk in chunks:
        if chunk.get("requirement_tier") != "approved":
            continue
        tag = next(iter(chunk.get("labels", {}).get("topics", [])), "")
        for block in chunk.get("blocks", []):
            if block.get("kind") == "table" and block.get("rows"):
                texts = [" | ".join(cell for cell in row if cell) for row in block["rows"]]
            else:
                texts = SENTENCE_END.split(block.get("text", ""))
            for text in texts:
                text = text.strip()
                key = (chunk.get("id"), text.casefold())
                if len(text) < 12 or not REQUIREMENT_CUE.search(text) or key in seen:
                    continue
                seen.add(key)
                output.append({
                    "id": f"req-{len(output)+1:03d}",
                    "text": text,
                    "tag": tag,
                    "source_chunk_id": chunk.get("id"),
                    "source_file": chunk.get("file"),
                    "source_pages": chunk.get("pages", []),
                    "section_path": chunk.get("section_path", []),
                })
    return output


def match_requirements(chunks: list[dict[str, Any]], evidence: list[dict[str, Any]], *, embedder: Any = None, match_min: float = 0.82, review_min: float = 0.72, file_ids_by_requirement: dict[str, list[str]] | None = None) -> dict[str, Any]:
    requirements = requirement_units(chunks)
    if not requirements:
        return {"requirements": [], "counts": {"matched": 0, "review": 0, "missing": 0}, "note": "Không tìm thấy câu yêu cầu rõ ràng trong các chunk approved."}
    model = embedder or local_model()
    texts = [item["text"] for item in requirements] + [item["text"] for item in evidence]
    vectors = model.encode(["query: " + text for text in texts], normalize_embeddings=True)
    requirement_vectors = vectors[:len(requirements)]
    evidence_vectors = vectors[len(requirements):]
    counts = {"matched": 0, "review": 0, "missing": 0}
    for item, vector in zip(requirements, requirement_vectors):
        allowed_ids = set(file_ids_by_requirement.get(item["id"], [])) if file_ids_by_requirement is not None else None
        ranked = sorted(
            ((round(_cosine(vector, other), 4), candidate) for candidate, other in zip(evidence, evidence_vectors)
             if allowed_ids is None or candidate.get("library_file_id") in allowed_ids),
            key=lambda pair: pair[0], reverse=True,
        )
        best_score, best = ranked[0] if ranked else (0.0, None)
        required_numbers = set(NUMBER.findall(item["text"]))
        evidence_numbers = set(NUMBER.findall(best["text"])) if best else set()
        numeric_conflict = bool(required_numbers and not required_numbers.issubset(evidence_numbers))
        status = "matched" if best_score >= match_min and not numeric_conflict else "review" if best_score >= review_min else "missing"
        item["status"] = status
        item["similarity"] = best_score if best else None
        item["evidence"] = best
        item["numeric_conflict"] = numeric_conflict
        counts[status] += 1
    return {
        "requirements": requirements,
        "counts": counts,
        "note": "Kết quả là gợi ý. Hãy kiểm tra file gốc trước khi kết luận đã đáp ứng hoặc còn thiếu.",
    }
