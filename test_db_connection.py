#!/usr/bin/env python3
"""Test database connection approach directly."""

import sqlite3
from pathlib import Path

def test_connection():
    """Test creating database connections directly."""
    db_path = Path("data/analytics.db")
    db_path.parent.mkdir(parents=True, exist_ok=True)

    print("Testing direct SQLite connection...")

    # Test 1: Direct connection
    try:
        conn = sqlite3.connect(
            db_path,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
        )
        conn.row_factory = sqlite3.Row

        # Simple query
        result = conn.execute("SELECT COUNT(*) as count FROM accounts").fetchone()
        print(f"✅ Direct connection works: {result['count']} accounts")

        conn.close()
    except Exception as e:
        print(f"❌ Direct connection failed: {e}")

    # Test 2: FastAPI-style dependency
    def get_database_connection():
        """Simulate FastAPI dependency."""
        try:
            conn = sqlite3.connect(
                db_path,
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
            )
            conn.execute("PRAGMA foreign_keys = ON")
            conn.row_factory = sqlite3.Row
            return conn
        except Exception as e:
            print(f"❌ Dependency failed: {e}")
            raise

    try:
        conn = get_database_connection()
        result = conn.execute("SELECT name, id FROM accounts LIMIT 3").fetchall()
        print(f"✅ Dependency connection works: {len(result)} accounts fetched")
        for row in result:
            print(f"   - {row['name']} (ID: {row['id']})")
        conn.close()
    except Exception as e:
        print(f"❌ Dependency usage failed: {e}")

    # Test 3: Simulate multiple connections (like FastAPI)
    print("\nTesting multiple connections (FastAPI simulation)...")
    for i in range(3):
        try:
            conn = get_database_connection()
            result = conn.execute("SELECT COUNT(*) as count FROM snapshots").fetchone()
            print(f"   Connection {i+1}: {result['count']} snapshots")
            conn.close()
        except Exception as e:
            print(f"❌ Connection {i+1} failed: {e}")

if __name__ == "__main__":
    test_connection()