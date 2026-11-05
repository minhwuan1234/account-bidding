"""Run report generation in the background and expose safe progress messages."""

from __future__ import annotations

import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from business.bid_report import generate_report


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


def submit(documents: list[dict], matches: list[dict]) -> str:
    if not any(document.get("chunks") for document in documents):
        raise ValueError("Tài liệu không có nội dung để tạo bản tổng hợp")
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
    _event(job_id, "queued", "Đang chờ tạo báo cáo")
    _executor.submit(_run, job_id, documents, matches)
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


def _run(job_id: str, documents: list[dict], matches: list[dict]) -> None:
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
        _event(job_id, "done", "Đã hoàn tất bản tổng hợp")
        with _lock:
            _jobs[job_id].update(status="done", result=result, updated=time.monotonic())
