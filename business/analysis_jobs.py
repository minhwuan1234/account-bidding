"""Run document analysis outside the HTTP request that uploads a file."""

from __future__ import annotations

import tempfile
import hashlib
import json
import os
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from business.chunker import chunk_file
from business.upload_service import mark_summary_unavailable, receive_rfp, summarize_rfp
from database.input_store import update_input_summary
from database.report_cache import get_report, save_report


_executor = ThreadPoolExecutor(max_workers=5, thread_name_prefix="document-analysis")
_lock = threading.Lock()
_jobs: dict[str, dict] = {}
_JOB_TTL_SECONDS = 30 * 60


def submit(filename: str, body: bytes, semantic: bool, threshold: float) -> str:
    now = time.monotonic()
    with _lock:
        for job_id, job in list(_jobs.items()):
            if job["status"] in ("done", "error") and now - job["updated"] > _JOB_TTL_SECONDS:
                del _jobs[job_id]
        job_id = uuid.uuid4().hex
        _jobs[job_id] = {"status": "queued", "phase": "Đang lưu file", "updated": now}
    try:
        stored = receive_rfp(filename, body)
    except Exception:
        with _lock:
            del _jobs[job_id]
        raise
    with _lock:
        _jobs[job_id].update(phase="Đang chờ lượt phân tích", updated=time.monotonic())
    try:
        _executor.submit(_run, job_id, filename, body, semantic, threshold, stored["id"], stored.get("reused", False))
    except Exception:
        with _lock:
            del _jobs[job_id]
        raise
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


def _analysis_cache_key(body: bytes, filename: str, semantic: bool, threshold: float) -> str:
    root = Path(__file__).resolve().parent
    version = hashlib.sha256()
    for name in ("chunker.py", "semantic.py", "labels.py", "description.py"):
        version.update((root / name).read_bytes())
    material = {"kind": "file-analysis-v1", "content": hashlib.sha256(body).hexdigest(),
                "extension": Path(filename).suffix.lower(), "semantic": semantic, "threshold": threshold,
                "version": version.hexdigest(), "embedding_model": os.environ.get("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")}
    return hashlib.sha256(json.dumps(material, sort_keys=True).encode()).hexdigest()


def _rename_cached_result(result: dict, filename: str) -> dict:
    old_name = result.get("file", filename)
    old_prefix, new_prefix = Path(old_name).stem + "-", Path(filename).stem + "-"
    result["file"] = filename
    for chunk in result.get("chunks", []):
        chunk["file"] = filename
        if chunk.get("id", "").startswith(old_prefix):
            chunk["id"] = new_prefix + chunk["id"][len(old_prefix):]
    return result


def _run(job_id: str, filename: str, body: bytes, semantic: bool, threshold: float, document_id: str, reused: bool = False) -> None:
    with _lock:
        _jobs[job_id].update(status="running", phase="Bắt đầu phân tích", updated=time.monotonic())
    started = time.monotonic()
    print(f"Analysis started: {filename}", flush=True)
    summary_saved = False
    try:
        cache_key = _analysis_cache_key(body, filename, semantic, threshold)
        try:
            cached = get_report(cache_key)
        except Exception as exc:
            print(f"Analysis cache read failed: {type(exc).__name__}: {exc}", flush=True)
            cached = None
        if cached:
            result = _rename_cached_result(cached["result"], filename)
            result["stored_document_id"] = document_id
            summary = cached.get("summary", "")
            if summary and not reused:
                summary = "# " + filename + "\n" + summary.partition("\n")[2]
                update_input_summary(document_id, summary)
            with _lock:
                _jobs[job_id].update(status="done", phase="Đã dùng dữ liệu file đã phân tích", result=result, updated=time.monotonic())
            return
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / filename
            path.write_bytes(body)
            summary = ""
            def record_summary(blocks):
                nonlocal summary_saved, summary
                if not reused:
                    summary = summarize_rfp(document_id, path, blocks)
                summary_saved = True

            def record_progress(phase):
                with _lock:
                    _jobs[job_id].update(phase=phase, updated=time.monotonic())
                print(f"Analysis {filename}: {phase}", flush=True)

            result = chunk_file(path, semantic=semantic, threshold=threshold,
                                on_blocks=record_summary, on_progress=record_progress)
            result["stored_document_id"] = document_id
            result["content_sha256"] = hashlib.sha256(body).hexdigest()
            result["analysis_options"] = {"semantic": semantic, "threshold": threshold}
            try:
                cached_result = {**result}
                cached_result.pop("stored_document_id", None)
                save_report(cache_key, {"result": cached_result, "summary": summary})
            except Exception as exc:
                print(f"Analysis cache save failed: {type(exc).__name__}: {exc}", flush=True)
        state = {"status": "done", "phase": "Phân tích xong", "result": result}
        print(f"Analysis completed: {filename}; {time.monotonic() - started:.1f}s", flush=True)
    except Exception as exc:
        if not summary_saved and not reused:
            try:
                mark_summary_unavailable(document_id, filename)
            except Exception:
                pass
        state = {"status": "error", "phase": "Phân tích lỗi", "error": str(exc)}
        print(f"Analysis failed: {filename}; {type(exc).__name__}: {exc}", flush=True)
    with _lock:
        _jobs[job_id].update(**state, updated=time.monotonic())
