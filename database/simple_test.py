#!/usr/bin/env python3
"""Simple database test without SQLAlchemy models."""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.connection import DatabaseConnection

def test_database():
    """Test database connection and schema setup."""
    print("Testing database setup...")

    # Use temporary database
    db_path = Path("temp_simple_test.db")

    try:
        db = DatabaseConnection(db_path)
        print("✅ Database connection created")

        # Initialize database
        db.initialize_database()
        print("✅ Database schema initialized")

        # Health check
        health = db.health_check()
        print(f"\n📊 Database Health:")
        print(f"   Status: {health['status']}")
        print(f"   Schema Version: {health.get('schema_version', 'Unknown')}")
        print(f"   Accounts: {health.get('accounts_count', 0)}")
        print(f"   Snapshots: {health.get('snapshots_count', 0)}")

        if health["issues"]:
            print(f"   Issues: {health['issues']}")

        # Test basic query
        with db.get_connection() as conn:
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ).fetchall()

            print(f"\n📋 Tables created:")
            for table in tables:
                print(f"   - {table['name']}")

        print("\n✅ Database test completed successfully!")
        return True

    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

    finally:
        # Cleanup
        if db_path.exists():
            db_path.unlink()
            print("🧹 Test database cleaned up")

if __name__ == "__main__":
    success = test_database()
    sys.exit(0 if success else 1)