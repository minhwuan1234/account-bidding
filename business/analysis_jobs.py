"""Run document analysis outside the HTTP request that uploads a file."""

from __future__ import annotations

import tempfile
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from business.chunker import chunk_file
from business.upload_service import mark_summary_unavailable, receive_rfp, summarize_rfp


_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="document-analysis")
_lock = threading.Lock()
_jobs: dict[str, dict] = {}
_MAX_JOBS = 8
_JOB_TTL_SECONDS = 30 * 60


def submit(filename: str, body: bytes, semantic: bool, threshold: float) -> str:
    now = time.monotonic()
    with _lock:
        for job_id, job in list(_jobs.items()):
            if job["status"] in ("done", "error") and now - job["updated"] > _JOB_TTL_SECONDS:
                del _jobs[job_id]
        if len(_jobs) >= _MAX_JOBS:
            raise RuntimeError("Máy chủ đang xử lý nhiều tài liệu. Hãy thử lại sau ít phút.")
        job_id = uuid.uuid4().hex
        _jobs[job_id] = {"status": "queued", "updated": now}
    try:
        stored = receive_rfp(filename, body)
    except Exception:
        with _lock:
            del _jobs[job_id]
        raise
    _executor.submit(_run, job_id, filename, body, semantic, threshold, stored["id"])
    return job_id


def get(job_id: str) -> dict | None:
    with _lock:
        job = _jobs.get(job_id)
        if job is None:
            return None
        snapshot = dict(job)
        snapshot.pop("updated", None)
        if snapshot["status"] in ("done", "error"):
            del _jobs[job_id]
        return snapshot


def _run(job_id: str, filename: str, body: bytes, semantic: bool, threshold: float, document_id: str) -> None:
    with _lock:
        _jobs[job_id].update(status="running", updated=time.monotonic())
    started = time.monotonic()
    print(f"Analysis started: {filename}", flush=True)
    summary_saved = False
    try:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / filename
            path.write_bytes(body)
            def record_summary(blocks):
                nonlocal summary_saved
                summarize_rfp(document_id, path, blocks)
                summary_saved = True

            result = chunk_file(path, semantic=semantic, threshold=threshold, on_blocks=record_summary)
            result["stored_document_id"] = document_id
        state = {"status": "done", "result": result}
        print(f"Analysis completed: {filename}; {time.monotonic() - started:.1f}s", flush=True)
    except Exception as exc:
        if not summary_saved:
            try:
                mark_summary_unavailable(document_id, filename)
            except Exception:
                pass
        state = {"status": "error", "error": str(exc)}
        print(f"Analysis failed: {filename}; {type(exc).__name__}: {exc}", flush=True)
    with _lock:
        _jobs[job_id].update(**state, updated=time.monotonic())
