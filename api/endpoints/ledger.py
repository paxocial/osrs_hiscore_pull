from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status

from api.dependencies import get_database_connection, require_plugin_ingest_key
from api.schemas.ledger import (
    CatherbyEventBatch,
    CatherbyEventEnvelope,
    ExportEligibility,
    LedgerIngestResponse,
)

router = APIRouter()

EVENT_PAYLOAD_CAP_BYTES = 65536
REQUESTS_PER_MINUTE_PER_KEY_IP = 60


def _canonical_json_hash(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _current_window() -> str:
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M")


def _record_rate_limit(conn: sqlite3.Connection, token_id: int, source_ip: str, endpoint: str) -> None:
    window = _current_window()
    conn.execute(
        """
        INSERT INTO ledger_rate_limit_records (token_id, source_ip, endpoint, window_start, request_count)
        VALUES (?, ?, ?, ?, 1)
        ON CONFLICT(token_id, source_ip, endpoint, window_start)
        DO UPDATE SET request_count = request_count + 1, updated_at = CURRENT_TIMESTAMP
        """,
        (token_id, source_ip, endpoint, window),
    )
    row = conn.execute(
        """
        SELECT request_count FROM ledger_rate_limit_records
        WHERE token_id = ? AND source_ip = ? AND endpoint = ? AND window_start = ?
        """,
        (token_id, source_ip, endpoint, window),
    ).fetchone()
    if row and int(row[0]) > REQUESTS_PER_MINUTE_PER_KEY_IP:
        raise HTTPException(status_code=429, detail="Ledger ingest rate limit exceeded")


def _get_intake_state(conn: sqlite3.Connection) -> dict:
    row = conn.execute(
        "SELECT enabled, status_only, degraded, reason, updated_at FROM intake_control WHERE scope = 'global'"
    ).fetchone()
    if not row:
        return {"enabled": True, "status_only": False, "degraded": False, "reason": "default", "updated_at": None}
    return {
        "enabled": bool(row[0]),
        "status_only": bool(row[1]),
        "degraded": bool(row[2]),
        "reason": row[3],
        "updated_at": row[4],
    }


def _record_validation_error(conn: sqlite3.Connection, envelope: CatherbyEventEnvelope, code: str, payload_hash: str, detail: str) -> None:
    conn.execute(
        """
        INSERT INTO event_validation_errors (event_id, idempotency_key, error_code, detail, payload_hash, export_eligibility)
        VALUES (NULL, ?, ?, ?, ?, ?)
        """,
        (envelope.idempotency_key, code, detail, payload_hash, ExportEligibility.BLOCKED.value),
    )


def _record_quarantine(
    conn: sqlite3.Connection,
    envelope: CatherbyEventEnvelope,
    payload_hash: str,
    reason_code: str,
    source_ip: str,
    token_id: int,
) -> None:
    summary = json.dumps({"event_family": envelope.event_family.value}, sort_keys=True)
    conn.execute(
        """
        INSERT INTO quarantine_records (
            event_id, idempotency_key, payload_hash, reason_code, payload_summary,
            source_domain, source_adapter, token_id, source_ip, review_state, export_eligibility
        ) VALUES (NULL, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)
        """,
        (
            envelope.idempotency_key,
            payload_hash,
            reason_code,
            summary,
            envelope.source_domain,
            envelope.source_adapter,
            token_id,
            source_ip,
            ExportEligibility.BLOCKED.value,
        ),
    )


def _insert_accepted_event(
    conn: sqlite3.Connection,
    envelope: CatherbyEventEnvelope,
    payload_hash: str,
    source_ip: str,
    user_agent: str,
    token: dict,
) -> str:
    event_id = str(uuid4())
    received_at = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """
        INSERT INTO ingested_events (
            event_id, source_event_id, idempotency_key, payload_hash, schema_version,
            source_domain, source_adapter, event_family, player_ref, session_id,
            plugin_version, privacy_class, export_eligibility, validation_status,
            reason_code, token_id, token_user_id, source_ip, user_agent,
            observed_at, received_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, ?, ?, ?)
        """,
        (
            event_id,
            envelope.source_event_id,
            envelope.idempotency_key,
            payload_hash,
            envelope.schema_version,
            envelope.source_domain,
            envelope.source_adapter,
            envelope.event_family.value,
            envelope.player_ref,
            envelope.session_id,
            envelope.plugin_version,
            envelope.privacy_class.value,
            envelope.export_eligibility.value,
            "accepted",
            token["id"],
            token["user_id"],
            source_ip,
            user_agent,
            envelope.observed_at.isoformat(),
            received_at,
        ),
    )
    conn.execute(
        "INSERT INTO event_payloads (event_id, payload_json) VALUES (?, ?)",
        (event_id, json.dumps(envelope.payload, sort_keys=True, separators=(",", ":"))),
    )
    for ref in envelope.source_refs:
        conn.execute(
            "INSERT INTO event_source_refs (event_id, ref_type, ref_value) VALUES (?, ?, ?)",
            (event_id, ref.ref_type, ref.ref_value),
        )
    return event_id


@router.post("/events", response_model=LedgerIngestResponse)
async def ingest_event(
    envelope: CatherbyEventEnvelope,
    request: Request,
    token: dict = Depends(require_plugin_ingest_key),
    conn: sqlite3.Connection = Depends(get_database_connection),
) -> LedgerIngestResponse:
    source_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    _record_rate_limit(conn, int(token["id"]), source_ip, "events")

    intake = _get_intake_state(conn)
    if not intake["enabled"] or intake["status_only"]:
        raise HTTPException(status_code=503, detail="Ledger intake currently unavailable")

    serialized = json.dumps(envelope.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    if len(serialized.encode("utf-8")) > EVENT_PAYLOAD_CAP_BYTES:
        payload_hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        _record_validation_error(conn, envelope, "payload_too_large", payload_hash, "single event exceeds byte cap")
        _record_quarantine(conn, envelope, payload_hash, "payload_too_large", source_ip, int(token["id"]))
        conn.commit()
        raise HTTPException(status_code=413, detail="Event payload too large")

    payload_hash = _canonical_json_hash(envelope.payload)
    existing = conn.execute(
        "SELECT event_id, payload_hash FROM ingested_events WHERE idempotency_key = ?",
        (envelope.idempotency_key,),
    ).fetchone()

    if existing:
        if existing[1] == payload_hash:
            return LedgerIngestResponse(
                status="duplicate",
                event_id=existing[0],
                idempotency_key=envelope.idempotency_key,
                payload_hash=payload_hash,
                validation_status="accepted",
            )
        _record_validation_error(conn, envelope, "idempotency_conflict", payload_hash, "same key with different payload hash")
        _record_quarantine(conn, envelope, payload_hash, "idempotency_conflict", source_ip, int(token["id"]))
        conn.commit()
        raise HTTPException(status_code=409, detail="Idempotency conflict")

    event_id = _insert_accepted_event(conn, envelope, payload_hash, source_ip, user_agent, token)
    return LedgerIngestResponse(
        status="accepted",
        event_id=event_id,
        idempotency_key=envelope.idempotency_key,
        payload_hash=payload_hash,
        validation_status="accepted",
    )


@router.post("/events/batch")
async def ingest_batch(
    batch: CatherbyEventBatch,
    request: Request,
    token: dict = Depends(require_plugin_ingest_key),
    conn: sqlite3.Connection = Depends(get_database_connection),
) -> dict:
    source_ip = request.client.host if request.client else "unknown"
    _record_rate_limit(conn, int(token["id"]), source_ip, "events_batch")

    intake = _get_intake_state(conn)
    if not intake["enabled"] or intake["status_only"]:
        raise HTTPException(status_code=503, detail="Ledger intake currently unavailable")

    accepted = duplicates = conflicts = rejected = 0
    results: list[LedgerIngestResponse] = []
    for envelope in batch.events:
        try:
            result = await ingest_event(envelope=envelope, request=request, token=token, conn=conn)
            if result.status == "accepted":
                accepted += 1
            else:
                duplicates += 1
            results.append(result)
        except HTTPException as exc:
            if exc.status_code == 409:
                conflicts += 1
            else:
                rejected += 1

    batch_id = str(uuid4())
    payload_bytes = len(json.dumps(batch.model_dump(mode="json"), sort_keys=True, separators=(",", ":")).encode("utf-8"))
    conn.execute(
        """
        INSERT INTO event_batches (batch_id, total_events, accepted_count, duplicate_count, conflict_count, rejected_count, total_payload_bytes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (batch_id, len(batch.events), accepted, duplicates, conflicts, rejected, payload_bytes),
    )

    return {
        "batch_id": batch_id,
        "total_events": len(batch.events),
        "accepted": accepted,
        "duplicates": duplicates,
        "conflicts": conflicts,
        "rejected": rejected,
        "results": [item.model_dump() for item in results],
    }


@router.get("/status")
async def ledger_status(
    token: dict = Depends(require_plugin_ingest_key),
    conn: sqlite3.Connection = Depends(get_database_connection),
) -> dict:
    del token
    intake = _get_intake_state(conn)
    return {
        "intake": intake,
        "service": "catherby-ledger",
    }
