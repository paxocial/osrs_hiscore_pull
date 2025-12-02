"""Lightweight in-process task runner to avoid blocking web requests."""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Any, Callable, Dict, Optional
from uuid import uuid4


class TaskRunner:
    def __init__(self, max_workers: int = 4) -> None:
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="task-runner")
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def submit(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> str:
        """Submit a callable to run in the background."""
        job_id = str(uuid4())
        with self._lock:
            self._jobs[job_id] = {"status": "pending", "result": None, "error": None}

        def _wrapper() -> Any:
            self._set_status(job_id, "running")
            try:
                result = fn(*args, **kwargs)
                self._set_status(job_id, "success", result=result)
                return result
            except Exception as exc:  # pragma: no cover - defensive
                self._set_status(job_id, "error", error=str(exc))
                return None

        self._executor.submit(_wrapper)
        return job_id

    def _set_status(self, job_id: str, status: str, *, result: Any = None, error: Optional[str] = None) -> None:
        with self._lock:
            job = self._jobs.get(job_id, {})
            job["status"] = status
            job["result"] = result
            job["error"] = error
            self._jobs[job_id] = job

    def get(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            return dict(job)  # shallow copy to avoid mutation races

