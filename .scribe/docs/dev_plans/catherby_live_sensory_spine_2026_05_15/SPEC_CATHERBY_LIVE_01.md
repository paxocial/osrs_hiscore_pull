---
id: catherby_live_sensory_spine_2026_05_15-spec-catherby-live-01
title: CATHERBY-LIVE-01 Live OSRS Event Ledger SPEC
doc_type: spec
doc_name: SPEC_CATHERBY_LIVE_01
category: engineering
status: draft
version: '0.1'
last_updated: 2026-05-15 06:45:44 UTC
maintained_by: agent-20260515-020223-e707f87e
created_by: agent-20260515-020223-e707f87e
owners: []
related_docs: []
tags: []
summary: Problem-definition SPEC for Catherby as the authenticated append-only live
  OSRS telemetry ledger feeding Dungeon Crawl evidence.
edit_trace:
  tool: manage_docs
  created_at: 2026-05-15 06:44:51 UTC
  created_via: create_doc
  last_edited_at: 2026-05-15 06:45:44 UTC
  last_edited_by: agent-20260515-020223-e707f87e
  last_action: append
  stage: spec
---

# CATHERBY-LIVE-01 Live OSRS Event Ledger SPEC

## Problem

Catherby must become the authenticated, append-only live telemetry spine for OSRS Dungeon Master work. The current repo already has hiscore snapshot/reporting behavior and a plugin API concept, but the product requires a source-cited event ledger that accepts RuneLite-derived gameplay observations, validates and hashes them, stores replay-safe records, derives facts/reports, and exposes vetted observations to Dungeon Crawl.

Hiscores remain useful background metadata. They are not the primary sensory product. The primary product input is live RuneLite telemetry or captured/replayed telemetry in real plugin-format envelopes.

## Goals

- Define the Catherby event ingestion contract for OSRS live telemetry.
- Preserve Catherby as telemetry, analytics, and advisory evidence only; it must never mutate Dungeon Crawl campaign authority.
- Gate plugin traffic with API-key authentication: no API key means no network request leaves the RuneLite plugin.
- Plan durable event storage with idempotency, replay handling, payload hashing, validation status, source refs, privacy/export classification, quarantine, and audit evidence.
- Plan rate limiting and backpressure for both public-hosted Catherby and local development.
- Keep the event ledger source-agnostic enough for later sensors while making OSRS/RuneLite the first concrete adapter.
- Reuse existing repo surfaces where sound: FastAPI endpoints, plugin auth concepts, schema validation, rate limiter ideas, report generation, SQLite/SQLAlchemy models, migration scripts, admin web surfaces.
- Prepare for managed Postgres without breaking local development, tests, or existing snapshot history.
- Support a future Catherby frontend/admin website that talks to the Catherby backend, not to Council runtime controls.

## Non-Goals

- Do not implement Catherby code in the SPEC phase.
- Do not expand the Dungeon Crawl Java plugin before Catherby ingestion is planned and built.
- Do not let RuneLite send raw events directly to Dungeon Crawl.
- Do not build RuneLite overlays, warning UI, menu/input hooks, chat insertion, packet behavior, or gameplay automation.
- Do not treat existing hiscore snapshots as live sensory proof.
- Do not require a managed Postgres service for local tests in the first package unless Blueprint explicitly designs a gated path.
- Do not connect Catherby frontend/admin web to Council controls or `.council` runtime APIs.
- Do not claim public/plugin readiness until auth, rate limit, idempotency, quarantine, payload caps, batch caps, and disable/backpressure controls exist.

## Controlling Flow

```text
RuneLite Plugin
-> Catherby ingestion API
-> Catherby event ledger / validation / hashing / audit
-> Catherby structured observation feed
-> Dungeon Crawl sensory adapter
-> Association Cortex
-> RealityFrame
-> ResponsePlan
-> local LLM proposal
-> transcript audit
-> output / optional TTS
```

Forbidden flow:

```text
RuneLite Plugin -> Dungeon Crawl raw
```

## Candidate Event Envelope

The first architecture pass must evaluate and refine this candidate, not blindly implement it:

```json
{
  "schema_version": "catherby.event.v1",
  "event_id": "uuid-or-deterministic-id",
  "source_event_id": "runelite-local-id",
  "idempotency_key": "player/session/source_event_id/hash",
  "observed_at": "client timestamp",
  "received_at": "server timestamp",
  "source_domain": "osrs",
  "source_adapter": "runelite_plugin",
  "event_family": "session|xp|inventory|equipment|bank|location|chat|drop|death|activity|quest|diary|combat_achievement",
  "player_ref": {"name": "Seaking", "mode": "main"},
  "session_id": "plugin-session-id",
  "plugin_version": "semver",
  "payload_hash": "sha256:...",
  "privacy_class": "operator_private",
  "export_eligibility": "scrub_required",
  "source_refs": [],
  "payload": {}
}
```

## Required Catherby Controls

- API-key authentication with plugin scope.
- Per-key and per-IP rate limits.
- Replay window enforcement.
- Idempotency duplicate/conflict behavior.
- Payload size caps.
- Batch size caps.
- Schema validation with stable error codes.
- Quarantine records for rejected or suspicious submissions.
- Append-only audit records for accepted and rejected submissions.
- Backpressure / disable switch so hosted Catherby can stop intake safely.
- Privacy/export classification on every accepted record.
- Source refs and payload hashes preserved through derived facts/reports.

## Candidate Storage Surfaces

Blueprint must decide exact tables/migrations after research, but the mission requires equivalents of:

- `ingested_events`
- `event_payloads`
- `event_validation_errors`
- `event_source_refs`
- `event_batches`
- `api_keys` or reuse of existing `api_tokens`
- `rate_limit_records`
- `quarantine_records`
- `derived_facts`
- `report_jobs`
- `report_event_links`

The existing snapshot tables must not be overloaded as the event ledger. Snapshots are periodic state; events are the audit trail.

## Candidate Source Surfaces For Research

Current Catherby source surfaces:

- `api/endpoints/plugin.py`
- `api/schemas/plugin.py`
- `api/dependencies.py`
- `api/main.py`
- `database/connection.py`
- `database/models.py`
- `database/sql/*.sql`
- `web/routes/admin.py`
- `web/templates/admin/*.html`
- `web/middleware/rate_limit.py`
- `web/services/audit.py`
- `core/report_builder.py`
- `agents/report_agent.py`
- `tests/test_plugin_schemas.py`
- `tests/test_api_dependencies.py`

External prior-art targets:

- Wise Old Man RuneLite plugin / client sync behavior.
- OSRS Wiki Sync RuneLite plugin and any published sync schemas.
- Bank Value / bank valuation RuneLite plugin behavior for bank/container access patterns.
- RuneLite plugin hub examples for `StatChanged`, `ItemContainerChanged`, `GameTick`, `ClientTick`, `ChatMessage`, session/login/logout, and HTTP client patterns.

## Research Questions

1. What plugin telemetry schemas and endpoint behaviors already exist in this repo, and which pieces are safe to reuse for a unified event ledger?
2. What current storage model is actually authoritative: raw SQLite SQL migrations, SQLAlchemy models, or a mixed path? What is the least risky path toward managed Postgres while preserving local dev?
3. How does existing auth/rate limiting work, what is production-safe, and what must change before public/plugin traffic?
4. What do Wise Old Man, OSRS Wiki Sync, Bank Value, and related open RuneLite plugins actually collect, batch, hash, authenticate, and send?
5. Which RuneLite event families are reliable and safe for the first exporter nerve, and what payload shapes should Catherby accept first?
6. What evidence feed shape should Dungeon Crawl consume so Catherby remains advisory and source-cited without leaking raw plugin internals into campaign authority?
7. What admin/frontend surfaces are required for Catherby hosted operations, and how do we keep them separate from Council runtime controls?

## Initial Research Bracket

Wave 1 may run up to five researchers in parallel after this SPEC quality-checks clean:

- Lens: current Catherby API/schema/database/report inventory.
- Sentinel: auth, rate limit, replay, quarantine, hosted exposure, API-key and public traffic threat model.
- Lens: external RuneLite telemetry plugin prior-art research, including Wise Old Man, OSRS Wiki Sync, Bank Value, and RuneLite event/API patterns.
- Loom: Catherby hosted/admin frontend boundary research only, focused on required operator surfaces and separation from Council controls.

Synthesis must happen before Blueprint. Blueprint may then write `ARCHITECTURE_GUIDE`, `PHASE_PLAN`, `CHECKLIST`, and bounded task packages.

## Definition Of Done For This SPEC Stage

- SPEC exists as managed Scribe doc with problem, goals, non-goals, constraints, candidate surfaces, and research questions.
- SPEC does not contain implementation task packages or architecture decisions pretending to be final design.
- Research can be delegated from this SPEC without agents needing the coordinator transcript.
