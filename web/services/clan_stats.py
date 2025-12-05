"""Clan statistics aggregation helpers."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from database.connection import DatabaseConnection


class ClanStatsService:
    def __init__(self, db: Optional[DatabaseConnection] = None) -> None:
        self.db = db or DatabaseConnection(reuse_connection=False, check_same_thread=False)

    def _time_bounds(self, timeframe: str) -> Optional[datetime]:
        now = datetime.now(timezone.utc)
        if timeframe == "7d":
            return now - timedelta(days=7)
        if timeframe == "30d":
            return now - timedelta(days=30)
        if timeframe == "mtd":
            return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return None  # latest

    def _load_members(self, clan_id: int) -> List[Dict]:
        with self.db.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT a.id as account_id, a.name, COALESCE(a.default_mode, 'auto') as mode
                FROM clan_members cm
                JOIN accounts a ON cm.account_id = a.id
                WHERE cm.clan_id = ?
                """,
                (clan_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def _latest_snapshot(self, account_id: int):
        with self.db.get_connection() as conn:
            row = conn.execute(
                """
                SELECT id, total_xp, total_level, fetched_at
                FROM snapshots
                WHERE account_id = ?
                ORDER BY fetched_at DESC
                LIMIT 1
                """,
                (account_id,),
            ).fetchone()
            return dict(row) if row else None

    def _deltas_since(self, account_id: int, since: Optional[datetime]):
        if since is None:
            return []
        since_iso = since.isoformat()
        with self.db.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT sd.total_xp_delta, sd.skill_deltas, sd.activity_deltas
                FROM snapshots s
                JOIN snapshots_deltas sd ON sd.current_snapshot_id = s.id
                WHERE s.account_id = ? AND s.fetched_at >= ?
                """,
                (account_id, since_iso),
            ).fetchall()
            return [dict(r) for r in rows]

    def compute_stats(self, clan_id: int, timeframe: str = "7d") -> Dict[str, any]:
        members = self._load_members(clan_id)
        since = self._time_bounds(timeframe)

        totals = {"xp": 0, "level": 0, "members": len(members), "xp_gain": 0, "level_gain": 0}
        per_skill: Dict[str, float] = {}
        per_activity: Dict[str, float] = {}
        per_activity_top: Dict[str, Dict[str, any]] = {}
        per_activity_current: Dict[str, Dict[str, any]] = {}
        leaderboard: List[Dict] = []

        for m in members:
            latest = self._latest_snapshot(m["account_id"])
            xp_gain = 0
            lvl_gain = 0
            if latest:
                totals["xp"] += latest.get("total_xp") or 0
                totals["level"] += latest.get("total_level") or 0
                # Track current highs per activity (for fallback display)
                with self.db.get_connection() as conn:
                    acts = conn.execute(
                        "SELECT name, score FROM activities WHERE snapshot_id = ?",
                        (latest.get("id"),),
                    ).fetchall()
                    for a in acts:
                        name = a["name"]
                        score = a["score"] or 0
                        existing = per_activity_current.get(name)
                        if existing is None or score > existing.get("total", 0):
                            per_activity_current[name] = {"total": score, "top_member": m["name"], "top_value": score}

            deltas = self._deltas_since(m["account_id"], since)
            for d in deltas:
                xp_gain += d.get("total_xp_delta") or 0
                try:
                    skill_ds = json.loads(d.get("skill_deltas") or "[]")
                except Exception:
                    skill_ds = []
                for sd in skill_ds:
                    name = sd.get("name") or ""
                    per_skill[name] = per_skill.get(name, 0) + (sd.get("xp_delta") or 0)
                    lvl_gain += sd.get("level_delta") or 0
                try:
                    act_ds = json.loads(d.get("activity_deltas") or "[]")
                except Exception:
                    act_ds = []
                for ad in act_ds:
                    aname = ad.get("name") or ""
                    delta_val = ad.get("score_delta") or 0
                    per_activity[aname] = per_activity.get(aname, 0) + delta_val
                    if delta_val > 0:
                        top = per_activity_top.get(aname)
                        if top is None or delta_val > top.get("value", 0):
                            per_activity_top[aname] = {"member": m["name"], "value": delta_val}

            totals["xp_gain"] += xp_gain
            totals["level_gain"] += lvl_gain
            leaderboard.append({"name": m["name"], "xp_gain": xp_gain, "level_gain": lvl_gain})

        leaderboard_sorted = sorted(leaderboard, key=lambda x: x.get("xp_gain", 0), reverse=True)
        top_skills = sorted(per_skill.items(), key=lambda kv: kv[1], reverse=True)[:10]

        def classify_activity(name: str) -> str:
            lower = name.lower()
            if "clue" in lower:
                return "clues"
            return "bosses"

        activity_groups: Dict[str, float] = {"bosses": 0, "clues": 0}
        for k, v in per_activity.items():
            activity_groups[classify_activity(k)] = activity_groups.get(classify_activity(k), 0) + v
        all_activities = []
        for name, total in per_activity.items():
            top = per_activity_top.get(name) or {}
            all_activities.append(
                {
                    "name": name,
                    "total": total,
                    "top_member": top.get("member"),
                    "top_value": top.get("value"),
                }
            )
        all_activities = [a for a in all_activities if a["total"] > 0]

        # Fallback: if no delta-based activity gains, show current highest scores
        if not all_activities and per_activity_current:
            for name, info in per_activity_current.items():
                all_activities.append(
                    {
                        "name": name,
                        "total": info.get("total") or 0,
                        "top_member": info.get("top_member"),
                        "top_value": info.get("top_value"),
                    }
                )
            all_activities = [a for a in all_activities if a["total"] > 0]

        all_activities_sorted = sorted(all_activities, key=lambda kv: kv["total"], reverse=True)
        top_activities = all_activities_sorted[:10]
        top_bosses = [a for a in all_activities_sorted if classify_activity(a["name"]) == "bosses"][:10]
        top_clues = [a for a in all_activities_sorted if classify_activity(a["name"]) == "clues"][:10]

        return {
            "timeframe": timeframe,
            "since": since.isoformat() if since else None,
            "totals": totals,
            "leaderboard": leaderboard_sorted,
            "top_skills": top_skills,
            "activities": activity_groups,
            "top_activities": top_activities,
            "top_bosses": top_bosses,
            "top_clues": top_clues,
        }

    def get_leaderboard(
        self,
        clan_id: int,
        timeframe: str = "7d",
        metric: str = "xp",
        page: int = 1,
        page_size: int = 10,
    ) -> Dict[str, any]:
        data = self.compute_stats(clan_id, timeframe=timeframe)
        rows = data.get("leaderboard", [])
        if metric == "levels":
            rows = sorted(rows, key=lambda x: x.get("level_gain", 0), reverse=True)
        total = len(rows)
        page = max(1, page)
        page_size = max(1, min(page_size, 50))
        offset = (page - 1) * page_size
        slice_rows = rows[offset:offset + page_size]
        return {
            "total": total,
            "offset": offset,
            "limit": page_size,
            "page": page,
            "page_size": page_size,
            "metric": metric,
            "timeframe": timeframe,
            "rows": slice_rows,
        }

    def get_last_run(self, clan_id: int) -> Optional[Dict[str, any]]:
        with self.db.get_connection() as conn:
            row = conn.execute(
                """
                SELECT * FROM clan_snapshots
                WHERE clan_id = ?
                ORDER BY started_at DESC
                LIMIT 1
                """,
                (clan_id,),
            ).fetchone()
            if not row:
                return None
            snap = dict(row)
            stats = conn.execute(
                """
                SELECT
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success_count,
                    COUNT(*) as member_total
                FROM clan_snapshot_members
                WHERE clan_snapshot_id = ?
                """,
                (snap["id"],),
            ).fetchone()
            snap["success_count"] = stats["success_count"] if stats else 0
            snap["member_total"] = stats["member_total"] if stats else 0
            return snap
