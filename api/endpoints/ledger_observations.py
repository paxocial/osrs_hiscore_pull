from __future__ import annotations

import sqlite3
from datetime import datetime

from fastapi import APIRouter, Depends

from api.dependencies import get_database_connection, require_plugin_ingest_key
from api.schemas.ledger import AdvisoryObservation, ExportEligibility, PrivacyClass, SourceRef

router = APIRouter()


@router.get("/observations", response_model=list[AdvisoryObservation])
async def list_observations(
    token: dict = Depends(require_plugin_ingest_key),
    conn: sqlite3.Connection = Depends(get_database_connection),
) -> list[AdvisoryObservation]:
    del token
    rows = conn.execute(
        """
        SELECT
            event_id,
            payload_hash,
            privacy_class,
            export_eligibility,
            event_family,
            source_domain,
            source_adapter,
            player_ref,
            created_at
        FROM v_ledger_exportable_observations
        ORDER BY created_at DESC, event_id DESC
        """
    ).fetchall()

    observations: list[AdvisoryObservation] = []
    for row in rows:
        refs_rows = conn.execute(
            "SELECT ref_type, ref_value FROM event_source_refs WHERE event_id = ? ORDER BY id ASC",
            (row["event_id"],),
        ).fetchall()
        source_refs = [SourceRef(ref_type=ref["ref_type"], ref_value=ref["ref_value"]) for ref in refs_rows]
        summary = (
            f"{row['event_family']} advisory for {row['player_ref']} "
            f"from {row['source_domain']}/{row['source_adapter']}"
        )
        created_at = row["created_at"]
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        observations.append(
            AdvisoryObservation(
                observation_id=f"obs-{row['event_id']}",
                event_ids=[row["event_id"]],
                source_refs=source_refs,
                payload_hashes=[row["payload_hash"]],
                privacy_class=PrivacyClass(row["privacy_class"]),
                export_eligibility=ExportEligibility(row["export_eligibility"]),
                summary=summary,
                created_at=created_at,
            )
        )
    return observations
