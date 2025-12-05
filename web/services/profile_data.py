"""Profile data access for RSN dashboards."""

from __future__ import annotations

import json
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from pathlib import Path
from database.connection import DatabaseConnection


class ProfileDataService:
    def __init__(self, db: Optional[DatabaseConnection] = None) -> None:
        self.db = db or DatabaseConnection()

    def _snapshot_filename(self, fetched_at: str, account_name: str) -> str:
        try:
            ts = datetime.fromisoformat(fetched_at.replace("Z", "+00:00"))
        except Exception:
            return ""
        safe = account_name.replace(" ", "_")
        path = Path(f"data/snapshots/{safe}/{ts.strftime('%Y%m%d_%H%M%S')}.json")
        if path.exists():
            return str(path)
        # Fallback: search for matching snapshot_id file
        snap_dir = Path(f"data/snapshots/{safe}")
        if snap_dir.exists():
            for json_file in snap_dir.glob("*.json"):
                try:
                    import json

                    md = json.loads(json_file.read_text()).get("metadata", {})
                    if md.get("fetched_at") == fetched_at:
                        return str(json_file)
                except Exception:
                    continue
        return ""

    def _report_path(self, snapshot_id: str, account_name: str) -> str:
        safe = account_name.replace(" ", "_")
        path = Path(f"reports/{safe}/{snapshot_id}.md")
        if path.exists():
            return str(path)
        # Fallback: scan reports dir for matching snapshot_id
        reports_dir = Path(f"reports/{safe}")
        if reports_dir.exists():
            candidate = reports_dir / f"{snapshot_id}.md"
            if candidate.exists():
                return str(candidate)
        return ""

    def _load_deltas(self, conn, snapshot_ids: List[int]) -> dict[int, dict]:
        if not snapshot_ids:
            return {}
        placeholders = ",".join("?" for _ in snapshot_ids)
        rows = conn.execute(
            f"SELECT * FROM snapshots_deltas WHERE current_snapshot_id IN ({placeholders})",
            snapshot_ids,
        ).fetchall()
        deltas: dict[int, dict] = {}
        for row in rows:
            rd = dict(row)
            # Parse JSON fields into Python structures
            for key in ("skill_deltas", "activity_deltas"):
                try:
                    rd[key] = json.loads(rd.get(key) or "[]")
                except Exception:
                    rd[key] = []
            deltas[row["current_snapshot_id"]] = rd
        return deltas

    def _delta_summary(self, delta_row: Optional[dict]) -> str:
        if not delta_row:
            return "No delta recorded"
        total_xp_delta = delta_row.get("total_xp_delta")
        hours = delta_row.get("time_diff_hours")
        parts = []
        if total_xp_delta is not None:
            parts.append(f"{total_xp_delta:+,} XP")
        if hours:
            parts.append(f"over {hours:.1f}h")
        return " ".join(parts) if parts else "Delta recorded"

    def _friendly_time(self, fetched_at: Optional[str]) -> str:
        if not fetched_at:
            return "—"
        try:
            ts = datetime.fromisoformat(fetched_at.replace("Z", "+00:00"))
            return ts.strftime("%Y-%m-%d %H:%M UTC")
        except Exception:
            return fetched_at

    def _time_bounds(self, timeframe: str) -> Optional[datetime]:
        now = datetime.now(timezone.utc)
        if timeframe == "7d":
            return now - timedelta(days=7)
        if timeframe == "30d":
            return now - timedelta(days=30)
        if timeframe == "mtd":
            return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return None  # latest / all-time

    def _compute_window_delta(self, conn, account_id: int, since: Optional[datetime]) -> Optional[dict]:
        """Compute delta between earliest and latest snapshots within window (or all-time if since is None)."""
        if since is None:
            snaps = conn.execute(
                """
                SELECT id, fetched_at, total_xp, total_level
                FROM snapshots
                WHERE account_id = ?
                ORDER BY fetched_at ASC
                """,
                (account_id,),
            ).fetchall()
        else:
            since_iso = since.isoformat()
            snaps = conn.execute(
                """
                SELECT id, fetched_at, total_xp, total_level
                FROM snapshots
                WHERE account_id = ? AND fetched_at >= ?
                ORDER BY fetched_at ASC
                """,
                (account_id, since_iso),
            ).fetchall()
        if not snaps:
            return None
        baseline = dict(snaps[0])
        latest = dict(snaps[-1])
        if baseline["id"] == latest["id"]:
            # Only one snapshot in window: treat as zero delta (baseline only).
            return {
                "current_snapshot_id": latest.get("id"),
                "previous_snapshot_id": baseline.get("id"),
                "total_xp_delta": 0,
                "skill_deltas": [],
                "activity_deltas": [],
                "time_diff_hours": None,
            }

        def load_skills(snapshot_id: int):
            rows = conn.execute(
                "SELECT name, xp, level FROM skills WHERE snapshot_id = ?",
                (snapshot_id,),
            ).fetchall()
            return {r["name"]: dict(r) for r in rows}

        def load_acts(snapshot_id: int):
            rows = conn.execute(
                "SELECT name, score FROM activities WHERE snapshot_id = ?",
                (snapshot_id,),
            ).fetchall()
            return {r["name"]: dict(r) for r in rows}

        base_skills = load_skills(baseline["id"])
        latest_skills = load_skills(latest["id"])
        skill_deltas: list[dict] = []
        for name, ls in latest_skills.items():
            prev = base_skills.get(name, {})
            skill_deltas.append(
                {
                    "name": name,
                    "xp_delta": (ls.get("xp") or 0) - (prev.get("xp") or 0),
                    "level_delta": (ls.get("level") or 0) - (prev.get("level") or 0),
                }
            )

        base_acts = load_acts(baseline["id"])
        latest_acts = load_acts(latest["id"])
        activity_deltas: list[dict] = []
        for name, la in latest_acts.items():
            prev = base_acts.get(name, {})
            activity_deltas.append(
                {
                    "name": name,
                    "score_delta": (la.get("score") or 0) - (prev.get("score") or 0),
                }
            )

        try:
            current_ts = datetime.fromisoformat(latest.get("fetched_at", "").replace("Z", "+00:00"))
            prev_ts = datetime.fromisoformat(baseline.get("fetched_at", "").replace("Z", "+00:00"))
            time_diff_hours = (current_ts - prev_ts).total_seconds() / 3600
        except Exception:
            time_diff_hours = None

        delta_row = {
            "current_snapshot_id": latest.get("id"),
            "previous_snapshot_id": baseline.get("id"),
            "total_xp_delta": (latest.get("total_xp") or 0) - (baseline.get("total_xp") or 0),
            "skill_deltas": skill_deltas,
            "activity_deltas": activity_deltas,
            "time_diff_hours": time_diff_hours,
        }
        return delta_row

    def _compute_delta_from_db(self, conn, snapshot_row: dict[str, Any]) -> Optional[dict]:
        """Compute delta if none stored, by comparing to previous snapshot."""
        account_id = snapshot_row.get("account_id")
        fetched_at = snapshot_row.get("fetched_at")
        if not account_id or not fetched_at:
            return None

        prev_row = conn.execute(
            """
            SELECT * FROM snapshots
            WHERE account_id = ? AND fetched_at < ?
            ORDER BY fetched_at DESC LIMIT 1
            """,
            (account_id, fetched_at),
        ).fetchone()
        if not prev_row:
            return None
        prev = dict(prev_row)

        prev_skills = [
            dict(s)
            for s in conn.execute(
                "SELECT * FROM skills WHERE snapshot_id = ?",
                (prev.get("id"),),
            ).fetchall()
        ]
        cur_skills = [
            dict(s)
            for s in conn.execute(
                "SELECT * FROM skills WHERE snapshot_id = ?",
                (snapshot_row["id"],),
            ).fetchall()
        ]

        prev_acts = [
            dict(a)
            for a in conn.execute(
                "SELECT * FROM activities WHERE snapshot_id = ?",
                (prev.get("id"),),
            ).fetchall()
        ]
        cur_acts = [
            dict(a)
            for a in conn.execute(
                "SELECT * FROM activities WHERE snapshot_id = ?",
                (snapshot_row["id"],),
            ).fetchall()
        ]

        skill_map_prev = {s.get("name"): s for s in prev_skills}
        skill_deltas: list[dict[str, Any]] = []
        for s in cur_skills:
            prev_s = skill_map_prev.get(s["name"], {})
            skill_deltas.append(
                {
                    "name": s["name"],
                    "xp_delta": (s.get("xp") or 0) - (prev_s.get("xp") or 0),
                    "level_delta": (s.get("level") or 0) - (prev_s.get("level") or 0),
                }
            )

        act_map_prev = {a.get("name"): a for a in prev_acts}
        activity_deltas: list[dict[str, Any]] = []
        for a in cur_acts:
            prev_a = act_map_prev.get(a["name"], {})
            activity_deltas.append(
                {
                    "name": a["name"],
                    "score_delta": (a.get("score") or 0) - (prev_a.get("score") or 0),
                }
            )

        try:
            current_ts = datetime.fromisoformat(fetched_at.replace("Z", "+00:00"))
            prev_ts = datetime.fromisoformat(prev.get("fetched_at", "").replace("Z", "+00:00"))
            time_diff_hours = (current_ts - prev_ts).total_seconds() / 3600
        except Exception:
            time_diff_hours = None

        delta_row = {
            "current_snapshot_id": snapshot_row.get("id"),
            "previous_snapshot_id": prev.get("id"),
            "total_xp_delta": (snapshot_row.get("total_xp") or 0) - (prev.get("total_xp") or 0),
            "skill_deltas": skill_deltas,
            "activity_deltas": activity_deltas,
            "time_diff_hours": time_diff_hours,
        }
        return delta_row

    def get_snapshot_payload(self, snapshot_id: str) -> Optional[dict]:
        """Build a JSON-like payload for a snapshot using DB-stored data."""
        with self.db.get_connection() as conn:
            snapshot_row = conn.execute(
                """
                SELECT s.*, a.name as account_name, a.display_name, a.default_mode
                FROM snapshots s
                JOIN accounts a ON s.account_id = a.id
                WHERE s.snapshot_id = ?
                """,
                (snapshot_id,),
            ).fetchone()
            if not snapshot_row:
                return None

            snapshot = dict(snapshot_row)
            skills = conn.execute(
                "SELECT * FROM skills WHERE snapshot_id = ? ORDER BY skill_id",
                (snapshot_row["id"],),
            ).fetchall()
            activities = conn.execute(
                "SELECT * FROM activities WHERE snapshot_id = ? ORDER BY activity_id",
                (snapshot_row["id"],),
            ).fetchall()

            # Deltas
            deltas_map = self._load_deltas(conn, [snapshot_row["id"]])
            delta_row = deltas_map.get(snapshot_row["id"])
            if not delta_row:
                delta_row = self._compute_delta_from_db(conn, snapshot)

            metadata = snapshot.get("metadata")
            try:
                metadata = json.loads(metadata) if isinstance(metadata, str) else dict(metadata or {})
            except Exception:
                metadata = {}

            payload = {
                "metadata": {
                    **metadata,
                    "snapshot_id": snapshot.get("snapshot_id"),
                    "player": snapshot.get("account_name"),
                    "requested_mode": snapshot.get("requested_mode"),
                    "resolved_mode": snapshot.get("resolved_mode"),
                    "fetched_at": snapshot.get("fetched_at"),
                    "fetched_at_display": self._friendly_time(snapshot.get("fetched_at")),
                    "endpoint": snapshot.get("endpoint"),
                    "latency_ms": snapshot.get("latency_ms"),
                    "agent_version": snapshot.get("agent_version"),
                    "total_level": snapshot.get("total_level"),
                    "total_xp": snapshot.get("total_xp"),
                },
                "data": {
                    "skills": [dict(s) for s in skills],
                    "activities": [dict(a) for a in activities],
                },
            }

            if delta_row:
                payload["delta"] = delta_row
                payload["delta_summary"] = self._delta_summary(delta_row)
            else:
                payload["delta"] = None
                payload["delta_summary"] = "No delta recorded"

            return payload

    def get_profile(self, account_name: str, limit: int = 10, offset: int = 0) -> dict:
        with self.db.get_connection() as conn:
            account = conn.execute(
                "SELECT * FROM accounts WHERE name = ?",
                (account_name,),
            ).fetchone()
            if not account:
                return {"account": None, "latest": None, "timeline": [], "total": 0}

            account_id = account["id"]

            latest = conn.execute(
                "SELECT * FROM snapshots WHERE account_id = ? ORDER BY fetched_at DESC LIMIT 1",
                (account_id,),
            ).fetchone()

            latest_dict: Optional[Dict] = None
            if latest:
                latest_dict = dict(latest)
                skills = conn.execute("SELECT * FROM skills WHERE snapshot_id = ?", (latest["id"],)).fetchall()
                acts = conn.execute("SELECT * FROM activities WHERE snapshot_id = ?", (latest["id"],)).fetchall()
                latest_dict["skills"] = [dict(s) for s in skills]
                latest_dict["activities"] = [dict(a) for a in acts]
                deltas_map = self._load_deltas(conn, [latest["id"]])
                delta_row = deltas_map.get(latest["id"])
                if not delta_row:
                    delta_row = self._compute_delta_from_db(conn, latest_dict)
                if delta_row:
                    latest_dict["delta"] = delta_row
                    latest_dict["delta_summary"] = self._delta_summary(delta_row)
                fetched_at_val = latest_dict.get("fetched_at")
                snapshot_id_val = latest_dict.get("snapshot_id")
                latest_dict["json_path"] = self._snapshot_filename(fetched_at_val, account_name) if fetched_at_val else ""
                latest_dict["report_path"] = self._report_path(snapshot_id_val, account_name) if snapshot_id_val else ""
                latest_dict["fetched_at_display"] = self._friendly_time(fetched_at_val)

            timeline_rows = conn.execute(
                "SELECT * FROM snapshots WHERE account_id = ? ORDER BY fetched_at DESC LIMIT ? OFFSET ?",
                (account_id, limit, offset),
            ).fetchall()
            timeline = []
            deltas_map = self._load_deltas(conn, [r["id"] for r in timeline_rows])
            for r in timeline_rows:
                rd = dict(r)
                rd["json_path"] = self._snapshot_filename(rd.get("fetched_at", ""), account_name) if rd.get("fetched_at") else ""
                rd["report_path"] = self._report_path(rd.get("snapshot_id", ""), account_name) if rd.get("snapshot_id") else ""
                delta_row = deltas_map.get(r["id"])
                if not delta_row:
                    delta_row = self._compute_delta_from_db(conn, rd)
                if delta_row:
                    rd["delta"] = delta_row
                    rd["delta_summary"] = self._delta_summary(delta_row)
                rd["fetched_at_display"] = self._friendly_time(rd.get("fetched_at"))
                timeline.append(rd)

            total = conn.execute(
                "SELECT COUNT(*) as c FROM snapshots WHERE account_id = ?",
                (account_id,),
            ).fetchone()["c"]

            return {
                "account": dict(account),
                "latest": latest_dict,
                "timeline": timeline,
                "total": total,
            }

    def get_series(
        self,
        account_name: str,
        *,
        from_ts: Optional[str] = None,
        to_ts: Optional[str] = None,
        limit: int = 500,
    ) -> Dict[str, Any]:
        """Return time-series data for charts: total xp/level plus per-skill and activity snapshots."""
        with self.db.get_connection() as conn:
            account = conn.execute("SELECT * FROM accounts WHERE name = ?", (account_name,)).fetchone()
            if not account:
                return {"series": []}

            params: List[Any] = [account["id"]]
            where = "WHERE account_id = ?"
            if from_ts:
                where += " AND fetched_at >= ?"
                params.append(from_ts)
            if to_ts:
                where += " AND fetched_at <= ?"
                params.append(to_ts)

            rows = conn.execute(
                f"""
                SELECT * FROM snapshots
                {where}
                ORDER BY fetched_at ASC
                LIMIT ?
                """,
                (*params, limit),
            ).fetchall()

            series: List[Dict[str, Any]] = []
            for r in rows:
                rd = dict(r)
                skills = conn.execute("SELECT name, level, xp FROM skills WHERE snapshot_id = ?", (r["id"],)).fetchall()
                acts = conn.execute("SELECT name, score FROM activities WHERE snapshot_id = ?", (r["id"],)).fetchall()
                series.append(
                    {
                        "snapshot_id": rd.get("snapshot_id"),
                        "fetched_at": rd.get("fetched_at"),
                        "total_xp": rd.get("total_xp"),
                        "total_level": rd.get("total_level"),
                        "resolved_mode": rd.get("resolved_mode"),
                        "skills": [dict(s) for s in skills],
                        "activities": [dict(a) for a in acts],
                    }
                )

            return {"series": series}
