#!/usr/bin/env python3
"""Database setup script for OSRS Hiscore Analytics."""

import argparse
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.connection import DatabaseConnection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def setup_database(db_path: str, force: bool = False) -> None:
    """Initialize the database."""
    db_path_obj = Path(db_path)

    if db_path_obj.exists() and not force:
        print(f"Database already exists at {db_path}")
        response = input("Do you want to re-initialize it? This will delete all data. (y/N): ")
        if response.lower() != 'y':
            print("Database setup cancelled.")
            return

        # Remove existing database
        db_path_obj.unlink()
        print(f"Removed existing database at {db_path}")

    print(f"Setting up database at {db_path}")

    try:
        db = DatabaseConnection(Path(db_path))
        db.initialize_database()

        # Run health check
        health = db.health_check()
        print("\nDatabase Health Check:")
        print(f"Status: {health['status']}")
        print(f"Schema Version: {health.get('schema_version', 'Unknown')}")
        print(f"Accounts: {health.get('accounts_count', 0)}")
        print(f"Snapshots: {health.get('snapshots_count', 0)}")

        if health["issues"]:
            print("Issues:")
            for issue in health["issues"]:
                print(f"  - {issue}")

        if health["status"] == "healthy":
            print("\n✅ Database setup completed successfully!")
        else:
            print(f"\n❌ Database setup completed with issues: {health['status']}")

    except Exception as e:
        logger.error(f"Database setup failed: {e}")
        print(f"❌ Database setup failed: {e}")
        sys.exit(1)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Set up OSRS Hiscore Analytics database")
    parser.add_argument(
        "--db-path",
        default="data/analytics.db",
        help="Path to database file (default: data/analytics.db)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-initialization of existing database"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    setup_database(args.db_path, args.force)


if __name__ == "__main__":
    main()