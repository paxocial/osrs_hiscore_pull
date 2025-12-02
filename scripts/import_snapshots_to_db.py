#!/usr/bin/env python3
"""Import snapshot JSON files from disk into the analytics database.

Scans data/snapshots/<player>/<timestamp>.json produced by SnapshotAgent and
inserts accounts, snapshots, skills, and activities. Idempotent: skips existing
snapshot_ids.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from database.connection import DatabaseConnection
from core.constants import SKILLS, ACTIVITY_LOOKUP


def load_snapshot(path: Path) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    metadata = payload.get("metadata", {})
    data = payload.get("data", {})
    return metadata, data


def extract_skills(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    skills = data.get("skills") or []
    if isinstance(skills, dict):
        # Convert dict keyed by name/id to list
        skills = list(skills.values())
    return skills


def extract_activities(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    activities = data.get("activities") or []
    if isinstance(activities, dict):
        activities = list(activities.values())
    return activities


def total_from_skills(skills: List[Dict[str, Any]]) -> Tuple[int, int]:
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


def iter_snapshot_files(root: Path) -> Iterable[Path]:
    if not root.exists():
        return []
    for player_dir in root.iterdir():
        if not player_dir.is_dir():
            continue
        for snap in sorted(player_dir.glob("*.json")):
            yield snap


def import_snapshots(db: DatabaseConnection, root: Path) -> Dict[str, int]:
    stats = {"accounts": 0, "snapshots": 0, "skills": 0, "activities": 0, "skipped": 0}
    with db.get_connection() as conn:
        for snap_path in iter_snapshot_files(root):
            try:
                metadata, data = load_snapshot(snap_path)
            except Exception:
                stats["skipped"] += 1
                continue

            player = metadata.get("player") or snap_path.parent.name
            snapshot_id = metadata.get("snapshot_id")
            if not snapshot_id or not player:
                stats["skipped"] += 1
                continue

            exists = conn.execute(
                "SELECT id FROM snapshots WHERE snapshot_id = ?",
                (snapshot_id,),
            ).fetchone()
            if exists:
                stats["skipped"] += 1
                continue

            # Ensure account
            resolved_mode = metadata.get("resolved_mode") or metadata.get("requested_mode") or "main"
            account = conn.execute(
                "SELECT id FROM accounts WHERE name = ?",
                (player,),
            ).fetchone()
            if not account:
                cursor = conn.execute(
                    "INSERT INTO accounts (name, display_name, default_mode) VALUES (?, ?, ?)",
                    (player, metadata.get("display_name"), resolved_mode),
                )
                account_id = cursor.lastrowid
                stats["accounts"] += 1
            else:
                account_id = account["id"]
                # Update default_mode to latest resolved mode
                conn.execute("UPDATE accounts SET default_mode = ? WHERE id = ?", (resolved_mode, account_id))

            # Totals
            skills = extract_skills(data)
            total_level, total_xp = total_from_skills(skills)

            fetched_at = metadata.get("fetched_at") or metadata.get("timestamp")
            # Insert snapshot
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
            db_snapshot_id = cursor.lastrowid
            stats["snapshots"] += 1

            # Skills
            for idx, skill in enumerate(skills):
                skill_id = skill.get("id") or skill.get("skill_id")
                if skill_id is None:
                    # Try to map by name; fallback to index
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
                        db_snapshot_id,
                        skill_id,
                        skill.get("name"),
                        skill.get("level"),
                        skill.get("xp"),
                        skill.get("rank"),
                    ),
                )
                stats["skills"] += 1

            # Activities
            for idx, activity in enumerate(extract_activities(data)):
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
                        db_snapshot_id,
                        activity_id,
                        activity.get("name"),
                        activity.get("score"),
                        activity.get("rank"),
                    ),
                )
                stats["activities"] += 1
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Import snapshot JSON files into the database.")
    parser.add_argument("--root", default="data/snapshots", help="Root directory of snapshot JSONs.")
    parser.add_argument("--db-path", default="data/analytics.db", help="Path to SQLite database.")
    args = parser.parse_args()

    db = DatabaseConnection(Path(args.db_path))
    db.initialize_database()
    stats = import_snapshots(db, Path(args.root))
    print(f"Accounts added:   {stats['accounts']}")
    print(f"Snapshots added:  {stats['snapshots']}")
    print(f"Skills added:     {stats['skills']}")
    print(f"Activities added: {stats['activities']}")
    print(f"Skipped (existing/invalid): {stats['skipped']}")


if __name__ == "__main__":
    main()
