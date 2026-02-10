"""Account comparison service for head-to-head and roster comparisons."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from database.connection import DatabaseConnection


class ComparisonService:
    def __init__(self, db: Optional[DatabaseConnection] = None) -> None:
        self.db = db or DatabaseConnection()

    def _time_bounds(self, timeframe: str) -> Optional[datetime]:
        now = datetime.now(timezone.utc)
        if timeframe == "7d":
            return now - timedelta(days=7)
        if timeframe == "30d":
            return now - timedelta(days=30)
        if timeframe == "mtd":
            return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return None

    def _player_stats(self, conn, account_name: str, since: Optional[datetime]) -> Optional[Dict[str, Any]]:
        """Get current stats + gains for a single player."""
        account = conn.execute(
            "SELECT * FROM accounts WHERE name = ?", (account_name,)
        ).fetchone()
        if not account:
            return None

        account_id = account["id"]

        # Latest snapshot
        latest = conn.execute(
            "SELECT * FROM snapshots WHERE account_id = ? ORDER BY fetched_at DESC LIMIT 1",
            (account_id,),
        ).fetchone()
        if not latest:
            return None

        # Current skills + activities
        skills = conn.execute(
            "SELECT name, level, xp, rank FROM skills WHERE snapshot_id = ? ORDER BY skill_id",
            (latest["id"],),
        ).fetchall()
        activities = conn.execute(
            "SELECT name, score, rank FROM activities WHERE snapshot_id = ? ORDER BY activity_id",
            (latest["id"],),
        ).fetchall()

        skills_list = [dict(s) for s in skills]
        activities_list = [dict(a) for a in activities]

        # Compute gains over timeframe
        xp_gain = 0
        level_gain = 0
        skill_gains = {}
        activity_gains = {}

        if since is not None:
            since_iso = since.isoformat()
            baseline = conn.execute(
                """SELECT id, total_xp, total_level FROM snapshots
                   WHERE account_id = ? AND fetched_at >= ?
                   ORDER BY fetched_at ASC LIMIT 1""",
                (account_id, since_iso),
            ).fetchone()
        else:
            baseline = conn.execute(
                """SELECT id, total_xp, total_level FROM snapshots
                   WHERE account_id = ?
                   ORDER BY fetched_at ASC LIMIT 1""",
                (account_id,),
            ).fetchone()

        if baseline and baseline["id"] != latest["id"]:
            xp_gain = (latest["total_xp"] or 0) - (baseline["total_xp"] or 0)
            level_gain = (latest["total_level"] or 0) - (baseline["total_level"] or 0)

            base_skills = {
                r["name"]: dict(r)
                for r in conn.execute(
                    "SELECT name, level, xp FROM skills WHERE snapshot_id = ?",
                    (baseline["id"],),
                ).fetchall()
            }
            for sk in skills_list:
                prev = base_skills.get(sk["name"], {})
                sk["xp_gain"] = (sk["xp"] or 0) - (prev.get("xp") or 0)
                sk["level_gain"] = (sk["level"] or 0) - (prev.get("level") or 0)

            base_acts = {
                r["name"]: dict(r)
                for r in conn.execute(
                    "SELECT name, score FROM activities WHERE snapshot_id = ?",
                    (baseline["id"],),
                ).fetchall()
            }
            for act in activities_list:
                prev = base_acts.get(act["name"], {})
                act["score_gain"] = (act["score"] or 0) - (prev.get("score") or 0)
        else:
            for sk in skills_list:
                sk["xp_gain"] = 0
                sk["level_gain"] = 0
            for act in activities_list:
                act["score_gain"] = 0

        return {
            "name": account_name,
            "mode": latest["resolved_mode"],
            "total_xp": latest["total_xp"] or 0,
            "total_level": latest["total_level"] or 0,
            "xp_gain": xp_gain,
            "level_gain": level_gain,
            "skills": skills_list,
            "activities": activities_list,
        }

    def head_to_head(
        self, name_a: str, name_b: str, timeframe: str = "7d"
    ) -> Dict[str, Any]:
        """Compare two players head-to-head."""
        since = self._time_bounds(timeframe)

        with self.db.get_connection() as conn:
            player_a = self._player_stats(conn, name_a, since)
            player_b = self._player_stats(conn, name_b, since)

        players = [p for p in [player_a, player_b] if p is not None]

        # Compute skill winners
        skill_winners = {}
        if player_a and player_b:
            skills_a = {s["name"]: s for s in player_a["skills"]}
            skills_b = {s["name"]: s for s in player_b["skills"]}
            all_skill_names = set(skills_a.keys()) | set(skills_b.keys())
            for name in all_skill_names:
                a_xp = skills_a.get(name, {}).get("xp", 0) or 0
                b_xp = skills_b.get(name, {}).get("xp", 0) or 0
                if a_xp > b_xp:
                    skill_winners[name] = name_a
                elif b_xp > a_xp:
                    skill_winners[name] = name_b
                else:
                    skill_winners[name] = "tie"

        return {
            "players": players,
            "skill_winners": skill_winners,
            "timeframe": timeframe,
        }

    def roster_compare(
        self, clan_id: int, timeframe: str = "7d", metric: str = "xp"
    ) -> Dict[str, Any]:
        """Compare all members of a clan."""
        since = self._time_bounds(timeframe)

        with self.db.get_connection() as conn:
            members = conn.execute(
                """SELECT a.name
                   FROM clan_members cm
                   JOIN accounts a ON cm.account_id = a.id
                   WHERE cm.clan_id = ?""",
                (clan_id,),
            ).fetchall()

            roster = []
            for m in members:
                stats = self._player_stats(conn, m["name"], since)
                if stats:
                    roster.append(stats)

        sort_key = "xp_gain" if metric == "xp" else "level_gain"
        roster.sort(key=lambda x: x.get(sort_key, 0), reverse=True)

        return {
            "members": roster,
            "timeframe": timeframe,
            "metric": metric,
        }

    def search_accounts(self, query: str, limit: int = 10) -> List[str]:
        """Search account names for autocomplete."""
        with self.db.get_connection() as conn:
            rows = conn.execute(
                "SELECT name FROM accounts WHERE name LIKE ? LIMIT ?",
                (f"%{query}%", limit),
            ).fetchall()
            return [r["name"] for r in rows]
