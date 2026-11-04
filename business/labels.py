"""Infer a short extractive topic from each chunk using local embeddings.

Embedding vectors do not contain words to print. We first collect candidate
phrases from the chunk itself, then choose the phrase closest to the chunk's
meaning. No fixed topic taxonomy or text-generation model is used.
"""

from __future__ import annotations

import math
import re
import unicodedata
from typing import Any

import numpy as np

from business.semantic import SENTENCE_END, local_model


WORD = re.compile(r"[^\W_]+(?:[-’'][^\W_]+)*", re.UNICODE)
STOP = {
    "a", "an", "and", "are", "as", "at", "be", "been", "by", "can", "for", "from",
    "has", "have", "in", "into", "is", "it", "its", "of", "on", "or", "our", "shall",
    "should", "that", "the", "their", "these", "this", "those", "to", "under", "was",
    "were", "which", "who", "will", "with", "within", "you", "your", "we", "they",
    "before", "after", "made", "make", "such", "any", "all", "each",
    "và", "của", "cho", "các", "những", "một", "là", "được", "trong", "theo", "với",
    "từ", "để", "này", "đó", "khi", "về", "tại", "có", "sẽ", "phải", "như", "bởi",
}
PLACEHOLDER = re.compile(r"^(?:click or tap here|choose an item|yes|no|n/a)\b", re.I)
AUXILIARY = {"will", "shall", "must", "may", "can", "is", "are", "was", "were", "be", "been", "has", "have"}
MAX_CANDIDATES = 350


def _content_units(chunk: dict[str, Any]) -> list[str]:
    units: list[str] = []
    for block in chunk["blocks"]:
        if block["kind"] == "table" and block.get("rows"):
            texts = []
            for row in block["rows"]:
                cells = [str(cell).strip() for cell in row if str(cell).strip()]
                if not cells:
                    continue
                key = cells[0] if len(cells) > 1 and len(cells[0]) <= 100 else ""
                if key:
                    texts.append(key)
                for cell in (cells[1:] if key else cells):
                    texts.extend((key + " | " if key else "") + sentence for sentence in SENTENCE_END.split(cell))
        else:
            texts = SENTENCE_END.split(block["text"])
        for value in texts:
            value = value.strip()
            if not value or PLACEHOLDER.match(value):
                continue
            while len(value) > 700:
                cut = value.rfind(" ", 0, 700)
                cut = cut if cut > 350 else 700
                units.append(value[:cut].strip())
                value = value[cut:].strip()
            if value:
                units.append(value)
    return units


def _candidates(units: list[str]) -> list[dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    for unit_index, unit in enumerate(units):
        # Table separators and punctuation are phrase boundaries.
        for fragment in re.split(r"[|;:()\[\]\n]", unit):
            words = WORD.findall(fragment)
            if not words:
                continue
            for size in range(1, 6):
                for start in range(len(words) - size + 1):
                    part = words[start:start + size]
                    lower = [word.casefold() for word in part]
                    if lower[0] in STOP or lower[-1] in STOP:
                        continue
                    if any(word in AUXILIARY for word in lower):
                        continue
                    if not any(any(c.isalpha() for c in word) for word in part):
                        continue
                    if part[0][0].isdigit() or part[-1][-1].isdigit():
                        continue
                    phrase = " ".join(part)
                    if len(phrase) < 7 or len(phrase) > 72:
                        continue
                    key = phrase.casefold()
                    if key not in found:
                        found[key] = {"phrase": phrase, "count": 0, "first": unit_index, "evidence": unit}
                    found[key]["count"] += 1
    # Common phrases and earlier phrases get considered first. Embeddings make
    # the final decision; this cap keeps very large tables responsive.
    return sorted(found.values(), key=lambda item: (-item["count"], item["first"], -len(item["phrase"])))[:MAX_CANDIDATES]


def _slug(phrase: str) -> str:
    normalized = unicodedata.normalize("NFKD", phrase.casefold())
    ascii_text = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", "_", ascii_text).strip("_") or "topic"


def _normalize(vector: np.ndarray) -> np.ndarray:
    length = np.linalg.norm(vector)
    return vector / length if length else vector


def attach_labels(chunks: list[dict[str, Any]], *, embedder: Any = None) -> list[dict[str, Any]]:
    model = embedder or local_model()
    units_by_chunk = [_content_units(chunk) for chunk in chunks]
    candidates_by_chunk = [_candidates(units) for units in units_by_chunk]
    all_texts = list(dict.fromkeys(
        [unit for units in units_by_chunk for unit in units] +
        [candidate["phrase"] for candidates in candidates_by_chunk for candidate in candidates]
    ))
    vectors = np.asarray(model.encode(["query: " + text for text in all_texts], normalize_embeddings=True)) if all_texts else np.empty((0, 1))
    by_text = dict(zip(all_texts, vectors))
    for chunk, units, candidates in zip(chunks, units_by_chunk, candidates_by_chunk):
        if not units or not candidates:
            chunk["labels"] = {"topics": ["Nội dung không xác định"], "topic_details": [], "source": "fallback"}
            continue
        # Average sentence/row vectors so long chunks are represented beyond
        # the embedding model's single-input length limit.
        centroid = _normalize(np.mean([by_text[unit] for unit in units], axis=0))
        scored = []
        opening_weight = 0.02 if any(block["kind"] == "table" for block in chunk["blocks"]) else 0.05
        for candidate in candidates:
            cosine = float(by_text[candidate["phrase"]] @ centroid)
            words = candidate["phrase"].split()
            length_bonus = 0.012 if 2 <= len(words) <= 4 else 0.0
            frequency_bonus = min(0.018, 0.007 * math.log1p(candidate["count"]))
            opening_bonus = opening_weight / (1 + candidate["first"])
            scored.append((cosine + length_bonus + frequency_bonus + opening_bonus, cosine, candidate))
        _, similarity, best = max(scored, key=lambda item: item[0])
        phrase = best["phrase"][0].upper() + best["phrase"][1:]
        chunk["labels"] = {
            "topics": [phrase],
            "topic_details": [{
                "id": _slug(phrase),
                "name": phrase,
                "score": round(similarity, 4),
                "evidence": best["evidence"],
            }],
            "source": "content_embedding",
        }
    return chunks
