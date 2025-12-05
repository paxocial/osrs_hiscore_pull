"""Lightweight cron scheduler tied to the jobs queue."""

from __future__ import annotations

import json
import threading
import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from croniter import croniter

from web.services.jobs import JobService
from database.connection import DatabaseConnection


class Scheduler:
    def __init__(self, db: Optional[DatabaseConnection] = None, *, poll_interval: float = 30.0) -> None:
        self.db = db or DatabaseConnection(reuse_connection=False, check_same_thread=False)
        self.jobs = JobService(self.db)
        self.poll_interval = poll_interval
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="scheduler", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)

    def _loop(self) -> None:
        while not self._stop.is_set():
            self._tick()
            time.sleep(self.poll_interval)

    def _tick(self) -> None:
        now = datetime.now(timezone.utc)
        with self.db.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT sj.*, a.name as account_name, a.default_mode
                FROM snapshot_jobs sj
                JOIN accounts a ON sj.target_id = a.id
                WHERE sj.target_type = 'account'
                  AND sj.status != 'disabled'
                  AND (sj.next_run IS NULL OR sj.next_run <= ?)
                """,
                (now.isoformat(),),
            ).fetchall()

            for row in rows:
                sched = dict(row)
                metadata = {}
                try:
                    if sched.get("metadata"):
                        metadata = json.loads(sched["metadata"])
                except Exception:
                    metadata = {}
                payload = {
                    "player": sched["account_name"],
                    "mode": metadata.get("mode") or sched.get("default_mode") or "auto",
                    "user_id": sched.get("user_id"),
                    "target_type": "account",
                }
                self.jobs.create_job("snapshot", payload)

                itr = croniter(sched["cadence_cron"], now)
                next_run = itr.get_next(datetime)
                conn.execute(
                    """
                    UPDATE snapshot_jobs
                    SET last_run = ?, next_run = ?, status = 'scheduled'
                    WHERE id = ?
                    """,
                    (now.isoformat(), next_run.isoformat(), sched["id"]),
                )

            # Clan schedules
            clan_rows = conn.execute(
                """
                SELECT sj.*, c.name as clan_name
                FROM snapshot_jobs sj
                JOIN clans c ON sj.target_id = c.id
                WHERE sj.target_type = 'clan'
                  AND sj.status != 'disabled'
                  AND (sj.next_run IS NULL OR sj.next_run <= ?)
                """,
                (now.isoformat(),),
            ).fetchall()

            for row in clan_rows:
                sched = dict(row)
                metadata = {}
                try:
                    if sched.get("metadata"):
                        metadata = json.loads(sched["metadata"])
                except Exception:
                    metadata = {}
                payload = {
                    "clan_id": sched["target_id"],
                    "user_id": sched.get("user_id"),
                    "target_type": "clan",
                    "config_path": metadata.get("config_path"),
                    "mode_cache_path": metadata.get("mode_cache_path"),
                }
                self.jobs.create_job("clan_snapshot", payload)

                itr = croniter(sched["cadence_cron"], now)
                next_run = itr.get_next(datetime)
                conn.execute(
                    """
                    UPDATE snapshot_jobs
                    SET last_run = ?, next_run = ?, status = 'scheduled'
                    WHERE id = ?
                    """,
                    (now.isoformat(), next_run.isoformat(), sched["id"]),
                )
