"""Pydantic v2 models for OSRS Hiscore Analytics API.

This module defines all data models used in the API, including request/response
schemas, validation, and serialization logic.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional, List, Dict
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from pydantic_core import ValidationError


class AccountBase(BaseModel):
    """Base account model with common fields."""
    name: str = Field(..., min_length=1, max_length=50, description="Account username")
    display_name: Optional[str] = Field(None, max_length=50, description="Display name")
    default_mode: str = Field("main", description="Default game mode")
    active: bool = Field(True, description="Whether account is active")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @field_validator("metadata", mode="before")
    @classmethod
    def parse_metadata(cls, v):
        """Parse metadata from JSON string if needed."""
        if isinstance(v, str):
            try:
                import json
                return json.loads(v)
            except json.JSONDecodeError:
                return {}
        return v or {}

    @field_validator("active", mode="before")
    @classmethod
    def parse_active(cls, v):
        """Parse active field from integer if needed."""
        if isinstance(v, int):
            return v == 1
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate account name format."""
        if not v or not v.strip():
            raise ValueError("Account name cannot be empty")
        return v.strip()

    @field_validator("default_mode")
    @classmethod
    def validate_mode(cls, v: str) -> str:
        """Validate game mode."""
        from core.constants import GAME_MODES
        if v not in GAME_MODES:
            raise ValueError(f"Invalid game mode: {v}")
        return v


class AccountCreate(AccountBase):
    """Model for creating new accounts."""
    pass


class AccountUpdate(BaseModel):
    """Model for updating accounts."""
    display_name: Optional[str] = Field(None, max_length=50)
    default_mode: Optional[str] = None
    active: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None

    @field_validator("default_mode")
    @classmethod
    def validate_mode(cls, v: Optional[str]) -> Optional[str]:
        """Validate game mode if provided."""
        if v is not None:
            from core.constants import GAME_MODES
            if v not in GAME_MODES:
                raise ValueError(f"Invalid game mode: {v}")
        return v


class Account(AccountBase):
    """Complete account model with database fields."""
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Database ID")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    # Optional computed fields
    total_snapshots: Optional[int] = Field(None, description="Total number of snapshots")
    latest_snapshot: Optional[datetime] = Field(None, description="Latest snapshot timestamp")


class SkillBase(BaseModel):
    """Base skill model."""
    id: int = Field(..., ge=0, le=99, description="Skill ID (0-99)")
    name: str = Field(..., min_length=1, max_length=50, description="Skill name")
    level: Optional[int] = Field(None, ge=1, le=99, description="Skill level (1-99)")
    xp: Optional[int] = Field(None, ge=0, description="Skill XP (>= 0)")
    rank: Optional[int] = Field(None, ge=0, description="Hiscore rank (>= 0)")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate skill name."""
        if not v or not v.strip():
            raise ValueError("Skill name cannot be empty")
        return v.strip()

    @field_validator("xp")
    @classmethod
    def validate_xp(cls, v: Optional[int]) -> Optional[int]:
        """Validate XP values."""
        if v is not None and v < 0:
            raise ValueError("XP cannot be negative")
        return v


class Skill(SkillBase):
    """Complete skill model with snapshot relationship."""
    model_config = ConfigDict(from_attributes=True)

    snapshot_id: int = Field(..., description="Parent snapshot ID")


class ActivityBase(BaseModel):
    """Base activity model."""
    id: int = Field(..., ge=0, description="Activity ID")
    name: str = Field(..., min_length=1, max_length=100, description="Activity name")
    score: Optional[int] = Field(None, ge=0, description="Activity score")
    rank: Optional[int] = Field(None, ge=0, description="Hiscore rank")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate activity name."""
        if not v or not v.strip():
            raise ValueError("Activity name cannot be empty")
        return v.strip()


class Activity(ActivityBase):
    """Complete activity model with snapshot relationship."""
    model_config = ConfigDict(from_attributes=True)

    snapshot_id: int = Field(..., description="Parent snapshot ID")


class SnapshotBase(BaseModel):
    """Base snapshot model with common fields."""
    snapshot_id: str = Field(..., min_length=1, description="Unique snapshot identifier")
    requested_mode: str = Field(..., description="Requested game mode")
    resolved_mode: str = Field(..., description="Actually resolved game mode")
    fetched_at: datetime = Field(..., description="When snapshot was fetched")
    endpoint: Optional[str] = Field(None, description="API endpoint used")
    latency_ms: Optional[float] = Field(None, ge=0, description="Request latency in milliseconds")
    agent_version: Optional[str] = Field(None, description="Agent version used")
    total_level: Optional[int] = Field(None, ge=0, description="Total skill level")
    total_xp: Optional[int] = Field(None, ge=0, description="Total skill XP")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @field_validator("metadata", mode="before")
    @classmethod
    def parse_metadata(cls, v):
        """Parse metadata from JSON string if needed."""
        if isinstance(v, str):
            try:
                import json
                return json.loads(v)
            except json.JSONDecodeError:
                return {}
        return v or {}

    @field_validator("requested_mode", "resolved_mode")
    @classmethod
    def validate_mode(cls, v: str) -> str:
        """Validate game modes."""
        from core.constants import GAME_MODES
        if v not in GAME_MODES:
            raise ValueError(f"Invalid game mode: {v}")
        return v

    @field_validator("snapshot_id")
    @classmethod
    def validate_snapshot_id(cls, v: str) -> str:
        """Validate snapshot ID format."""
        if not v or not v.strip():
            raise ValueError("Snapshot ID cannot be empty")
        return v.strip()


class SnapshotCreate(SnapshotBase):
    """Model for creating new snapshots."""
    account_id: int = Field(..., gt=0, description="Account ID")
    skills: List[Skill] = Field(default_factory=list, description="Skill data")
    activities: List[Activity] = Field(default_factory=list, description="Activity data")


class Snapshot(SnapshotBase):
    """Complete snapshot model with database fields."""
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Database ID")
    account_id: int = Field(..., description="Account ID")
    created_at: datetime = Field(..., description="Database creation timestamp")

    # Optional relationships
    skills: Optional[List[Skill]] = Field(None, description="Skill data")
    activities: Optional[List[Activity]] = Field(None, description="Activity data")


class SnapshotDeltaBase(BaseModel):
    """Base snapshot delta model."""
    total_xp_delta: int = Field(..., description="Total XP change")
    time_diff_hours: Optional[float] = Field(None, ge=0, description="Time difference in hours")
    skill_deltas: List[Dict[str, Any]] = Field(default_factory=list, description="Skill changes")
    activity_deltas: List[Dict[str, Any]] = Field(default_factory=list, description="Activity changes")


class SnapshotDelta(SnapshotDeltaBase):
    """Complete snapshot delta model."""
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Database ID")
    current_snapshot_id: int = Field(..., description="Current snapshot ID")
    previous_snapshot_id: Optional[int] = Field(None, description="Previous snapshot ID")
    created_at: datetime = Field(..., description="Creation timestamp")


class AnalyticsProgress(BaseModel):
    """Progress analytics model."""
    account_name: str = Field(..., description="Account name")
    skill_name: str = Field(..., description="Skill name")
    start_date: datetime = Field(..., description="Analysis start date")
    end_date: datetime = Field(..., description="Analysis end date")
    start_level: Optional[int] = Field(None, description="Starting level")
    end_level: Optional[int] = Field(None, description="Ending level")
    start_xp: Optional[int] = Field(None, ge=0, description="Starting XP")
    end_xp: Optional[int] = Field(None, ge=0, description="Ending XP")
    xp_gained: int = Field(0, description="XP gained during period")
    levels_gained: int = Field(0, description="Levels gained during period")
    xp_rate_per_hour: Optional[float] = Field(None, ge=0, description="XP gain rate per hour")


class AnalyticsMilestone(BaseModel):
    """Milestone analytics model."""
    account_name: str = Field(..., description="Account name")
    skill_name: str = Field(..., description="Skill name")
    milestone_level: int = Field(..., ge=1, le=99, description="Milestone level")
    achieved_at: datetime = Field(..., description="When milestone was achieved")
    xp_at_milestone: int = Field(..., ge=0, description="XP at milestone")
    rank_at_milestone: Optional[int] = Field(None, ge=0, description="Rank at milestone")


class AnalyticsComparison(BaseModel):
    """Account comparison analytics model."""
    accounts: List[str] = Field(..., min_items=2, description="Account names to compare")
    comparison_date: datetime = Field(..., description="Date of comparison")
    metrics: Dict[str, Dict[str, Any]] = Field(..., description="Comparison metrics by account")
    leader: str = Field(..., description="Account leading in most metrics")


# Request/Response models
class AccountListResponse(BaseModel):
    """Response model for account list endpoint."""
    accounts: List[Account]
    total: int = Field(..., description="Total number of accounts")
    page: int = Field(1, ge=1, description="Current page number")
    page_size: int = Field(10, ge=1, le=100, description="Items per page")


class SnapshotListResponse(BaseModel):
    """Response model for snapshot list endpoint."""
    snapshots: List[Snapshot]
    total: int = Field(..., description="Total number of snapshots")
    page: int = Field(1, ge=1, description="Current page number")
    page_size: int = Field(10, ge=1, le=100, description="Items per page")
    account_name: Optional[str] = Field(None, description="Filter by account name")


class SnapshotDetailResponse(BaseModel):
    """Response model for detailed snapshot endpoint."""
    snapshot: Snapshot
    deltas: Optional[SnapshotDelta] = Field(None, description="Comparison with previous snapshot")
    account: Account = Field(..., description="Account information")


class AnalyticsProgressResponse(BaseModel):
    """Response model for progress analytics."""
    account_name: str
    skills: List[AnalyticsProgress]
    period_days: int = Field(..., description="Analysis period in days")


class AnalyticsMilestonesResponse(BaseModel):
    """Response model for milestone analytics."""
    account_name: str
    milestones: List[AnalyticsMilestone]
    total_milestones: int = Field(..., description="Total number of milestones")


# Query parameters
class AccountQueryParams(BaseModel):
    """Query parameters for account endpoints."""
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(10, ge=1, le=100, description="Items per page")
    active_only: bool = Field(True, description="Only show active accounts")
    search: Optional[str] = Field(None, min_length=1, description="Search term")


class SnapshotQueryParams(BaseModel):
    """Query parameters for snapshot endpoints."""
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(10, ge=1, le=100, description="Items per page")
    account_name: Optional[str] = Field(None, description="Filter by account name")
    mode: Optional[str] = Field(None, description="Filter by game mode")
    start_date: Optional[datetime] = Field(None, description="Filter start date")
    end_date: Optional[datetime] = Field(None, description="Filter end date")
    include_skills: bool = Field(False, description="Include skill data")
    include_activities: bool = Field(False, description="Include activity data")


class AnalyticsQueryParams(BaseModel):
    """Query parameters for analytics endpoints."""
    account_name: str = Field(..., description="Account name")
    start_date: Optional[datetime] = Field(None, description="Analysis start date")
    end_date: Optional[datetime] = Field(None, description="Analysis end date")
    skills: Optional[List[str]] = Field(None, description="Specific skills to analyze")
    include_deltas: bool = Field(True, description="Include delta calculations")


# Error response models
class ErrorResponse(BaseModel):
    """Standard error response model."""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.now, description="Error timestamp")


class ValidationErrorResponse(BaseModel):
    """Validation error response model."""
    error: str = Field("validation_error", description="Error type")
    message: str = Field("Validation failed", description="General error message")
    validation_errors: List[Dict[str, Any]] = Field(..., description="Field validation errors")
    timestamp: datetime = Field(default_factory=datetime.now, description="Error timestamp")