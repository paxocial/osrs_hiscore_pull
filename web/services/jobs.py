"""SQLite-backed job queue for background tasks."""

from __future__ import annotations

import json
import time
from typing import Any, Dict, Optional, List
from uuid import uuid4

from database.connection import DatabaseConnection


class JobService:
    def __init__(self, db: Optional[DatabaseConnection] = None) -> None:
        self.db = db or DatabaseConnection(reuse_connection=False, check_same_thread=False)

    def create_job(self, job_type: str, payload: Dict[str, Any]) -> str:
        job_id = str(uuid4())
        with self.db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO jobs (job_id, type, payload, status)
                VALUES (?, ?, ?, 'pending')
                """,
                (job_id, job_type, json.dumps(payload, default=str)),
            )
        return job_id

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self.db.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM jobs WHERE job_id = ?",
                (job_id,),
            ).fetchone()
            if not row:
                return None
            data = dict(row)
            for key in ("payload", "result"):
                try:
                    if data.get(key):
                        data[key] = json.loads(data[key])
                except Exception:
                    pass
            return data

    def fetch_next_pending(self) -> Optional[Dict[str, Any]]:
        with self.db.get_connection() as conn:
            row = conn.execute(
                """
                SELECT * FROM jobs
                WHERE status = 'pending'
                ORDER BY created_at ASC
                LIMIT 1
                """,
            ).fetchone()
            if not row:
                return None
            data = dict(row)
            try:
                data["payload"] = json.loads(data["payload"])
            except Exception:
                data["payload"] = {}
            # mark running
            conn.execute(
                "UPDATE jobs SET status = 'running', started_at = CURRENT_TIMESTAMP WHERE job_id = ?",
                (data["job_id"],),
            )
            return data

    def mark_success(self, job_id: str, result: Any) -> None:
        with self.db.get_connection() as conn:
            conn.execute(
                """
                UPDATE jobs
                SET status = 'success',
                    result = ?,
                    finished_at = CURRENT_TIMESTAMP
                WHERE job_id = ?
                """,
                (json.dumps(result), job_id),
            )

    def mark_error(self, job_id: str, error: str) -> None:
        with self.db.get_connection() as conn:
            conn.execute(
                """
                UPDATE jobs
                SET status = 'error',
                    error = ?,
                    finished_at = CURRENT_TIMESTAMP
                WHERE job_id = ?
                """,
                (error, job_id),
            )

    def list_recent(
        self,
        limit: int = 10,
        *,
        user_id: Optional[int] = None,
        player: Optional[str] = None,
        clan_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        with self.db.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT job_id, type, status, created_at, finished_at
                FROM jobs
                ORDER BY created_at DESC
                LIMIT 50
                """,
            ).fetchall()
            filtered: List[Dict[str, Any]] = []
            for r in rows:
                item = dict(r)
                try:
                    item["payload"] = json.loads(item.get("payload") or "{}")
                except Exception:
                    item["payload"] = {}
                try:
                    if item.get("result"):
                        item["result"] = json.loads(item["result"])
                except Exception:
                    pass

                payload_user = item["payload"].get("user_id")
                payload_player = (item["payload"].get("player") or "").lower()
                payload_target = item["payload"].get("target_type")
                payload_clan = item["payload"].get("clan_id")

                if user_id is not None and payload_user != user_id:
                    continue
                if player is not None and payload_player != player.lower():
                    continue
                if clan_id is not None and payload_target == "clan" and payload_clan != clan_id:
                    continue

                filtered.append(item)
                if len(filtered) >= limit:
                    break
            return filtered
