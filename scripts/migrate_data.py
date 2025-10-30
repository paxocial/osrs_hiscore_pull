#!/usr/bin/env python3
"""Migration script for JSON snapshots to database."""

import argparse
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.migrations import JSONMigrationManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def run_migration(force: bool = False, verbose: bool = False) -> None:
    """Run the migration process."""
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    print("🚀 Starting JSON to Database Migration")
    print("=" * 50)

    migration_manager = JSONMigrationManager()

    try:
        # Run migration
        stats = migration_manager.run_migration(force=force)

        # Print summary
        migration_manager.print_migration_summary(stats)

        # Print detailed log if verbose
        if verbose:
            print("\nDETAILED LOG:")
            print("-" * 30)
            for log_entry in migration_manager.get_migration_log():
                print(f"  {log_entry}")

        return stats["migrated"] > 0

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        print(f"\n❌ Migration failed: {e}")
        return False


def check_status() -> None:
    """Check current migration status."""
    print("📊 Checking Migration Status")
    print("=" * 30)

    try:
        migration_manager = JSONMigrationManager()
        migration_manager.ensure_database_ready()

        # Scan for JSON files
        account_snapshots = migration_manager.scan_for_snapshots()
        total_json_files = sum(len(files) for files in account_snapshots.values())

        # Get database counts
        status = get_migration_status()

        print(f"JSON files on disk: {total_json_files}")
        print(f"Accounts in database: {status['accounts_count']}")
        print(f"Snapshots in database: {status['snapshots_count']}")
        print(f"Database ready: {status['database_ready']}")

        if status['latest_snapshot']:
            print(f"Latest snapshot: {status['latest_snapshot']}")

        # Account breakdown
        if account_snapshots:
            print(f"\n📋 Account breakdown:")
            for account_name, files in account_snapshots.items():
                print(f"  {account_name}: {len(files)} files")

    except Exception as e:
        print(f"❌ Status check failed: {e}")


def get_migration_status() -> dict:
    """Get migration status."""
    from database.migrations import get_migration_status as get_status
    return get_status()


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Migrate JSON snapshots to database")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-migration of all snapshots (overwrites existing data)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Check migration status only"
    )

    args = parser.parse_args()

    if args.status:
        check_status()
    else:
        success = run_migration(force=args.force, verbose=args.verbose)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()