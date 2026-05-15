-- Migration 013: Catherby live event ledger core (session/xp first package)

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS ingested_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL UNIQUE,
    source_event_id TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    source_domain TEXT NOT NULL,
    source_adapter TEXT NOT NULL,
    event_family TEXT NOT NULL,
    player_ref TEXT NOT NULL,
    session_id TEXT NOT NULL,
    plugin_version TEXT NOT NULL,
    privacy_class TEXT NOT NULL,
    export_eligibility TEXT NOT NULL,
    validation_status TEXT NOT NULL,
    reason_code TEXT,
    token_id INTEGER,
    token_user_id INTEGER,
    source_ip TEXT,
    user_agent TEXT,
    observed_at DATETIME NOT NULL,
    received_at DATETIME NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(idempotency_key)
);

CREATE INDEX IF NOT EXISTS idx_ingested_events_idempotency ON ingested_events(idempotency_key);
CREATE INDEX IF NOT EXISTS idx_ingested_events_family ON ingested_events(event_family);
CREATE INDEX IF NOT EXISTS idx_ingested_events_created ON ingested_events(created_at);

CREATE TABLE IF NOT EXISTS event_payloads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (event_id) REFERENCES ingested_events(event_id) ON DELETE CASCADE,
    UNIQUE(event_id)
);

CREATE TABLE IF NOT EXISTS event_validation_errors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT,
    idempotency_key TEXT,
    error_code TEXT NOT NULL,
    detail TEXT,
    payload_hash TEXT,
    export_eligibility TEXT NOT NULL DEFAULT 'blocked',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_event_validation_errors_event ON event_validation_errors(event_id);
CREATE INDEX IF NOT EXISTS idx_event_validation_errors_key ON event_validation_errors(idempotency_key);

CREATE TABLE IF NOT EXISTS event_source_refs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL,
    ref_type TEXT NOT NULL,
    ref_value TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (event_id) REFERENCES ingested_events(event_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_event_source_refs_event ON event_source_refs(event_id);

CREATE TABLE IF NOT EXISTS event_batches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id TEXT NOT NULL UNIQUE,
    total_events INTEGER NOT NULL,
    accepted_count INTEGER NOT NULL,
    duplicate_count INTEGER NOT NULL,
    conflict_count INTEGER NOT NULL,
    rejected_count INTEGER NOT NULL,
    total_payload_bytes INTEGER NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS quarantine_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT,
    idempotency_key TEXT,
    payload_hash TEXT,
    reason_code TEXT NOT NULL,
    payload_summary TEXT,
    source_domain TEXT,
    source_adapter TEXT,
    token_id INTEGER,
    source_ip TEXT,
    review_state TEXT NOT NULL DEFAULT 'pending',
    export_eligibility TEXT NOT NULL DEFAULT 'blocked',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_quarantine_records_key ON quarantine_records(idempotency_key);

CREATE TABLE IF NOT EXISTS ledger_rate_limit_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token_id INTEGER NOT NULL,
    source_ip TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    window_start TEXT NOT NULL,
    request_count INTEGER NOT NULL DEFAULT 1,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(token_id, source_ip, endpoint, window_start)
);

CREATE INDEX IF NOT EXISTS idx_ledger_rate_lookup ON ledger_rate_limit_records(token_id, source_ip, endpoint, window_start);

CREATE TABLE IF NOT EXISTS intake_control (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scope TEXT NOT NULL UNIQUE DEFAULT 'global',
    enabled INTEGER NOT NULL DEFAULT 1,
    status_only INTEGER NOT NULL DEFAULT 0,
    degraded INTEGER NOT NULL DEFAULT 0,
    reason TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

INSERT OR IGNORE INTO intake_control (scope, enabled, status_only, degraded, reason)
VALUES ('global', 1, 0, 0, 'default');

INSERT OR REPLACE INTO schema_version (id, version, description)
VALUES (13, '2.2', 'Added Catherby live event ledger core tables');
