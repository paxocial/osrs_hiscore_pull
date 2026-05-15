from __future__ import annotations

import hashlib
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from api import dependencies
from api.main import app
from database.connection import DatabaseConnection


def _seed_token(conn, token_value: str, scopes: str = "plugin:ingest") -> None:
    conn.execute("INSERT INTO users (email, password_hash) VALUES (?, ?)", ("t@example.com", "x"))
    token_hash = hashlib.sha256(token_value.encode("utf-8")).hexdigest()
    conn.execute(
        "INSERT INTO api_tokens (user_id, token_hash, scopes, label) VALUES (1, ?, ?, 't')",
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


def _event(idem: str, payload=None):
    if payload is None:
        payload = {"event": "login", "world": 301}
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
        "privacy_class": "operator_private",
        "export_eligibility": "blocked",
        "payload": payload,
        "source_refs": [{"ref_type": "client", "ref_value": "abc"}],
    }


def test_migration_smoke(client):
    _, db = client
    with db.get_connection() as conn:
        row = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ingested_events'").fetchone()
    assert row is not None


def test_accept_and_store_event(client):
    c, db = client
    r = c.post("/api/v1/ledger/osrs/events", json=_event("idem-aaa11111"), headers=_headers())
    assert r.status_code == 200
    assert r.json()["status"] == "accepted"
    with db.get_connection() as conn:
        count = conn.execute("SELECT COUNT(*) FROM ingested_events").fetchone()[0]
    assert count == 1


def test_idempotent_replay(client):
    c, _ = client
    payload = _event("idem-bbb22222")
    r1 = c.post("/api/v1/ledger/osrs/events", json=payload, headers=_headers())
    r2 = c.post("/api/v1/ledger/osrs/events", json=payload, headers=_headers())
    assert r1.status_code == 200 and r2.status_code == 200
    assert r2.json()["status"] == "duplicate"
    assert r1.json()["event_id"] == r2.json()["event_id"]


def test_conflict_quarantine(client):
    c, db = client
    r1 = c.post("/api/v1/ledger/osrs/events", json=_event("idem-ccc33333", payload={"event": "login", "world": 301}), headers=_headers())
    assert r1.status_code == 200
    r2 = c.post("/api/v1/ledger/osrs/events", json=_event("idem-ccc33333", payload={"event": "logout", "world": 301}), headers=_headers())
    assert r2.status_code == 409
    with db.get_connection() as conn:
        q = conn.execute("SELECT export_eligibility FROM quarantine_records ORDER BY id DESC LIMIT 1").fetchone()
    assert q[0] == "blocked"


def test_durable_key_ip_rate_record(client):
    c, db = client
    c.post("/api/v1/ledger/osrs/events", json=_event("idem-ddd44444"), headers=_headers())
    with db.get_connection() as conn:
        row = conn.execute("SELECT request_count FROM ledger_rate_limit_records WHERE endpoint = 'events'").fetchone()
    assert row is not None and row[0] >= 1


def test_disabled_intake_status_only(client):
    c, db = client
    with db.get_connection() as conn:
        conn.execute("UPDATE intake_control SET enabled = 0, status_only = 1 WHERE scope = 'global'")
        conn.commit()
    post = c.post("/api/v1/ledger/osrs/events", json=_event("idem-eee55555"), headers=_headers())
    assert post.status_code == 503
    status_resp = c.get("/api/v1/ledger/osrs/status", headers=_headers())
    assert status_resp.status_code == 200


def test_batch_caps(client):
    c, _ = client
    events = [_event(f"idem-{i:08d}") for i in range(51)]
    r = c.post("/api/v1/ledger/osrs/events/batch", json={"events": events}, headers=_headers())
    assert r.status_code == 422


def test_validation_error_record_for_oversized(client):
    c, db = client
    huge_payload = {"event": "login", "world": 301, "x": "a" * 70000}
    r = c.post("/api/v1/ledger/osrs/events", json=_event("idem-fff66666", payload=huge_payload), headers=_headers())
    assert r.status_code in (413, 422)
    if r.status_code == 413:
        with db.get_connection() as conn:
            row = conn.execute("SELECT error_code FROM event_validation_errors WHERE idempotency_key = 'idem-fff66666'").fetchone()
        assert row is not None
