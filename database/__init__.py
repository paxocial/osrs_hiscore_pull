"""Database package for OSRS Hiscore Analytics."""

from .connection import DatabaseConnection

# TODO: Fix SQLAlchemy models import issue
# from .models import (
#     Account,
#     Snapshot,
#     Skill,
#     Activity,
#     SnapshotDelta,
#     ModeCache,
#     SchemaVersion,
# )

__all__ = [
    "DatabaseConnection",
    # "Account",
    # "Snapshot",
    # "Skill",
    # "Activity",
    # "SnapshotDelta",
    # "ModeCache",
    # "SchemaVersion",
]

__version__ = "1.0.0"