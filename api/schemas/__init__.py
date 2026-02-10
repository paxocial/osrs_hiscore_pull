"""Pydantic schemas for API validation.

This package contains all Pydantic models used for request/response validation
across the API, including plugin payload schemas.
"""

# Import core models from base module (formerly schemas.py)
from api.schemas.base import (
    # Account models
    AccountBase,
    AccountCreate,
    AccountUpdate,
    Account,
    # Skill models
    SkillBase,
    Skill,
    # Activity models
    ActivityBase,
    Activity,
    # Snapshot models
    SnapshotBase,
    SnapshotCreate,
    Snapshot,
    SnapshotDeltaBase,
    SnapshotDelta,
    # Analytics models
    AnalyticsProgress,
    AnalyticsMilestone,
    AnalyticsComparison,
    # Response models
    AccountListResponse,
    SnapshotListResponse,
    SnapshotDetailResponse,
    AnalyticsProgressResponse,
    AnalyticsMilestonesResponse,
    # Query parameter models
    AccountQueryParams,
    SnapshotQueryParams,
    AnalyticsQueryParams,
    # Error models
    ErrorResponse,
    ValidationErrorResponse,
)

# Import plugin models
from api.schemas.plugin import (
    # Base model
    PluginPayloadBase,
    # Individual payload models
    SessionEvent,
    XpSnapshot,
    CollectionLogEntry,
    QuestStatus,
    DiaryProgress,
    CombatAchievementProgress,
    EquipmentState,
    LootDrop,
    ActivityUpdate,
    BankSnapshot,
    # Batch and response models
    BatchPayload,
    StatusResponse,
)

__all__ = [
    # Account models
    "AccountBase",
    "AccountCreate",
    "AccountUpdate",
    "Account",
    # Skill models
    "SkillBase",
    "Skill",
    # Activity models
    "ActivityBase",
    "Activity",
    # Snapshot models
    "SnapshotBase",
    "SnapshotCreate",
    "Snapshot",
    "SnapshotDeltaBase",
    "SnapshotDelta",
    # Analytics models
    "AnalyticsProgress",
    "AnalyticsMilestone",
    "AnalyticsComparison",
    # Response models
    "AccountListResponse",
    "SnapshotListResponse",
    "SnapshotDetailResponse",
    "AnalyticsProgressResponse",
    "AnalyticsMilestonesResponse",
    # Query parameter models
    "AccountQueryParams",
    "SnapshotQueryParams",
    "AnalyticsQueryParams",
    # Error models
    "ErrorResponse",
    "ValidationErrorResponse",
    # Plugin models - Base
    "PluginPayloadBase",
    # Plugin models - Individual payloads
    "SessionEvent",
    "XpSnapshot",
    "CollectionLogEntry",
    "QuestStatus",
    "DiaryProgress",
    "CombatAchievementProgress",
    "EquipmentState",
    "LootDrop",
    "ActivityUpdate",
    "BankSnapshot",
    # Plugin models - Batch and response
    "BatchPayload",
    "StatusResponse",
]
