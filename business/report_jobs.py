"""Run report generation in the background and expose safe progress messages."""

from __future__ import annotations

import threading
import hashlib
import json
import os
from pathlib import Path
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from business.bid_report import generate_report
from database.report_cache import get_report, save_report


_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="bid-report")
_lock = threading.Lock()
_jobs: dict[str, dict] = {}
_MAX_JOBS = 8
_JOB_TTL_SECONDS = 30 * 60


def _event(job_id: str, state: str, message: str) -> None:
    event = {"state": state, "message": message,
             "time": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    with _lock:
        job = _jobs[job_id]
        job["events"].append(event)
        job["phase"] = message
        job["updated"] = time.monotonic()
    print(f"Report {job_id[:8]}: {state} - {message}", flush=True)


def _cache_key(documents, matches):
    if matches or not documents or any(not isinstance(doc.get("content_sha256"), str) or len(doc["content_sha256"]) != 64 for doc in documents):
        return None
    root = Path(__file__).resolve().parent
    version = hashlib.sha256()
    for filename in ("bid_report.py", "chunker.py", "semantic.py", "labels.py", "llm_tag_match.py"):
        version.update((root / filename).read_bytes())
    inputs = [{"hash": doc["content_sha256"], "file": doc.get("file"), "options": doc.get("analysis_options"), "chunks": [{"id": c.get("id"), "text": c.get("text"), "pages": c.get("pages"), "section_path": c.get("section_path"), "labels": c.get("labels")} for c in doc.get("chunks", [])]} for doc in documents]
    material = {"version": version.hexdigest(), "documents": inputs, "embedding_model": os.environ.get("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")}
    return hashlib.sha256(json.dumps(material, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def submit(documents: list[dict], matches: list[dict], force: bool = False) -> str:
    if not any(document.get("chunks") for document in documents):
        raise ValueError("Tài liệu không có nội dung để tạo bản tổng hợp")
    key = _cache_key(documents, matches)
    try:
        cached = get_report(key) if key and not force else None
    except Exception as exc:
        print(f"Report cache read failed: {type(exc).__name__}: {exc}", flush=True)
        cached = None
    now = time.monotonic()
    with _lock:
        for job_id, job in list(_jobs.items()):
            if job["status"] in ("done", "error") and now - job["updated"] > _JOB_TTL_SECONDS:
                del _jobs[job_id]
        if len(_jobs) >= _MAX_JOBS:
            raise RuntimeError("Máy chủ đang xử lý nhiều báo cáo. Hãy thử lại sau ít phút.")
        job_id = uuid.uuid4().hex
        _jobs[job_id] = {"status": "queued", "phase": "Đang chờ tạo báo cáo",
                         "events": [], "updated": now}
    if cached is not None:
        cached["usage_events"] = []
        cached["usage"] = None
        cached["usage_missing"] = False
        cached["cached"] = True
        _event(job_id, "done", "Đã dùng bản tổng hợp đã lưu")
        with _lock:
            _jobs[job_id].update(status="done", result=cached, updated=time.monotonic())
        return job_id
    _event(job_id, "queued", "Đang chờ tạo báo cáo")
    _executor.submit(_run, job_id, documents, matches, key)
    return job_id


def get(job_id: str) -> dict | None:
    with _lock:
        job = _jobs.get(job_id)
        if job is None:
            return None
        snapshot = dict(job)
        snapshot["events"] = list(job["events"])
        snapshot.pop("updated", None)
        if snapshot["status"] in ("done", "error"):
            del _jobs[job_id]
        return snapshot


def _run(job_id: str, documents: list[dict], matches: list[dict], cache_key: str | None) -> None:
    with _lock:
        _jobs[job_id].update(status="running", updated=time.monotonic())
    try:
        result = generate_report(documents, matches,
                                 on_progress=lambda state, message: _event(job_id, state, message))
    except Exception as exc:
        _event(job_id, "error", f"Tạo báo cáo lỗi: {exc}")
        with _lock:
            _jobs[job_id].update(status="error", error=str(exc), updated=time.monotonic())
    else:
        if cache_key:
            try:
                save_report(cache_key, result)
            except Exception as exc:
                print(f"Report cache save failed: {type(exc).__name__}: {exc}", flush=True)
        _event(job_id, "done", "Đã hoàn tất bản tổng hợp")
        with _lock:
            _jobs[job_id].update(status="done", result=result, updated=time.monotonic())
