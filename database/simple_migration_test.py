#!/usr/bin/env python3
"""Simple migration test with minimal database setup."""

import sys
import json
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_simple_migration():
    """Test migration with simple approach."""
    print("🧪 Testing Simple Migration")
    print("=" * 30)

    import sqlite3

    # Create simple database
    db_path = Path("simple_test.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Create basic tables without triggers or complex features
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            default_mode TEXT DEFAULT 'main',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            active BOOLEAN DEFAULT TRUE,
            metadata TEXT DEFAULT '{}'
        );

        CREATE TABLE IF NOT EXISTS snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER NOT NULL,
            snapshot_id TEXT UNIQUE NOT NULL,
            requested_mode TEXT NOT NULL,
            resolved_mode TEXT NOT NULL,
            fetched_at TIMESTAMP NOT NULL,
            endpoint TEXT,
            latency_ms REAL,
            agent_version TEXT,
            total_level INTEGER,
            total_xp INTEGER,
            metadata TEXT DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS skills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_id INTEGER NOT NULL,
            skill_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            level INTEGER,
            xp INTEGER,
            rank INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (snapshot_id) REFERENCES snapshots(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_id INTEGER NOT NULL,
            activity_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            score INTEGER,
            rank INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (snapshot_id) REFERENCES snapshots(id) ON DELETE CASCADE
        );
    """)

    # Read first JSON file
    json_file = Path("data/snapshots/ArchonBorn/20251027_150009.json")
    if not json_file.exists():
        print("❌ Test JSON file not found")
        return False

    with open(json_file, 'r') as f:
        snapshot_data = json.load(f)

    print("✅ JSON loaded successfully")
    metadata = snapshot_data["metadata"]
    print(f"Player: {metadata['player']}")
    print(f"Mode: {metadata.get('resolved_mode', metadata.get('mode'))}")

    # Create account
    cursor = conn.execute(
        "INSERT OR IGNORE INTO accounts (name, default_mode, metadata) VALUES (?, ?, ?)",
        (metadata["player"], metadata.get("resolved_mode", metadata.get("mode")), json.dumps(metadata))
    )
    account_id = cursor.lastrowid or conn.execute("SELECT id FROM accounts WHERE name = ?", (metadata["player"],)).fetchone()["id"]
    print(f"✅ Account created/updated: {account_id}")

    # Calculate totals
    skills = snapshot_data.get("data", {}).get("skills", [])
    total_xp = sum(skill.get("xp", 0) for skill in skills)
    total_level = sum(skill.get("level", 0) for skill in skills if skill.get("name") != "Overall")

    # Generate snapshot ID
    from uuid import NAMESPACE_URL, uuid5
    snapshot_id = metadata.get("snapshot_id", str(uuid5(NAMESPACE_URL, f"osrs:{metadata['player']}:{json_file.name}")))

    # Create snapshot
    cursor = conn.execute(
        """INSERT INTO snapshots
           (account_id, snapshot_id, requested_mode, resolved_mode, fetched_at, endpoint,
            latency_ms, agent_version, total_level, total_xp, metadata)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            account_id,
            snapshot_id,
            metadata.get("requested_mode", metadata.get("resolved_mode", metadata.get("mode"))),
            metadata.get("resolved_mode", metadata.get("mode")),
            metadata["fetched_at"].replace("Z", "+00:00"),
            metadata.get("endpoint"),
            metadata.get("latency_ms"),
            metadata.get("agent_version"),
            total_level,
            total_xp,
            json.dumps(metadata)
        )
    )
    snapshot_db_id = cursor.lastrowid
    print(f"✅ Snapshot created: {snapshot_db_id}")

    # Add skills
    skills_count = 0
    for skill in skills[:5]:  # Just first 5 skills for testing
        conn.execute(
            "INSERT INTO skills (snapshot_id, skill_id, name, level, xp, rank) VALUES (?, ?, ?, ?, ?, ?)",
            (snapshot_db_id, skill["id"], skill["name"], skill.get("level"), skill.get("xp"), skill.get("rank"))
        )
        skills_count += 1
    print(f"✅ Added {skills_count} skills")

    # Test query
    result = conn.execute("""
        SELECT a.name, s.snapshot_id, s.total_level, s.total_xp
        FROM accounts a
        JOIN snapshots s ON a.id = s.account_id
        WHERE a.name = ?
    """, (metadata["player"],)).fetchone()

    if result:
        print(f"✅ Query successful: {result['name']} - Level {result['total_level']}, XP {result['total_xp']:,}")
    else:
        print("❌ Query failed")

    conn.close()
    db_path.unlink()
    print("🧹 Test completed and cleaned up")
    return True

if __name__ == "__main__":
    success = test_simple_migration()
    sys.exit(0 if success else 1)