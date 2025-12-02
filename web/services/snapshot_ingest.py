"""Ingest SnapshotAgent results into the analytics database."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from agents.osrs_snapshot_agent import SnapshotResult
from core.constants import SKILLS, ACTIVITY_LOOKUP
from core.processing import compute_snapshot_delta, summarize_delta
from database.connection import DatabaseConnection


class SnapshotIngestService:
    def __init__(self, db: Optional[DatabaseConnection] = None) -> None:
        self.db = db or DatabaseConnection(reuse_connection=False, check_same_thread=False)

    def _total_from_skills(self, skills: List[Dict[str, Any]]) -> Tuple[int, int]:
        total_level = 0
        total_xp = 0
        for skill in skills:
            name = str(skill.get("name", "")).lower()
            level = int(skill.get("level", 0) or 0)
            xp = int(skill.get("xp", 0) or 0)
            if name == "overall":
                total_level = level
                total_xp = xp
                break
        if total_level == 0:
            total_level = sum(int(s.get("level", 0) or 0) for s in skills)
        if total_xp == 0:
            total_xp = sum(int(s.get("xp", 0) or 0) for s in skills)
        return total_level, total_xp

    def _ensure_account(self, conn, player: str, resolved_mode: str) -> int:
        account = conn.execute("SELECT id FROM accounts WHERE name = ?", (player,)).fetchone()
        if account:
            conn.execute("UPDATE accounts SET default_mode = ? WHERE id = ?", (resolved_mode, account["id"]))
            return account["id"]
        cursor = conn.execute(
            "INSERT INTO accounts (name, default_mode) VALUES (?, ?)",
            (player, resolved_mode),
        )
        return cursor.lastrowid

    def _insert_skills(self, conn, snapshot_db_id: int, skills: List[Dict[str, Any]]) -> int:
        count = 0
        for idx, skill in enumerate(skills):
            skill_id = skill.get("id") or skill.get("skill_id")
            if skill_id is None:
                name = str(skill.get("name", "")).strip()
                if name in SKILLS:
                    skill_id = SKILLS.index(name)
                else:
                    skill_id = idx
            conn.execute(
                """
                INSERT INTO skills (snapshot_id, skill_id, name, level, xp, rank)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot_db_id,
                    skill_id,
                    skill.get("name"),
                    skill.get("level"),
                    skill.get("xp"),
                    skill.get("rank"),
                ),
            )
            count += 1
        return count

    def _insert_activities(self, conn, snapshot_db_id: int, activities: List[Dict[str, Any]]) -> int:
        count = 0
        for idx, activity in enumerate(activities):
            activity_id = activity.get("id") or activity.get("activity_id")
            if activity_id is None:
                name = str(activity.get("name", "")).strip()
                activity_id = ACTIVITY_LOOKUP.get(name, idx)
            conn.execute(
                """
                INSERT INTO activities (snapshot_id, activity_id, name, score, rank)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    snapshot_db_id,
                    activity_id,
                    activity.get("name"),
                    activity.get("score"),
                    activity.get("rank"),
                ),
            )
            count += 1
        return count

    def _insert_delta(self, conn, account_id: int, snapshot_db_id: int, fetched_at: str, delta: Optional[Dict[str, Any]], current_skills: List[Dict[str, Any]], current_activities: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        # Find previous snapshot for linkage/time diff
        prev_row = conn.execute(
            """
            SELECT id, fetched_at FROM snapshots
            WHERE account_id = ? AND fetched_at < ?
            ORDER BY fetched_at DESC
            LIMIT 1
            """,
            (account_id, fetched_at),
        ).fetchone()
        prev = dict(prev_row) if prev_row else None
        prev_id = prev.get("id") if prev else None
        time_diff_hours = None
        if prev and prev.get("fetched_at"):
            try:
                from datetime import datetime

                current_ts = datetime.fromisoformat(fetched_at.replace("Z", "+00:00"))
                prev_ts = datetime.fromisoformat(prev["fetched_at"].replace("Z", "+00:00"))
                time_diff_hours = (current_ts - prev_ts).total_seconds() / 3600
            except Exception:
                time_diff_hours = None

        # Recompute delta against previous snapshot in DB when available
        if prev_id:
            prev_skills = [dict(s) for s in conn.execute("SELECT name, level, xp, rank FROM skills WHERE snapshot_id = ?", (prev_id,)).fetchall()]
            prev_acts = [dict(a) for a in conn.execute("SELECT name, score, rank FROM activities WHERE snapshot_id = ?", (prev_id,)).fetchall()]
            computed_delta = compute_snapshot_delta(
                {"skills": prev_skills, "activities": prev_acts},
                {"skills": current_skills, "activities": current_activities},
            )
            delta = computed_delta

        if delta is None:
            return None

        conn.execute(
            """
            INSERT INTO snapshots_deltas (
                current_snapshot_id, previous_snapshot_id,
                total_xp_delta, skill_deltas, activity_deltas, time_diff_hours
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot_db_id,
                prev_id,
                delta.get("total_xp_delta") or 0,
                json.dumps(delta.get("skill_deltas") or []),
                json.dumps(delta.get("activity_deltas") or []),
                time_diff_hours,
            ),
        )
        return delta

    def ingest_result(self, result: SnapshotResult) -> Optional[Dict[str, Any]]:
        """Persist snapshot result into DB. Returns details including delta."""
        if not result.success or not result.payload:
            return None

        payload = result.payload
        metadata = payload.get("metadata", {})
        data = payload.get("data", {})
        delta = payload.get("delta")

        player = metadata.get("player") or result.player
        resolved_mode = metadata.get("resolved_mode") or metadata.get("requested_mode") or "main"
        snapshot_id = metadata.get("snapshot_id")
        fetched_at = metadata.get("fetched_at")

        skills = data.get("skills") or []
        activities = data.get("activities") or []
        total_level = metadata.get("total_level")
        total_xp = metadata.get("total_xp")
        if total_level is None or total_xp is None:
            total_level, total_xp = self._total_from_skills(skills)

        with self.db.get_connection() as conn:
            existing = conn.execute(
                "SELECT id FROM snapshots WHERE snapshot_id = ?",
                (snapshot_id,),
            ).fetchone()
            if existing:
                return existing["id"]

            account_id = self._ensure_account(conn, player, resolved_mode)

            cursor = conn.execute(
                """
                INSERT INTO snapshots (
                    snapshot_id, account_id, fetched_at, total_xp, total_level,
                    endpoint, latency_ms, agent_version, requested_mode, resolved_mode, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot_id,
                    account_id,
                    fetched_at,
                    total_xp,
                    total_level,
                    metadata.get("endpoint"),
                    metadata.get("latency_ms"),
                    metadata.get("agent_version"),
                    metadata.get("requested_mode"),
                    resolved_mode,
                    json.dumps(metadata),
                ),
            )
            snapshot_db_id = cursor.lastrowid

            self._insert_skills(conn, snapshot_db_id, skills)
            self._insert_activities(conn, snapshot_db_id, activities)
            delta_used = self._insert_delta(conn, account_id, snapshot_db_id, fetched_at, delta, skills, activities)
            delta_summary = summarize_delta(delta_used) if delta_used else None

            return {
                "snapshot_db_id": snapshot_db_id,
                "delta": delta_used,
                "delta_summary": delta_summary,
            }
