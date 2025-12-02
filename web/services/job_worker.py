"""Background job worker that processes queued jobs (SQLite-backed)."""

from __future__ import annotations

import os
import threading
import time
from typing import Optional
from pathlib import Path

from agents.osrs_snapshot_agent import SnapshotAgent
from agents.report_agent import ReportAgent
from core.constants import DEFAULT_MODE
from web.services.jobs import JobService
from web.services.snapshot_ingest import SnapshotIngestService
from web.services.webhooks import WebhookService
import httpx


class JobWorker:
    def __init__(
        self,
        job_service: Optional[JobService] = None,
        ingest_service: Optional[SnapshotIngestService] = None,
        *,
        poll_interval: float = 1.0,
        config_path: Optional[str] = None,
    ) -> None:
        self.job_service = job_service or JobService()
        self.ingest_service = ingest_service or SnapshotIngestService()
        self.webhooks = WebhookService()
        self.config_path = config_path
        self.poll_interval = poll_interval
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="job-worker", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)

    def _loop(self) -> None:
        while not self._stop.is_set():
            job = self.job_service.fetch_next_pending()
            if not job:
                time.sleep(self.poll_interval)
                continue
            try:
                if job["type"] == "snapshot":
                    result = self._run_snapshot(job)
                    self.job_service.mark_success(job["job_id"], result)
                else:
                    self.job_service.mark_error(job["job_id"], f"Unsupported job type: {job['type']}")
            except Exception as exc:  # pragma: no cover - defensive
                self.job_service.mark_error(job["job_id"], str(exc))

    def _serialize_result(self, res):
        return {
            "player": res.player,
            "resolved_mode": res.mode,
            "success": res.success,
            "message": res.message,
            "snapshot_path": str(res.snapshot_path) if res.snapshot_path else None,
            "delta_summary": res.delta_summary,
            "metadata": res.metadata,
            "payload": res.payload,
        }

    def _send_webhook(self, result: dict, payload: dict):
        owner_user_id = payload.get("user_id")
        target_type = payload.get("target_type")
        clan_id = payload.get("clan_id")
        if not owner_user_id:
            return
        body = {
            "player": result.get("player"),
            "mode": result.get("resolved_mode"),
            "delta_summary": result.get("delta_summary"),
            "snapshot_path": result.get("snapshot_path"),
            "snapshot_id": result.get("metadata", {}).get("snapshot_id") if result.get("metadata") else None,
        }
        self.webhooks.dispatch(owner_user_id, target_type, clan_id, event="snapshot_complete", payload=body)

    def _run_snapshot(self, job: dict):
        payload = job.get("payload") or {}
        player = payload.get("player")
        mode = (payload.get("mode") or DEFAULT_MODE).lower()
        if not player:
            return {"status": 400, "body": {"error": "missing player"}}

        output_dir = payload.get("output_dir") or os.path.join("data", "snapshots")
        mode_cache_path = payload.get("mode_cache_path")
        config_path = payload.get("config_path") or self.config_path

        output_dir = Path(output_dir)
        mode_cache_path = Path(mode_cache_path) if mode_cache_path else None
        config_path = Path(config_path) if config_path else None

        agent = SnapshotAgent(
            output_dir=output_dir,
            mode_cache_path=mode_cache_path,
            config_path=config_path,
        )
        results = agent.run([{"name": player, "mode": mode}])

        # Optionally generate reports
        try:
            report_agent = ReportAgent(Path("reports"), scribe_config=self.config_path)
        except Exception:  # pragma: no cover - defensive
            report_agent = None

        for r in results:
            if r.success and r.payload:
                # Ingest into DB
                ingest_info = self.ingest_service.ingest_result(r)
                if ingest_info:
                    if ingest_info.get("delta"):
                        r.delta = ingest_info["delta"]
                        if r.payload is not None:
                            r.payload["delta"] = ingest_info["delta"]
                    if ingest_info.get("delta_summary"):
                        r.delta_summary = ingest_info["delta_summary"]
                # Build report if possible
                if report_agent and r.payload and r.snapshot_path:
                    try:
                        report_agent.build_from_payload(
                            payload=r.payload,
                            report_source=r.snapshot_path,
                            delta_summary=r.delta_summary,
                        )
                    except Exception:
                        pass
                # Send webhook if configured
                self._send_webhook(self._serialize_result(r), payload)

        # Mimic API response shape for UI reuse
        return {"status": 200, "body": {"results": [self._serialize_result(r) for r in results]}}
