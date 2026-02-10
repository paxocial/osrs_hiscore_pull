"""Pydantic v2 models for RuneLite plugin API payloads.

This module defines all data models for plugin telemetry ingestion, including
individual payload types, batch submissions, and response schemas.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict


class PluginPayloadBase(BaseModel):
    """Shared base model for all plugin payloads.

    All plugin submissions include these common fields for tracking
    the player context and plugin version.
    """
    rsn: str = Field(
        ...,
        min_length=1,
        max_length=12,
        description="RuneScape display name (1-12 characters)"
    )
    world: Optional[int] = Field(
        None,
        ge=300,
        le=600,
        description="World number (300-600 range)"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Event timestamp (UTC)"
    )
    plugin_version: str = Field(
        ...,
        pattern=r"^\d+\.\d+\.\d+$",
        description="Plugin version (semver format)"
    )

    model_config = ConfigDict(from_attributes=True)


class SessionEventType(str, Enum):
    """Valid session event types."""
    LOGIN = "login"
    LOGOUT = "logout"
    WORLD_HOP = "world_hop"


class SessionEvent(PluginPayloadBase):
    """Player session event (login, logout, world hop).

    Tracks player session lifecycle events with duration tracking.
    """
    session_id: str = Field(
        ...,
        description="Unique session identifier"
    )
    event: SessionEventType = Field(
        ...,
        description="Event type (login/logout/world_hop)"
    )
    duration_seconds: Optional[int] = Field(
        None,
        ge=0,
        description="Session duration in seconds (for logout events)"
    )

    @model_validator(mode='after')
    def validate_world_required(self):
        """World is required for session events."""
        if self.world is None:
            raise ValueError("world is required for session events")
        return self


class XpSnapshot(PluginPayloadBase):
    """Live XP snapshot from client.

    Captures all 23 skill XP values at a specific moment.
    """
    skills: Dict[str, int] = Field(
        ...,
        description="Skill name to XP mapping (all 23 skills required)"
    )

    @field_validator("skills")
    @classmethod
    def validate_skills(cls, v):
        """Ensure all 23 OSRS skills are present with valid XP values."""
        required_skills = [
            "attack", "defence", "strength", "hitpoints", "ranged", "prayer", "magic",
            "cooking", "woodcutting", "fletching", "fishing", "firemaking", "crafting",
            "smithing", "mining", "herblore", "agility", "thieving", "slayer", "farming",
            "runecraft", "hunter", "construction"
        ]

        for skill in required_skills:
            if skill not in v:
                raise ValueError(f"Missing skill: {skill}")
            if not isinstance(v[skill], int) or v[skill] < 0:
                raise ValueError(f"Invalid XP for {skill}: must be non-negative integer")

        return v


class CollectionLogEntry(PluginPayloadBase):
    """Collection log item obtained event.

    Records when a player obtains a collection log item.
    """
    item_id: int = Field(
        ...,
        ge=0,
        description="OSRS item ID"
    )
    item_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Item display name"
    )
    quantity: int = Field(
        ...,
        ge=1,
        description="Quantity obtained"
    )
    source: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Source/boss/activity name"
    )
    obtained_at: datetime = Field(
        ...,
        description="Timestamp when item was obtained"
    )


class QuestState(str, Enum):
    """Valid quest completion states."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"


class QuestStatus(PluginPayloadBase):
    """Quest progress update.

    Tracks quest completion state changes.
    """
    quest_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Quest name"
    )
    state: QuestState = Field(
        ...,
        description="Quest state (not_started/in_progress/complete)"
    )


class DiaryProgress(PluginPayloadBase):
    """Achievement diary progress update.

    Tracks completion status for each diary tier in a region.
    """
    region: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Diary region name (e.g., 'Varrock', 'Lumbridge')"
    )
    easy: bool = Field(
        default=False,
        description="Easy tier completed"
    )
    medium: bool = Field(
        default=False,
        description="Medium tier completed"
    )
    hard: bool = Field(
        default=False,
        description="Hard tier completed"
    )
    elite: bool = Field(
        default=False,
        description="Elite tier completed"
    )


class CombatAchievementProgress(PluginPayloadBase):
    """Combat achievement progress update.

    Tracks tier progress and individual task completions.
    """
    tier_progress: Dict[str, int] = Field(
        ...,
        description="Tier name to completed count mapping (e.g., {'easy': 5, 'medium': 3})"
    )
    completed_tasks: List[str] = Field(
        default_factory=list,
        description="List of completed task names"
    )

    @field_validator("tier_progress")
    @classmethod
    def validate_tier_progress(cls, v):
        """Validate tier progress values are non-negative."""
        valid_tiers = ["easy", "medium", "hard", "elite", "master", "grandmaster"]
        for tier, count in v.items():
            if tier not in valid_tiers:
                raise ValueError(f"Invalid tier: {tier}. Must be one of {valid_tiers}")
            if not isinstance(count, int) or count < 0:
                raise ValueError(f"Invalid count for {tier}: must be non-negative integer")
        return v


class EquipmentState(PluginPayloadBase):
    """Player equipment and inventory snapshot.

    Captures current worn equipment and inventory contents.
    """
    equipment: Dict[str, Any] = Field(
        default_factory=dict,
        description="Equipped items (slot -> item_id mapping)"
    )
    inventory: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Inventory items (list of {item_id, quantity} dicts)"
    )


class LootSourceType(str, Enum):
    """Valid loot source types."""
    NPC = "npc"
    BOSS = "boss"
    CHEST = "chest"
    CLUE = "clue"
    MINIGAME = "minigame"
    OTHER = "other"


class LootDrop(PluginPayloadBase):
    """Loot drop received event.

    Records loot obtained from NPCs, bosses, chests, etc.
    """
    item_id: int = Field(
        ...,
        ge=0,
        description="OSRS item ID"
    )
    item_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Item display name"
    )
    quantity: int = Field(
        ...,
        ge=1,
        description="Quantity dropped"
    )
    ge_value: Optional[int] = Field(
        None,
        ge=0,
        description="Grand Exchange value (coins)"
    )
    source: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Source name (NPC/boss/chest)"
    )
    source_type: LootSourceType = Field(
        ...,
        description="Type of loot source"
    )


class ActivityUpdate(PluginPayloadBase):
    """General activity update event.

    Tracks miscellaneous player activities and achievements.
    """
    activity: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Activity name/type"
    )
    detail: Optional[str] = Field(
        None,
        max_length=500,
        description="Additional activity details"
    )


class BankSnapshot(PluginPayloadBase):
    """Bank contents snapshot.

    Captures complete bank contents with item values.
    """
    items: List[Dict[str, Any]] = Field(
        ...,
        description="List of bank items ({item_id, quantity, value})"
    )
    total_value: int = Field(
        ...,
        ge=0,
        description="Total bank value in coins"
    )

    @field_validator("items")
    @classmethod
    def validate_items(cls, v):
        """Ensure items list contains valid item dictionaries."""
        for item in v:
            if not isinstance(item, dict):
                raise ValueError("Each item must be a dictionary")
            if "item_id" not in item or "quantity" not in item:
                raise ValueError("Each item must have item_id and quantity")
            if not isinstance(item["item_id"], int) or item["item_id"] < 0:
                raise ValueError("item_id must be a non-negative integer")
            if not isinstance(item["quantity"], int) or item["quantity"] < 1:
                raise ValueError("quantity must be a positive integer")
        return v


class BatchPayload(PluginPayloadBase):
    """Batch submission containing multiple payload categories.

    Allows plugins to submit multiple event types in a single request.
    All categories are optional - submit only what changed.
    """
    sessions: Optional[List[SessionEvent]] = Field(
        None,
        description="Session events"
    )
    xp_snapshots: Optional[List[XpSnapshot]] = Field(
        None,
        description="XP snapshots"
    )
    collection_log: Optional[List[CollectionLogEntry]] = Field(
        None,
        description="Collection log entries"
    )
    quests: Optional[List[QuestStatus]] = Field(
        None,
        description="Quest status updates"
    )
    diaries: Optional[List[DiaryProgress]] = Field(
        None,
        description="Diary progress updates"
    )
    combat_achievements: Optional[List[CombatAchievementProgress]] = Field(
        None,
        description="Combat achievement progress"
    )
    equipment: Optional[List[EquipmentState]] = Field(
        None,
        description="Equipment snapshots"
    )
    loot: Optional[List[LootDrop]] = Field(
        None,
        description="Loot drops"
    )
    activity: Optional[List[ActivityUpdate]] = Field(
        None,
        description="Activity updates"
    )
    bank: Optional[List[BankSnapshot]] = Field(
        None,
        description="Bank snapshots"
    )


class StatusResponse(BaseModel):
    """API status response for health checks and authentication verification.

    Returned by the /api/v1/plugin/status endpoint.
    """
    status: str = Field(
        ...,
        description="API status (ok/error)"
    )
    version: str = Field(
        ...,
        description="API version"
    )
    authenticated: bool = Field(
        ...,
        description="Whether request is authenticated"
    )
    user_id: Optional[int] = Field(
        None,
        description="Authenticated user ID (if authenticated)"
    )

    model_config = ConfigDict(from_attributes=True)
