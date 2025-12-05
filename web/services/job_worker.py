"""Background job worker that processes queued jobs (SQLite-backed)."""

from __future__ import annotations

import os
import threading
import time
import json
from typing import Optional, List, Dict, Any
from pathlib import Path
from datetime import datetime, timezone

from agents.osrs_snapshot_agent import SnapshotAgent
from agents.report_agent import ReportAgent
from core.constants import DEFAULT_MODE
from web.services.jobs import JobService
from web.services.snapshot_ingest import SnapshotIngestService
from web.services.webhooks import WebhookService
import httpx
from database.connection import DatabaseConnection


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
        self.db: DatabaseConnection = self.ingest_service.db  # reuse DB for clan lookups
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
                job_type = str(job.get("type") or "").strip().lower()
                if job_type == "snapshot":
                    result = self._run_snapshot(job)
                    self.job_service.mark_success(job["job_id"], result)
                elif job_type == "clan_snapshot":
                    result = self._run_clan_snapshot(job)
                    self.job_service.mark_success(job["job_id"], result)
                else:
                    self.job_service.mark_error(job["job_id"], f"Unsupported job type: {job.get('type')}")
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

    def _run_clan_snapshot(self, job: dict) -> Dict[str, Any]:
        payload = job.get("payload") or {}
        clan_id = payload.get("clan_id")
        user_id = payload.get("user_id")
        if not clan_id:
            return {"status": 400, "body": {"error": "missing clan_id"}}

        # Lookup clan + members
        with self.db.get_connection() as conn:
            clan = conn.execute("SELECT * FROM clans WHERE id = ?", (clan_id,)).fetchone()
            if not clan:
                return {"status": 404, "body": {"error": "clan not found"}}
            members = conn.execute(
                """
                SELECT a.name, COALESCE(a.default_mode, 'auto') as mode
                FROM clan_members cm
                JOIN accounts a ON cm.account_id = a.id
                WHERE cm.clan_id = ?
                """,
                (clan_id,),
            ).fetchall()
            member_list = [dict(m) for m in members]

        if not member_list:
            return {"status": 400, "body": {"error": "no clan members to snapshot"}}

        # Create clan snapshot record
        with self.db.get_connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO clan_snapshots (clan_id, job_id, status, member_count, requested_by_user_id, metadata)
                VALUES (?, ?, 'running', ?, ?, ?)
                """,
                (clan_id, job["job_id"], len(member_list), user_id, json.dumps(payload)),
            )
            clan_snapshot_id = cur.lastrowid

        agent = SnapshotAgent(
            output_dir=Path(payload.get("output_dir") or "data/snapshots"),
            mode_cache_path=Path(payload.get("mode_cache_path")) if payload.get("mode_cache_path") else None,
            config_path=Path(payload.get("config_path") or self.config_path) if (payload.get("config_path") or self.config_path) else None,
        )
        try:
            report_agent = ReportAgent(Path("reports"), scribe_config=self.config_path)
        except Exception:
            report_agent = None

        results: List[Dict[str, Any]] = []
        agg_total_xp = 0
        agg_total_level = 0
        agg_delta_xp = 0
        success_count = 0

        for m in member_list:
            player = m["name"]
            mode = (m.get("mode") or DEFAULT_MODE).lower()
            try:
                res_obj = agent.run([{"name": player, "mode": mode}])[0]
            except Exception as exc:
                res_obj = None
                res = {"success": False, "player": player, "resolved_mode": mode, "message": str(exc)}
            else:
                res = self._serialize_result(res_obj)

            snapshot_db_id = None
            delta_summary = None
            if res_obj and res_obj.success and res_obj.payload:
                ingest_info = self.ingest_service.ingest_result(res_obj)
                if isinstance(ingest_info, dict):
                    snapshot_db_id = ingest_info.get("snapshot_db_id")
                    if ingest_info.get("delta"):
                        res_obj.payload["delta"] = ingest_info["delta"]
                    if ingest_info.get("delta_summary"):
                        res_obj.delta_summary = ingest_info["delta_summary"]
                elif isinstance(ingest_info, int):
                    snapshot_db_id = ingest_info
                if res_obj.payload:
                    md = res_obj.payload.get("metadata", {})
                    agg_total_xp += md.get("total_xp") or 0
                    agg_total_level += md.get("total_level") or 0
                    delta_obj = res_obj.payload.get("delta") or {}
                    if delta_obj.get("total_xp_delta"):
                        agg_delta_xp += delta_obj["total_xp_delta"]
                if res_obj.delta_summary:
                    delta_summary = res_obj.delta_summary
                if report_agent and res_obj.payload and res_obj.snapshot_path:
                    try:
                        report_agent.build_from_payload(
                            payload=res_obj.payload,
                            report_source=res_obj.snapshot_path,
                            delta_summary=res_obj.delta_summary,
                        )
                    except Exception:
                        pass
                success_count += 1
            # Persist member record
            with self.db.get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO clan_snapshot_members (clan_snapshot_id, account_id, snapshot_id, status, error)
                    VALUES (
                        ?,
                        (SELECT id FROM accounts WHERE name = ? LIMIT 1),
                        ?,
                        ?,
                        ?
                    )
                    """,
                    (
                        clan_snapshot_id,
                        player,
                        snapshot_db_id,
                        "success" if res_obj and res_obj.success else "error",
                        None if res_obj and res_obj.success else res.get("message") if res else "unknown error",
                    ),
                )
            res["snapshot_db_id"] = snapshot_db_id
            res["delta_summary"] = delta_summary or res.get("delta_summary")
            results.append(res)

        # Update clan snapshot status
        with self.db.get_connection() as conn:
            conn.execute(
                """
                UPDATE clan_snapshots
                SET status = ?, finished_at = CURRENT_TIMESTAMP, latency_ms = NULL, error = NULL,
                    metadata = ?
                WHERE id = ?
                """,
                ("success", json.dumps({"success_count": success_count}), clan_snapshot_id),
            )

            # Upsert simple aggregate (latest)
            payload_obj = {
                "total_xp": agg_total_xp,
                "total_level": agg_total_level,
                "total_delta_xp": agg_delta_xp,
                "members_snapshotted": success_count,
                "member_count": len(member_list),
            }
            conn.execute(
                """
                INSERT INTO clan_stats (clan_id, timeframe, start_at, end_at, payload)
                VALUES (?, 'latest', NULL, NULL, ?)
                ON CONFLICT(clan_id, timeframe, start_at, end_at)
                DO UPDATE SET payload = excluded.payload, generated_at = CURRENT_TIMESTAMP
                """,
                (clan_id, json.dumps(payload_obj)),
            )

        return {"status": 200, "body": {"results": results, "clan_snapshot_id": clan_snapshot_id}}
