"""Create library checklists in background jobs."""
from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from business.library_checklist_service import create_checklist

_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix='library-checklist')
_lock = threading.Lock()
_jobs = {}


def submit(file_id):
    if not file_id:
        raise ValueError('Thiếu ID tài liệu')
    job_id = uuid4().hex
    with _lock:
        now = time.monotonic()
        for key, job in list(_jobs.items()):
            if job['status'] in ('done', 'error') and now - job['updated'] > 3600:
                del _jobs[key]
        _jobs[job_id] = {'status':'queued', 'updated':now}
    try:
        _executor.submit(_run, job_id, file_id)
    except Exception:
        with _lock:
            del _jobs[job_id]
        raise
    return job_id


def get(job_id):
    with _lock:
        job = _jobs.get(job_id)
        if not job:
            return None
        return {key:value for key, value in job.items() if key != 'updated'}


def _run(job_id, file_id):
    with _lock:
        _jobs[job_id].update(status='running', updated=time.monotonic())
    try:
        state = {'status':'done', 'items':create_checklist(file_id)}
    except Exception as exc:
        state = {'status':'error', 'error':str(exc)}
    with _lock:
        _jobs[job_id].update(**state, updated=time.monotonic())
