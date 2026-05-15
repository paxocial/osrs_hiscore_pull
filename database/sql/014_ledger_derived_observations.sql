-- Migration 014: Catherby advisory observation read model from accepted ledger events

PRAGMA foreign_keys = ON;

DROP VIEW IF EXISTS v_ledger_exportable_observations;

CREATE VIEW v_ledger_exportable_observations AS
SELECT
    e.event_id,
    e.idempotency_key,
    e.payload_hash,
    e.privacy_class,
    e.export_eligibility,
    e.event_family,
    e.source_domain,
    e.source_adapter,
    e.player_ref,
    e.created_at
FROM ingested_events e
WHERE e.validation_status = 'accepted'
  AND e.export_eligibility = 'exportable'
  AND NOT EXISTS (
      SELECT 1
      FROM quarantine_records q
      WHERE q.event_id = e.event_id
         OR (q.idempotency_key IS NOT NULL AND q.idempotency_key = e.idempotency_key)
  );

INSERT OR REPLACE INTO schema_version (id, version, description)
VALUES (14, '2.3', 'Added derived advisory observation read model view');
