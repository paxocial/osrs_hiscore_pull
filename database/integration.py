"""Database integration functions for existing agents."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from .connection import DatabaseConnection
from .migrations import JSONMigrationManager

logger = logging.getLogger(__name__)

# Global database instance
_db_instance: Optional[DatabaseConnection] = None
_migration_manager: Optional[JSONMigrationManager] = None


def get_database() -> DatabaseConnection:
    """Get the global database instance, creating if needed."""
    global _db_instance
    if _db_instance is None:
        _db_instance = DatabaseConnection()
        _db_instance.initialize_database()
    return _db_instance


def ensure_database_ready() -> bool:
    """Ensure database is ready for use (auto-migrates if needed)."""
    try:
        global _migration_manager
        if _migration_manager is None:
            _migration_manager = JSONMigrationManager()

        # Run auto-migration for any new JSON files
        migrated_count = _migration_manager.auto_migrate_new_snapshots()
        if migrated_count > 0:
            logger.info(f"Auto-migrated {migrated_count} new snapshots to database")

        return True
    except Exception as e:
        logger.error(f"Failed to ensure database ready: {e}")
        return False


def store_snapshot_in_database(snapshot_data: Dict[str, Any], file_path: Optional[Path] = None) -> bool:
    """Store a snapshot in the database (used by SnapshotAgent)."""
    try:
        ensure_database_ready()
        db = get_database()

        # Check if already exists
        metadata = snapshot_data["metadata"]
        snapshot_id = metadata.get("snapshot_id")

        if snapshot_id:
            with db.get_connection() as conn:
                existing = conn.execute(
                    "SELECT id FROM snapshots WHERE snapshot_id = ?",
                    (snapshot_id,)
                ).fetchone()
                if existing:
                    return False  # Already exists

        # Use migration manager to store
        global _migration_manager
        if _migration_manager is None:
            _migration_manager = JSONMigrationManager()

        success = _migration_manager.migrate_snapshot(snapshot_data, check_existing=False, file_path=file_path)
        return success

    except Exception as e:
        logger.error(f"Failed to store snapshot in database: {e}")
        return False


def get_account_snapshots(account_name: str, limit: int = 10) -> list[Dict[str, Any]]:
    """Get recent snapshots for an account from database."""
    try:
        ensure_database_ready()
        db = get_database()

        with db.get_connection() as conn:
            snapshots = conn.execute("""
                SELECT s.snapshot_id, s.requested_mode, s.resolved_mode, s.fetched_at,
                       s.total_level, s.total_xp, s.metadata
                FROM snapshots s
                JOIN accounts a ON s.account_id = a.id
                WHERE a.name = ?
                ORDER BY s.fetched_at DESC
                LIMIT ?
            """, (account_name, limit)).fetchall()

            return [dict(row) for row in snapshots]

    except Exception as e:
        logger.error(f"Failed to get snapshots for {account_name}: {e}")
        return []


def get_latest_snapshot(account_name: str) -> Optional[Dict[str, Any]]:
    """Get the latest snapshot for an account from database."""
    try:
        ensure_database_ready()
        db = get_database()

        with db.get_connection() as conn:
            snapshot = conn.execute("""
                SELECT s.snapshot_id, s.requested_mode, s.resolved_mode, s.fetched_at,
                       s.total_level, s.total_xp, s.metadata
                FROM snapshots s
                JOIN accounts a ON s.account_id = a.id
                WHERE a.name = ?
                ORDER BY s.fetched_at DESC
                LIMIT 1
            """, (account_name,)).fetchone()

            return dict(snapshot) if snapshot else None

    except Exception as e:
        logger.error(f"Failed to get latest snapshot for {account_name}: {e}")
        return None


def get_snapshot_data(snapshot_id: str) -> Optional[Dict[str, Any]]:
    """Get complete snapshot data including skills and activities."""
    try:
        ensure_database_ready()
        db = get_database()

        with db.get_connection() as conn:
            # Get snapshot metadata
            snapshot = conn.execute("""
                SELECT s.*, a.name as account_name
                FROM snapshots s
                JOIN accounts a ON s.account_id = a.id
                WHERE s.snapshot_id = ?
            """, (snapshot_id,)).fetchone()

            if not snapshot:
                return None

            snapshot_dict = dict(snapshot)

            # Get skills
            skills = conn.execute("""
                SELECT name, level, xp, rank
                FROM skills
                WHERE snapshot_id = (SELECT id FROM snapshots WHERE snapshot_id = ?)
                ORDER BY skill_id
            """, (snapshot_id,)).fetchall()

            snapshot_dict["skills"] = [dict(skill) for skill in skills]

            # Get activities
            activities = conn.execute("""
                SELECT name, score, rank
                FROM activities
                WHERE snapshot_id = (SELECT id FROM snapshots WHERE snapshot_id = ?)
                ORDER BY activity_id
            """, (snapshot_id,)).fetchall()

            snapshot_dict["activities"] = [dict(activity) for activity in activities]

            return snapshot_dict

    except Exception as e:
        logger.error(f"Failed to get snapshot data for {snapshot_id}: {e}")
        return None


def search_accounts(query: str, limit: int = 10) -> list[Dict[str, Any]]:
    """Search for accounts by name."""
    try:
        ensure_database_ready()
        db = get_database()

        with db.get_connection() as conn:
            accounts = conn.execute("""
                SELECT id, name, display_name, default_mode, created_at, updated_at, active
                FROM accounts
                WHERE name LIKE ? OR display_name LIKE ?
                ORDER BY name
                LIMIT ?
            """, (f"%{query}%", f"%{query}%", limit)).fetchall()

            return [dict(account) for account in accounts]

    except Exception as e:
        logger.error(f"Failed to search accounts: {e}")
        return []


def get_database_stats() -> Dict[str, Any]:
    """Get database statistics."""
    try:
        ensure_database_ready()
        db = get_database()

        with db.get_connection() as conn:
            stats = {}

            # Basic counts
            stats["accounts_count"] = conn.execute("SELECT COUNT(*) as count FROM accounts").fetchone()["count"]
            stats["snapshots_count"] = conn.execute("SELECT COUNT(*) as count FROM snapshots").fetchone()["count"]
            stats["skills_count"] = conn.execute("SELECT COUNT(*) as count FROM skills").fetchone()["count"]
            stats["activities_count"] = conn.execute("SELECT COUNT(*) as count FROM activities").fetchone()["count"]

            # Latest activity
            latest = conn.execute("""
                SELECT a.name, s.fetched_at
                FROM snapshots s
                JOIN accounts a ON s.account_id = a.id
                ORDER BY s.fetched_at DESC
                LIMIT 1
            """).fetchone()

            stats["latest_activity"] = dict(latest) if latest else None

            # Schema version
            version = conn.execute("SELECT version FROM schema_version ORDER BY id DESC LIMIT 1").fetchone()
            stats["schema_version"] = version["version"] if version else "unknown"

            return stats

    except Exception as e:
        logger.error(f"Failed to get database stats: {e}")
        return {"error": str(e)}


# Convenience function for backward compatibility
def is_database_enabled() -> bool:
    """Check if database functionality is enabled and working."""
    try:
        stats = get_database_stats()
        return "error" not in stats and stats.get("accounts_count", 0) >= 0
    except:
        return False