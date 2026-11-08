"""Optional embedding-based splits inside structural sections."""

from __future__ import annotations

import math
import re
from functools import lru_cache
import json
import os
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from typing import Any


MODEL_ID = os.environ.get("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
SENTENCE_END = re.compile(r"(?<=[.!?。！？])\s+")


class APIEmbedder:
    """Embed token batches remotely while retaining one vector per input."""

    def encode(self, texts, normalize_embeddings=True):
        import tiktoken
        import numpy as np
        from business.llm_tag_match import api_key

        key = api_key()
        if not key:
            raise RuntimeError("Chưa cấu hình OPEN_AI_API_KEY trên máy chủ")
        tokenizer = tiktoken.get_encoding("cl100k_base")
        parts, owners = [], []
        for index, text in enumerate(texts):
            text = text.removeprefix("query: ")
            tokens = tokenizer.encode(text, disallowed_special=())
            if not tokens:
                raise ValueError("Không thể tạo embedding cho văn bản rỗng")
            for offset in range(0, len(tokens), 8000):
                part = tokens[offset:offset + 8000]
                parts.append(part)
                owners.append((index, len(part)))
        sums = [None] * len(texts)
        weights = [0] * len(texts)
        start = 0
        while start < len(parts):
            end, token_count = start, 0
            while end < len(parts) and end - start < 128 and token_count + len(parts[end]) <= 100000:
                token_count += len(parts[end])
                end += 1
            body = json.dumps({"model": MODEL_ID, "input": parts[start:end]}).encode()
            request = Request("https://api.openai.com/v1/embeddings", data=body,
                              headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
            for attempt in range(4):
                try:
                    with urlopen(request, timeout=90) as response:
                        data = json.load(response)
                    break
                except HTTPError as exc:
                    if exc.code in (429, 500, 502, 503, 504) and attempt < 3:
                        time.sleep(2 ** attempt)
                        continue
                    raise RuntimeError(f"OpenAI embedding API lỗi HTTP {exc.code}") from exc
                except (URLError, TimeoutError) as exc:
                    if attempt < 3:
                        time.sleep(2 ** attempt)
                        continue
                    raise RuntimeError("Không kết nối được OpenAI embedding API") from exc
            items = sorted(data["data"], key=lambda item: item["index"])
            if len(items) != end - start or [item["index"] for item in items] != list(range(end - start)):
                raise RuntimeError("OpenAI embedding API trả về dữ liệu không đầy đủ")
            for item, (index, weight) in zip(items, owners[start:end]):
                vector = np.asarray(item["embedding"], dtype=float) * weight
                sums[index] = vector if sums[index] is None else sums[index] + vector
                weights[index] += weight
            start = end
        result = []
        for vector, weight in zip(sums, weights):
            vector = vector / weight
            norm = np.linalg.norm(vector)
            result.append(vector / norm if normalize_embeddings and norm else vector)
        return result


@lru_cache(maxsize=1)
def local_model():
    # Kept as an internal compatibility name for existing callers.
    return APIEmbedder()


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
    # The API embedder receives the same text units as the local implementation.
    model = embedder or local_model()
    prepared = []
    all_sentences = []
    for chunk in chunks:
        units = _units(chunk["blocks"])
        sentences = [(i, block) for i, block in enumerate(units) if block["kind"] == "paragraph"]
        prepared.append((chunk, units, sentences))
        all_sentences.extend(block["text"] for _, block in sentences)
    # The API embedder batches inputs to limit request size.
    # Repeated calls for every section add substantial overhead on shared CPUs.
    all_vectors = model.encode(["query: " + text for text in all_sentences], normalize_embeddings=True) if all_sentences else []
    output = []
    offset = 0
    for chunk, units, sentences in prepared:
        vectors = all_vectors[offset:offset + len(sentences)]
        offset += len(sentences)
        if len(sentences) < 2:
            output.append(_build_chunk(chunk, units, 1, None))
            continue
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
