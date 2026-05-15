from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class EventFamily(str, Enum):
    SESSION = "session"
    XP = "xp"


class PrivacyClass(str, Enum):
    OPERATOR_PRIVATE = "operator_private"
    DERIVED_INTERNAL = "derived_internal"
    PUBLIC_SAFE = "public_safe"
    DUNGEON_CRAWL_EXPORTABLE = "dungeon_crawl_exportable"


class ExportEligibility(str, Enum):
    BLOCKED = "blocked"
    SCRUB_REQUIRED = "scrub_required"
    EXPORTABLE = "exportable"


class SourceRef(BaseModel):
    ref_type: str = Field(min_length=1, max_length=64)
    ref_value: str = Field(min_length=1, max_length=512)


class CatherbyEventEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = Field(min_length=1, max_length=32)
    source_event_id: str = Field(min_length=1, max_length=128)
    idempotency_key: str = Field(min_length=8, max_length=128)
    observed_at: datetime
    source_domain: str = Field(min_length=1, max_length=64)
    source_adapter: str = Field(min_length=1, max_length=64)
    event_family: EventFamily
    player_ref: str = Field(min_length=1, max_length=64)
    session_id: str = Field(min_length=1, max_length=128)
    plugin_version: str = Field(min_length=1, max_length=32)
    privacy_class: PrivacyClass
    export_eligibility: ExportEligibility
    payload: dict[str, Any]
    source_refs: list[SourceRef] = Field(default_factory=list, max_length=25)

    @field_validator("payload")
    @classmethod
    def _payload_must_be_object(cls, value: dict[str, Any]) -> dict[str, Any]:
        if not value:
            raise ValueError("payload must not be empty")
        return value

    @model_validator(mode="after")
    def _validate_family_payload_and_time(self) -> "CatherbyEventEnvelope":
        if self.event_family == EventFamily.SESSION:
            allowed = {"event", "world", "duration_seconds"}
            required = {"event"}
        else:
            allowed = {"skills", "deltas", "total_level"}
            required = {"skills"}

        missing = required - set(self.payload.keys())
        if missing:
            raise ValueError(f"payload missing required keys for {self.event_family.value}: {sorted(missing)}")

        unknown = set(self.payload.keys()) - allowed
        if unknown:
            raise ValueError(f"payload has unsupported keys for {self.event_family.value}: {sorted(unknown)}")

        observed = self.observed_at
        if observed.tzinfo is None:
            observed = observed.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        skew_seconds = abs((now - observed.astimezone(timezone.utc)).total_seconds())
        if skew_seconds > 86400:
            raise ValueError("observed_at timestamp skew exceeds 24h")

        return self


class CatherbyEventBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    events: list[CatherbyEventEnvelope] = Field(min_length=1, max_length=50)

    @model_validator(mode="after")
    def _enforce_total_payload_cap(self) -> "CatherbyEventBatch":
        payload = self.model_dump(mode="json")
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        if len(serialized.encode("utf-8")) > 262144:
            raise ValueError("batch payload exceeds 262144 bytes")
        return self


class LedgerIngestResponse(BaseModel):
    status: str
    event_id: str | None = None
    idempotency_key: str
    payload_hash: str
    validation_status: str
    reason_code: str | None = None
