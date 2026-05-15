from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from api.schemas.ledger import (
    CatherbyEventBatch,
    CatherbyEventEnvelope,
    EventFamily,
    ExportEligibility,
    PrivacyClass,
)


def _valid_envelope(**overrides):
    base = {
        "schema_version": "1",
        "source_event_id": "src-1",
        "idempotency_key": "idem-12345678",
        "observed_at": datetime.now(timezone.utc),
        "source_domain": "runelite",
        "source_adapter": "plugin",
        "event_family": EventFamily.SESSION,
        "player_ref": "player",
        "session_id": "sess-1",
        "plugin_version": "1.0.0",
        "privacy_class": PrivacyClass.OPERATOR_PRIVATE,
        "export_eligibility": ExportEligibility.BLOCKED,
        "payload": {"event": "login", "world": 301},
        "source_refs": [{"ref_type": "client", "ref_value": "abc"}],
    }
    base.update(overrides)
    return CatherbyEventEnvelope(**base)


def test_required_fields():
    with pytest.raises(ValidationError):
        CatherbyEventEnvelope()


def test_session_and_xp_allowed():
    assert _valid_envelope(event_family=EventFamily.SESSION)
    assert _valid_envelope(event_family=EventFamily.XP, payload={"skills": {"attack": 1000}})


def test_unsupported_family_rejected():
    with pytest.raises(ValidationError):
        _valid_envelope(event_family="bank")


def test_payload_caps_batch():
    events = [_valid_envelope(idempotency_key=f"idem-{i:08d}") for i in range(51)]
    with pytest.raises(ValidationError):
        CatherbyEventBatch(events=events)


def test_timestamp_skew_rejected():
    with pytest.raises(ValidationError):
        _valid_envelope(observed_at=datetime.now(timezone.utc) - timedelta(days=2))


def test_privacy_export_enums():
    event = _valid_envelope(
        privacy_class=PrivacyClass.PUBLIC_SAFE,
        export_eligibility=ExportEligibility.SCRUB_REQUIRED,
    )
    assert event.privacy_class == PrivacyClass.PUBLIC_SAFE
    assert event.export_eligibility == ExportEligibility.SCRUB_REQUIRED


def test_source_refs():
    event = _valid_envelope(source_refs=[{"ref_type": "hash", "ref_value": "deadbeef"}])
    assert event.source_refs[0].ref_type == "hash"
