#!/usr/bin/env python3
"""Debug migration script to identify issues."""

import sys
import json
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.migrations import JSONMigrationManager

def debug_migration():
    """Debug the migration process."""
    print("🔍 Debug Migration Process")
    print("=" * 30)

    migration_manager = JSONMigrationManager()
    migration_manager.ensure_database_ready()

    # Get account snapshots
    account_snapshots = migration_manager.scan_for_snapshots()
    print(f"Found accounts: {list(account_snapshots.keys())}")

    # Test with first file
    if account_snapshots and "ArchonBorn" in account_snapshots:
        account_files = account_snapshots["ArchonBorn"]
        if account_files:
            first_file = account_files[0]
            print(f"\nTesting file: {first_file}")

            # Parse file
            snapshot_data = migration_manager.parse_snapshot_file(first_file)
            if snapshot_data:
                print("✅ JSON parsed successfully")
                print(f"Keys: {list(snapshot_data.keys())}")

                metadata = snapshot_data.get("metadata", {})
                print(f"Metadata keys: {list(metadata.keys())}")
                print(f"Has snapshot_id: {'snapshot_id' in metadata}")

                if "snapshot_id" in metadata:
                    print(f"Snapshot ID: {metadata['snapshot_id']}")

                    # Try migration
                    try:
                        success = migration_manager.migrate_snapshot(snapshot_data, check_existing=False)
                        print(f"Migration result: {success}")
                    except Exception as e:
                        print(f"Migration error: {e}")
                        import traceback
                        traceback.print_exc()
                else:
                    print("❌ No snapshot_id in metadata")
            else:
                print("❌ Failed to parse JSON")

if __name__ == "__main__":
    debug_migration()