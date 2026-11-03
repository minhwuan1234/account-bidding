"""Provisional, tag-only embedding gate for the next processing step."""

from __future__ import annotations

from typing import Any

from semantic import _cosine, local_model


POSITIVE = [
    "A binding requirement or instruction that the bidder must follow when preparing or submitting an offer.",
    "A mandatory deadline, qualification, document, deliverable, evaluation criterion or contract condition.",
    "The supplier is required to perform a task or provide a product under the contract.",
]
NEGATIVE = [
    "Background information about the organization or project with no action required from the bidder.",
    "A document title, introduction, general overview or narrative description.",
    "A courtesy message or administrative information without an obligation.",
]
APPROVED_MIN = 0.50


def tier_for(score: float) -> str:
    if score >= APPROVED_MIN:
        return "approved"
    return "reject"


def mark_requirement_candidates(chunks: list[dict[str, Any]], *, embedder: Any = None, db_path: Any = None) -> list[dict[str, Any]]:
    tags = list(dict.fromkeys(tag for chunk in chunks for tag in chunk["labels"]["topics"] if tag.strip()))
    if not tags:
        return chunks
    model = embedder or local_model()
    vectors = model.encode(["query: " + text for text in tags + POSITIVE + NEGATIVE], normalize_embeddings=True)
    tag_vectors = vectors[:len(tags)]
    positive = vectors[len(tags):len(tags) + len(POSITIVE)]
    negative = vectors[len(tags) + len(POSITIVE):]
    by_tag: dict[str, dict[str, Any]] = {}
    for tag, vector in zip(tags, tag_vectors):
        margin = max(_cosine(vector, ref) for ref in positive) - max(_cosine(vector, ref) for ref in negative)
        model_score = max(0.0, min(1.0, 0.5 + margin / 0.12))
        model_tier = tier_for(model_score)
        by_tag[tag] = {
            "requirement_model_score": round(model_score, 4),
            "requirement_model_margin": round(margin, 4),
            "requirement_model_tier": model_tier,
            "requirement_score": round(model_score, 4),
            "requirement_tier": model_tier,
        }
    for chunk in chunks:
        tag = next(iter(chunk["labels"]["topics"]), None)
        fields = by_tag.get(tag, {
            "requirement_model_score": 0.0, "requirement_model_margin": None,
            "requirement_model_tier": "reject", "requirement_score": 0.0,
            "requirement_tier": "reject",
        })
        chunk.update(fields)
        chunk["requirement_candidate"] = fields["requirement_tier"] == "approved"
    return chunks
