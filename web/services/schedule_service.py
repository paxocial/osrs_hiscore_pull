"""Scheduling helpers backed by snapshot_jobs table."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from croniter import croniter

from database.connection import DatabaseConnection
from web.services.accounts import AccountService


class ScheduleService:
    def __init__(self, db: Optional[DatabaseConnection] = None) -> None:
        self.db = db or DatabaseConnection(reuse_connection=False, check_same_thread=False)
        self.accounts = AccountService(self.db)

    def _next_run(self, cron_expr: str, now: Optional[datetime] = None) -> str:
        now = now or datetime.now(timezone.utc)
        return croniter(cron_expr, now).get_next(datetime).isoformat()

    def add_account_schedule(self, user_id: int, account_name: str, cron_expr: str, mode: Optional[str] = None) -> int:
        account_id = self.accounts.ensure_account(account_name, display_name=None, mode=mode or "main", update_default_mode=False)
        next_run = self._next_run(cron_expr)
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO snapshot_jobs (user_id, target_type, target_id, cadence_cron, status, next_run, metadata)
                VALUES (?, 'account', ?, ?, 'scheduled', ?, ?)
                """,
                (user_id, account_id, cron_expr, next_run, json.dumps({"mode": mode or "auto"})),
            )
            return cursor.lastrowid

    def add_clan_schedule(self, user_id: int, clan_id: int, cron_expr: str, mode: Optional[str] = None, max_daily_runs: int = 2) -> int:
        # Enforce cap: allow only once or twice daily patterns
        allowed = {"0 0 * * *", "0 12 * * *", "0 0,12 * * *"}
        if cron_expr not in allowed:
            raise ValueError("Cron expression not allowed for clan schedules")
        next_run = self._next_run(cron_expr)
        metadata = {"mode": mode or "auto", "max_daily_runs": max_daily_runs}
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO snapshot_jobs (user_id, target_type, target_id, cadence_cron, status, next_run, metadata)
                VALUES (?, 'clan', ?, ?, 'scheduled', ?, ?)
                """,
                (user_id, clan_id, cron_expr, next_run, json.dumps(metadata)),
            )
            return cursor.lastrowid

    def list_user_schedules(self, user_id: int) -> List[Dict[str, Any]]:
        with self.db.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT sj.*, a.name as account_name
                FROM snapshot_jobs sj
                JOIN accounts a ON sj.target_id = a.id
                WHERE sj.user_id = ? AND sj.target_type = 'account'
                ORDER BY sj.created_at DESC
                """,
                (user_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def list_clan_schedules(self, user_id: int) -> List[Dict[str, Any]]:
        with self.db.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT sj.*, c.name as clan_name, c.slug as clan_slug
                FROM snapshot_jobs sj
                JOIN clans c ON sj.target_id = c.id
                WHERE sj.user_id = ? AND sj.target_type = 'clan'
                ORDER BY sj.created_at DESC
                """,
                (user_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def delete_schedule(self, user_id: int, schedule_id: int) -> None:
        with self.db.get_connection() as conn:
            conn.execute(
                "DELETE FROM snapshot_jobs WHERE id = ? AND user_id = ?",
                (schedule_id, user_id),
            )
