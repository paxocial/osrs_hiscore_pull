from __future__ import annotations

import hashlib
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from api import dependencies
from api.main import app
from database.connection import DatabaseConnection


def _seed_token(conn, token_value: str, scopes: str = "plugin:ingest") -> None:
    conn.execute("INSERT INTO users (email, password_hash) VALUES (?, ?)", ("o@example.com", "x"))
    token_hash = hashlib.sha256(token_value.encode("utf-8")).hexdigest()
    conn.execute(
        "INSERT INTO api_tokens (user_id, token_hash, scopes, label) VALUES (1, ?, ?, 'obs')",
        (token_hash, scopes),
    )
    conn.commit()


@pytest.fixture
def client(tmp_path: Path):
    db = DatabaseConnection(db_path=tmp_path / "test.db", reuse_connection=False, check_same_thread=False)
    db.initialize_database()
    dependencies._shared_db = db
    with db.get_connection() as conn:
        _seed_token(conn, "good-token")
    with TestClient(app) as c:
        yield c, db


def _headers(token: str = "good-token"):
    return {"X-API-Key": token}


def _event(idem: str, export_eligibility: str):
    return {
        "schema_version": "1",
        "source_event_id": f"src-{idem}",
        "idempotency_key": idem,
        "observed_at": "2026-05-15T07:00:00Z",
        "source_domain": "runelite",
        "source_adapter": "plugin",
        "event_family": "session",
        "player_ref": "p1",
        "session_id": "s1",
        "plugin_version": "1.0.0",
        "privacy_class": "public_safe",
        "export_eligibility": export_eligibility,
        "payload": {"event": "login", "world": 301},
        "source_refs": [{"ref_type": "client", "ref_value": "abc"}],
    }


def test_observations_include_lineage_fields(client):
    c, _ = client
    ingest = c.post("/api/v1/ledger/osrs/events", json=_event("idem-obs-0001", "exportable"), headers=_headers())
    assert ingest.status_code == 200
    event_id = ingest.json()["event_id"]
    payload_hash = ingest.json()["payload_hash"]

    response = c.get("/api/v1/ledger/osrs/observations", headers=_headers())
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    observation = data[0]
    assert observation["event_ids"] == [event_id]
    assert observation["payload_hashes"] == [payload_hash]
    assert observation["source_refs"] == [{"ref_type": "client", "ref_value": "abc"}]
    assert observation["export_eligibility"] == "exportable"
    assert observation["privacy_class"] == "public_safe"
    assert "payload" not in observation


def test_observations_exclude_non_exportable_and_quarantined(client):
    c, db = client
    exportable = c.post("/api/v1/ledger/osrs/events", json=_event("idem-obs-0002", "exportable"), headers=_headers())
    blocked = c.post("/api/v1/ledger/osrs/events", json=_event("idem-obs-0003", "blocked"), headers=_headers())
    assert exportable.status_code == 200
    assert blocked.status_code == 200

    exportable_event_id = exportable.json()["event_id"]
    with db.get_connection() as conn:
        conn.execute(
            """
            INSERT INTO quarantine_records (event_id, idempotency_key, payload_hash, reason_code, export_eligibility)
            VALUES (?, ?, ?, 'manual_review', 'blocked')
            """,
            (exportable_event_id, "idem-obs-0002", exportable.json()["payload_hash"]),
        )
        conn.commit()

    response = c.get("/api/v1/ledger/osrs/observations", headers=_headers())
    assert response.status_code == 200
    assert response.json() == []
