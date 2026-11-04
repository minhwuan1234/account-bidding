"""Run document analysis outside the HTTP request that uploads a file."""

from __future__ import annotations

import tempfile
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from business.chunker import chunk_file


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
    _executor.submit(_run, job_id, filename, body, semantic, threshold)
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


def _run(job_id: str, filename: str, body: bytes, semantic: bool, threshold: float) -> None:
    with _lock:
        _jobs[job_id].update(status="running", updated=time.monotonic())
    started = time.monotonic()
    print(f"Analysis started: {filename}", flush=True)
    try:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / filename
            path.write_bytes(body)
            result = chunk_file(path, semantic=semantic, threshold=threshold)
        state = {"status": "done", "result": result}
        print(f"Analysis completed: {filename}; {time.monotonic() - started:.1f}s", flush=True)
    except Exception as exc:
        state = {"status": "error", "error": str(exc)}
        print(f"Analysis failed: {filename}; {type(exc).__name__}: {exc}", flush=True)
    with _lock:
        _jobs[job_id].update(**state, updated=time.monotonic())
