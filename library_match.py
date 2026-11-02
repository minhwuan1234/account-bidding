"""Choose stored files by Markdown description, then compare their contents."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from evidence import evidence_units
from library_store import get_file, list_files
from matching import match_requirements, requirement_units
from semantic import _cosine, local_model


def match_library(chunks: list[dict[str, Any]], *, mode: str = "auto", manual_ids: list[str] | None = None, db_path: Path | None = None, embedder: Any = None) -> dict[str, Any]:
    if mode not in ("auto", "manual", "llm"):
        raise ValueError("Chế độ chọn file không hợp lệ")
    files = list_files(db_path)
    if not files:
        raise ValueError("Thư viện chưa có file. Hãy thêm file và mô tả Markdown trước.")
    requirements = requirement_units(chunks)
    if not requirements:
        return {"requirements": [], "counts": {"matched": 0, "review": 0, "missing": 0}, "selection_mode": mode, "note": "Không tìm thấy câu yêu cầu rõ ràng trong các chunk approved."}
    model = embedder or local_model()
    selected_by_requirement: dict[str, list[str]] = {}
    description_scores: dict[str, dict[str, float]] = {}
    if mode == "manual":
        allowed = {file["id"] for file in files}
        chosen = [file_id for file_id in (manual_ids or []) if file_id in allowed]
        if not chosen and mode == "manual":
            raise ValueError("Hãy chọn ít nhất một file trong thư viện")
        for requirement in requirements:
            selected_by_requirement[requirement["id"]] = chosen
    else:
        texts = [item["text"] for item in requirements] + [file["description_md"] for file in files]
        vectors = model.encode(["query: " + text for text in texts], normalize_embeddings=True)
        file_vectors = vectors[len(requirements):]
        for item, vector in zip(requirements, vectors[:len(requirements)]):
            ranked = sorted(
                ((_cosine(vector, file_vector), file["id"]) for file, file_vector in zip(files, file_vectors)),
                reverse=True,
            )
            best = ranked[0][0]
            selected = [(score, file_id) for score, file_id in ranked if score >= max(0.68, best - 0.06)][:3]
            if not selected:
                selected = ranked[:1]
            selected_by_requirement[item["id"]] = [file_id for _, file_id in selected]
            description_scores[item["id"]] = {file_id: round(score, 4) for score, file_id in selected}
    needed_ids = {file_id for ids in selected_by_requirement.values() for file_id in ids}
    evidence = []
    with tempfile.TemporaryDirectory() as folder:
        for file_id in needed_ids:
            stored = get_file(file_id, db_path)
            if not stored:
                continue
            path = Path(folder) / (file_id + Path(stored["filename"]).suffix.lower())
            path.write_bytes(stored["content"])
            for unit in evidence_units(path):
                unit["file"] = stored["filename"]
                unit["library_file_id"] = file_id
                evidence.append(unit)
    result = match_requirements(chunks, evidence, embedder=model, file_ids_by_requirement=selected_by_requirement)
    by_id = {file["id"]: file for file in files}
    for item in result["requirements"]:
        item["selected_files"] = [
            {"id": file_id, "filename": by_id[file_id]["filename"], "description_score": description_scores.get(item["id"], {}).get(file_id)}
            for file_id in selected_by_requirement.get(item["id"], []) if file_id in by_id
        ]
        item["selection_mode"] = mode
    result["selection_mode"] = mode
    return result
