"""Automatic migration system for JSON snapshots to database."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

from .connection import DatabaseConnection

logger = logging.getLogger(__name__)


class JSONMigrationManager:
    """Manages migration of JSON snapshots to the database."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db = DatabaseConnection(db_path or Path("data/analytics.db"))
        self.snapshots_dir = Path("data/snapshots")
        self.migration_log: List[str] = []

    def ensure_database_ready(self) -> None:
        """Ensure database is initialized and ready."""
        if not self.db._is_initialized():
            self.db.initialize_database()
            self.migration_log.append("Database initialized for migration")

    def scan_for_snapshots(self) -> Dict[str, List[Path]]:
        """Scan for all JSON snapshot files organized by account."""
        if not self.snapshots_dir.exists():
            self.migration_log.append("No snapshots directory found")
            return {}

        account_snapshots = {}

        for account_dir in self.snapshots_dir.iterdir():
            if account_dir.is_dir():
                account_name = account_dir.name
                json_files = list(account_dir.glob("*.json"))
                if json_files:
                    account_snapshots[account_name] = sorted(json_files)
                    self.migration_log.append(
                        f"Found {len(json_files)} snapshots for account: {account_name}"
                    )

        return account_snapshots

    def get_already_migrated_snapshots(self) -> Set[str]:
        """Get set of snapshot IDs that are already in the database."""
        with self.db.get_connection() as conn:
            result = conn.execute("SELECT snapshot_id FROM snapshots").fetchall()
            return {row["snapshot_id"] for row in result}

    def parse_snapshot_file(self, file_path: Path) -> Optional[Dict]:
        """Parse a JSON snapshot file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to parse snapshot file {file_path}: {e}")
            self.migration_log.append(f"Failed to parse {file_path}: {e}")
            return None

    def calculate_total_values(self, snapshot_data: Dict) -> tuple[int, int]:
        """Calculate total level and XP from snapshot data."""
        skills = snapshot_data.get("data", {}).get("skills", [])

        total_xp = sum(skill.get("xp", 0) for skill in skills)

        # Calculate total level excluding "Overall" skill
        total_level = sum(
            skill.get("level", 0) for skill in skills
            if skill.get("name") != "Overall"
        )

        return total_level, total_xp

    def generate_snapshot_id(self, metadata: Dict, file_path: Path) -> str:
        """Generate a snapshot ID if not present in metadata."""
        if "snapshot_id" in metadata:
            return metadata["snapshot_id"]

        # Generate ID from file path and timestamp
        from uuid import NAMESPACE_URL, uuid5
        timestamp = metadata.get("fetched_at", "unknown")
        player = metadata.get("player", "unknown")

        # Use file path as namespace to ensure uniqueness
        namespace = f"osrs:snapshot:{player}:{file_path.name}"
        return str(uuid5(NAMESPACE_URL, namespace))

    def migrate_snapshot(self, snapshot_data: Dict, check_existing: bool = True, file_path: Optional[Path] = None) -> bool:
        """Migrate a single snapshot to the database."""
        try:
            metadata = snapshot_data["metadata"]

            # Handle old vs new metadata formats
            snapshot_id = self.generate_snapshot_id(metadata, file_path or Path("unknown"))

            # Normalize mode fields
            if "resolved_mode" in metadata:
                requested_mode = metadata.get("requested_mode", metadata["resolved_mode"])
                resolved_mode = metadata["resolved_mode"]
            else:
                # Old format: single "mode" field
                resolved_mode = metadata["mode"]
                requested_mode = resolved_mode

            # Check if already migrated
            if check_existing:
                with self.db.get_connection() as conn:
                    existing = conn.execute(
                        "SELECT id FROM snapshots WHERE snapshot_id = ?",
                        (snapshot_id,)
                    ).fetchone()
                    if existing:
                        return False  # Already migrated

            # Get or create account
            account_name = metadata["player"]

            with self.db.get_connection() as conn:
                # Get account
                account_result = conn.execute(
                    "SELECT id FROM accounts WHERE name = ?",
                    (account_name,)
                ).fetchone()

                if not account_result:
                    # Create account
                    cursor = conn.execute(
                        """INSERT INTO accounts (name, default_mode, active, metadata)
                           VALUES (?, ?, ?, ?)""",
                        (account_name, resolved_mode, 1, json.dumps(metadata))
                    )
                    account_id = cursor.lastrowid
                    self.migration_log.append(f"Created account: {account_name}")
                else:
                    account_id = account_result["id"]

                # Calculate totals
                total_level, total_xp = self.calculate_total_values(snapshot_data)

                # Insert snapshot
                fetched_at = datetime.fromisoformat(
                    metadata["fetched_at"].replace("Z", "+00:00")
                ).isoformat()

                snapshot_cursor = conn.execute(
                    """INSERT INTO snapshots
                       (account_id, snapshot_id, requested_mode, resolved_mode,
                        fetched_at, endpoint, latency_ms, agent_version,
                        total_level, total_xp, metadata)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        account_id,
                        snapshot_id,
                        requested_mode,
                        resolved_mode,
                        fetched_at,
                        metadata.get("endpoint"),
                        metadata.get("latency_ms"),
                        metadata.get("agent_version"),
                        total_level,
                        total_xp,
                        json.dumps(metadata)
                    )
                )
                snapshot_db_id = snapshot_cursor.lastrowid

                # Insert skills
                for skill in snapshot_data.get("data", {}).get("skills", []):
                    conn.execute(
                        """INSERT INTO skills
                           (snapshot_id, skill_id, name, level, xp, rank)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (
                            snapshot_db_id,
                            skill["id"],
                            skill["name"],
                            skill.get("level"),
                            skill.get("xp"),
                            skill.get("rank")
                        )
                    )

                # Insert activities
                for activity in snapshot_data.get("data", {}).get("activities", []):
                    conn.execute(
                        """INSERT INTO activities
                           (snapshot_id, activity_id, name, score, rank)
                           VALUES (?, ?, ?, ?, ?)""",
                        (
                            snapshot_db_id,
                            activity["id"],
                            activity["name"],
                            activity.get("score"),
                            activity.get("rank")
                        )
                    )

                # Insert deltas if available
                if "delta" in snapshot_data and snapshot_data["delta"]:
                    delta_data = snapshot_data["delta"]

                    # Find previous snapshot for delta calculation
                    previous_result = conn.execute(
                        """SELECT id FROM snapshots
                           WHERE account_id = ? AND fetched_at < ?
                           ORDER BY fetched_at DESC LIMIT 1""",
                        (account_id, fetched_at)
                    ).fetchone()

                    previous_snapshot_id = previous_result["id"] if previous_result else None

                    conn.execute(
                        """INSERT INTO snapshots_deltas
                           (current_snapshot_id, previous_snapshot_id, total_xp_delta,
                            skill_deltas, activity_deltas, time_diff_hours)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (
                            snapshot_db_id,
                            previous_snapshot_id,
                            delta_data.get("total_xp_delta", 0),
                            json.dumps(delta_data.get("skill_deltas", [])),
                            json.dumps(delta_data.get("activity_deltas", [])),
                            None  # TODO: Calculate time difference if needed
                        )
                    )

                self.migration_log.append(f"Migrated snapshot: {snapshot_id}")
                return True

        except Exception as e:
            logger.error(f"Failed to migrate snapshot: {e}")
            self.migration_log.append(f"Failed to migrate snapshot: {e}")
            return False

    def run_migration(self, force: bool = False) -> Dict[str, int]:
        """Run complete migration of all JSON snapshots."""
        self.migration_log.clear()
        self.migration_log.append(f"Starting migration at {datetime.now()}")

        self.ensure_database_ready()

        # Scan for snapshots
        account_snapshots = self.scan_for_snapshots()
        if not account_snapshots:
            self.migration_log.append("No snapshots found to migrate")
            return {"accounts": 0, "snapshots": 0, "migrated": 0, "skipped": 0}

        # Get already migrated snapshots
        if not force:
            already_migrated = self.get_already_migrated_snapshots()
            self.migration_log.append(f"Found {len(already_migrated)} already migrated snapshots")
        else:
            already_migrated = set()
            self.migration_log.append("Force mode: migrating all snapshots")

        # Migration statistics
        stats = {"accounts": 0, "snapshots": 0, "migrated": 0, "skipped": 0}

        # Process each account
        for account_name, snapshot_files in account_snapshots.items():
            stats["accounts"] += 1
            stats["snapshots"] += len(snapshot_files)

            self.migration_log.append(f"Processing account: {account_name} ({len(snapshot_files)} files)")

            for snapshot_file in snapshot_files:
                snapshot_data = self.parse_snapshot_file(snapshot_file)
                if not snapshot_data:
                    stats["skipped"] += 1
                    continue

                # Generate snapshot_id for checking if already migrated
                snapshot_id = self.generate_snapshot_id(snapshot_data["metadata"], snapshot_file)
                if snapshot_id in already_migrated and not force:
                    stats["skipped"] += 1
                    continue

                if self.migrate_snapshot(snapshot_data, check_existing=not force, file_path=snapshot_file):
                    stats["migrated"] += 1
                else:
                    stats["skipped"] += 1

        self.migration_log.append(f"Migration completed: {stats}")
        return stats

    def auto_migrate_new_snapshots(self) -> int:
        """Automatically migrate any new JSON snapshots (runs in background)."""
        try:
            self.ensure_database_ready()
            account_snapshots = self.scan_for_snapshots()
            already_migrated = self.get_already_migrated_snapshots()

            migrated_count = 0
            for account_name, snapshot_files in account_snapshots.items():
                for snapshot_file in snapshot_files:
                    snapshot_data = self.parse_snapshot_file(snapshot_file)
                    if not snapshot_data:
                        continue

                    snapshot_id = self.generate_snapshot_id(snapshot_data["metadata"], snapshot_file)
                    if snapshot_id not in already_migrated:
                        if self.migrate_snapshot(snapshot_data, check_existing=True, file_path=snapshot_file):
                            migrated_count += 1
                            already_migrated.add(snapshot_id)

            if migrated_count > 0:
                logger.info(f"Auto-migrated {migrated_count} new snapshots")

            return migrated_count

        except Exception as e:
            logger.error(f"Auto-migration failed: {e}")
            return 0

    def get_migration_log(self) -> List[str]:
        """Get the migration log."""
        return self.migration_log.copy()

    def print_migration_summary(self, stats: Dict[str, int]) -> None:
        """Print a summary of the migration results."""
        print("\n" + "="*50)
        print("MIGRATION SUMMARY")
        print("="*50)
        print(f"Accounts processed: {stats['accounts']}")
        print(f"Total snapshots found: {stats['snapshots']}")
        print(f"Snapshots migrated: {stats['migrated']}")
        print(f"Snapshots skipped: {stats['skipped']}")

        if stats['migrated'] > 0:
            print(f"\n✅ Successfully migrated {stats['migrated']} snapshots")
        else:
            print("\n📝 No new snapshots to migrate")

        print("="*50)


# Background migration functions for integration with existing agents

def ensure_database_and_migrate():
    """Ensure database is ready and run auto-migration."""
    try:
        migration_manager = JSONMigrationManager()
        migrated_count = migration_manager.auto_migrate_new_snapshots()
        return migrated_count
    except Exception as e:
        logger.warning(f"Background migration failed: {e}")
        return 0


def get_migration_status() -> Dict[str, any]:
    """Get current migration status for reporting."""
    try:
        migration_manager = JSONMigrationManager()
        migration_manager.ensure_database_ready()

        with migration_manager.db.get_connection() as conn:
            # Get counts
            account_count = conn.execute("SELECT COUNT(*) as count FROM accounts").fetchone()["count"]
            snapshot_count = conn.execute("SELECT COUNT(*) as count FROM snapshots").fetchone()["count"]

            # Get latest snapshot
            latest = conn.execute(
                "SELECT fetched_at FROM snapshots ORDER BY fetched_at DESC LIMIT 1"
            ).fetchone()

            return {
                "database_ready": True,
                "accounts_count": account_count,
                "snapshots_count": snapshot_count,
                "latest_snapshot": latest["fetched_at"] if latest else None
            }

    except Exception as e:
        return {
            "database_ready": False,
            "error": str(e),
            "accounts_count": 0,
            "snapshots_count": 0,
            "latest_snapshot": None
        }