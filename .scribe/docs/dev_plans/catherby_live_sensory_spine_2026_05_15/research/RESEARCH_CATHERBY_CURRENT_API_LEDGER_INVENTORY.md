---
id: catherby_live_sensory_spine_2026_05_15-research-catherby-current-api-ledger-inventory
title: "\U0001F52C Research Catherby Current Api Ledger Inventory \u2014 catherby_live_sensory_spine_2026_05_15"
doc_type: RESEARCH_CATHERBY_CURRENT_API_LEDGER_INVENTORY
doc_name: RESEARCH_CATHERBY_CURRENT_API_LEDGER_INVENTORY
category: engineering
status: ready
version: '0.2'
last_updated: 2026-05-15 06:55:47 UTC
maintained_by: agent-20260515-064637-4ba7fba4
created_by: agent-20260515-064637-4ba7fba4
owners: []
related_docs: []
tags: []
summary: Current Catherby API/schema/database/report inventory for CATHERBY-LIVE-01
  with reuse candidates and conflicts against the append-only event ledger requirement.
edit_trace:
  tool: manage_docs
  created_at: 2026-05-15 06:55:47 UTC
  created_via: frontmatter_update
  last_edited_at: 2026-05-15 06:55:47 UTC
  last_edited_by: agent-20260515-064637-4ba7fba4
  last_action: frontmatter_update
---

# 🔬 Research Catherby Current Api Ledger Inventory — catherby_live_sensory_spine_2026_05_15
**Author:** Scribe
**Version:** v0.1
**Status:** ready
**Last Updated:** 2026-05-15 06:52:18 UTC

> Inventory of current Catherby API, schema, database, and report surfaces for CATHERBY-LIVE-01.

---
## Executive Summary
<!-- ID: executive_summary -->
# Executive Summary

Catherby’s current plugin surface is a live-ingestion API in name, but the implementation is still a snapshot-era, table-per-family pipeline backed by SQLite migrations, raw `sqlite3` inserts, and a snapshot report stack. The live-ledger requirement in `SPEC_CATHERBY_LIVE_01.md` is materially broader: append-only events, idempotency, payload hashes, quarantine, privacy/export classification, and ledger-oriented storage surfaces that do not exist yet.

Confidence: high.

- The current plugin route prefix is `/api/v1/plugin`, not the older `/api/v1/player/...` plan documented in `RUNELITE_PLUGIN_NEXT_STEPS.md`.
- The current auth path already reuses `api_tokens`, but the scope check is substring-based and may be too loose for public live traffic.
- The current SQL migrations define auth/rate limit/audit infrastructure, but not the `plugin_*` tables that the route handlers attempt to insert into.
- The first package should therefore be ledger-storage-first, not report-first.
## Research Scope
<!-- ID: research_scope -->
# Executive finding

Catherby already has a functioning RuneLite plugin API, but it is a snapshot-oriented ingestion surface, not an append-only live event ledger. The current code accepts 12 plugin endpoints under `/api/v1/plugin`, validates them with Pydantic models, authenticates them with `X-API-Key`, rate-limits them in memory, and writes each payload family into separate SQLite tables via raw `sqlite3` inserts. The storage and report layers are still built around snapshot history, not ledger semantics.

Confidence: high.

Evidence:
- `api/main.py:176-204` includes the plugin router at `/api/v1/plugin`.
- `api/endpoints/plugin.py:1-1116` defines the current plugin API surface and persistence logic.
- `api/schemas/plugin.py:1-405` defines the plugin payload and response schemas.
- `api/dependencies.py:42-364` defines plugin auth and rate limiters.
- `database/sql/001_initial_schema.sql:1-209`, `database/sql/004_auth_clans_tokens.sql:1-196`, `database/sql/009_rate_limiting.sql:1-23`, and `database/sql/011_audit_log.sql:1-21` define the current SQLite truth for core tables, auth tokens, rate limiting, and audit logging.
- `.scribe/docs/dev_plans/catherby_live_sensory_spine_2026_05_15/SPEC_CATHERBY_LIVE_01.md:80-136` defines the live-ledger controls and candidate storage surfaces that do not yet exist in the runtime code.

# Source inventory with file-level evidence

| Surface | What exists now | Evidence | Confidence |
|---|---|---|---|
| `api/main.py` | Registers the plugin router at `/api/v1/plugin` and applies a global IP rate limiter to all requests. | `api/main.py:1-204` | high |
| `api/endpoints/plugin.py` | 12 plugin endpoints plus batch/status; writes directly to `plugin_sessions`, `plugin_xp_snapshots`, `plugin_collection_log`, `plugin_quests`, `plugin_diaries`, `plugin_combat_achievements`, `plugin_equipment`, `plugin_loot`, `plugin_activity`, `plugin_bank`, and `plugin_sync_log`. | `api/endpoints/plugin.py:1-1116` | high |
| `api/schemas/plugin.py` | Pydantic v2 models for the 12 payload types plus `BatchPayload` and `StatusResponse`; includes validation for RSN, world, semver plugin version, 23-skill XP snapshots, tier validation, and bank item shape. | `api/schemas/plugin.py:1-405` | high |
| `api/dependencies.py` | `require_plugin_key` hashes `X-API-Key` with SHA-256, checks `api_tokens.token_hash`, requires `plugin` scope, updates `last_used_at`, and exposes token/IP rate limiters. | `api/dependencies.py:42-364` | high |
| `database/connection.py` | SQLite-first connection manager with migration runner that executes `database/sql/*.sql`; no separate plugin-specific migration path is present. | `database/connection.py:1-257` | high |
| `database/models.py` | ORM covers snapshot-era entities (`accounts`, `snapshots`, `skills`, `activities`, `snapshots_deltas`, `mode_cache`, `schema_version`) and does not define plugin ledger tables. | `database/models.py:1-359` | high |
| `database/sql/*.sql` | Core SQLite migrations define accounts, snapshots, auth tokens, IP rate limiting, and audit logging, but no `plugin_*` tables. | `database/sql/001_initial_schema.sql:1-209`, `database/sql/004_auth_clans_tokens.sql:1-196`, `database/sql/009_rate_limiting.sql:1-23`, `database/sql/011_audit_log.sql:1-21` | high |
| `core/report_builder.py` | Snapshot report generator for Markdown output; it computes snapshot totals and deltas, not live event ledger reports. | `core/report_builder.py:1-241` | high |
| `agents/report_agent.py` | Wraps snapshot report generation and Scribe reporting; still snapshot-oriented. | `agents/report_agent.py:1-78` | high |
| `README.md` | Documents the repo as a snapshot/reporting toolkit, with no live Catherby ledger contract. | `README.md:1-82` | high |
| `docs/dev_plans/PLUGIN_API_SCHEMA.md` | Documents a 11-table plugin schema with append-only time-series tables, JSONB/Postgres migration notes, and plugin sync audit logging, but those tables are not present in the runtime SQL files. | `docs/dev_plans/PLUGIN_API_SCHEMA.md:1-1269` | high |
| `docs/dev_plans/RUNELITE_PLUGIN_NEXT_STEPS.md` | Proposes old future API endpoints under `/api/v1/player/...` and plugin UI-heavy goals that do not match the current `/api/v1/plugin` implementation. | `docs/dev_plans/RUNELITE_PLUGIN_NEXT_STEPS.md:1-282` | high |
## Findings
<!-- ID: findings -->
# Findings

- Finding 1: The runtime plugin API exists and is wired end-to-end at `/api/v1/plugin`, with 12 handlers plus batch/status. Confidence: high. Evidence: `api/main.py:176-204`, `api/endpoints/plugin.py:1-1116`.
- Finding 2: Plugin auth is already centralized around `X-API-Key` and `api_tokens`, but the current scope gate is substring matching, not exact scope semantics. Confidence: high. Evidence: `api/dependencies.py:42-118`, `tests/test_api_dependencies.py:69-198`.
- Finding 3: Storage truth is mixed. SQLite migrations own the authoritative DB bootstrap, while plugin routes write to tables that are not defined in `database/sql/*.sql`. Confidence: high. Evidence: `database/connection.py:1-257`, `database/sql/001_initial_schema.sql:1-209`, `database/sql/004_auth_clans_tokens.sql:1-196`, `database/sql/009_rate_limiting.sql:1-23`, `database/sql/011_audit_log.sql:1-21`, `api/endpoints/plugin.py:73-845`.
- Finding 4: The plugin schema docs already describe a richer append-only ledger model than the runtime code implements, including idempotency, audit, and Postgres migration guidance. Confidence: high. Evidence: `docs/dev_plans/PLUGIN_API_SCHEMA.md:1-1269`, `.scribe/docs/dev_plans/catherby_live_sensory_spine_2026_05_15/SPEC_CATHERBY_LIVE_01.md:80-136`.
- Finding 5: Existing tests cover schemas and auth dependency behavior, but not the plugin route handlers or storage migrations. Confidence: medium. Evidence: `tests/test_plugin_schemas.py:1-517`, `tests/test_api_dependencies.py:1-198`.
## Technical Analysis
<!-- ID: technical_analysis -->
# Existing contracts and invariants

- `api/main.py` mounts the plugin router at `/api/v1/plugin` and also applies the global IP rate limiter before route dispatch. Confidence: high. Evidence: `api/main.py:1-204`.
- `api/endpoints/plugin.py` defines 12 concrete endpoints plus `/batch` and `/status`, and every payload handler follows the same pattern: auth dependency, per-token rate-limit check, RSN lookup in `accounts`, raw SQLite insert, audit log insert, commit, return `{"status": "ok"}`. Confidence: high. Evidence: `api/endpoints/plugin.py:1-1116`.
- `api/dependencies.py` authenticates via `X-API-Key`, SHA-256 hashes the token, checks `api_tokens.token_hash`, rejects revoked tokens, requires `plugin` substring in `scopes`, and updates `last_used_at`. Confidence: high. Evidence: `api/dependencies.py:42-118`.
- `api/dependencies.py` also exposes `plugin_rate_limiter` at 30 requests/minute and `batch_rate_limiter` at 10 batch requests/minute. Confidence: high. Evidence: `api/dependencies.py:292-364`.
- `api/schemas/plugin.py` enforces the current payload contract: RSN length, world 300-600, semver plugin version, 23 required skill keys for XP snapshots, non-negative tier counts, bounded item fields, and optional batch categories. Confidence: high. Evidence: `api/schemas/plugin.py:15-405`.
- `database/connection.py` is the runtime migration truth for SQLite. It runs SQL files from `database/sql/` and currently has no plugin-ledger-specific branch or Postgres migration path. Confidence: high. Evidence: `database/connection.py:1-257`.
- `database/models.py` is a parallel ORM truth for snapshot-era entities only; it does not define plugin ingestion tables or an event ledger model. Confidence: high. Evidence: `database/models.py:1-359`.
- `core/report_builder.py` and `agents/report_agent.py` are downstream consumers of snapshot data, not live event data. Confidence: high. Evidence: `core/report_builder.py:14-241`, `agents/report_agent.py:22-78`.

# Reuse candidates

- Reuse `require_plugin_key` as the auth entrypoint only if Blueprint keeps `api_tokens` as the plugin key store; otherwise split it into a shared auth helper and a ledger-specific key policy. Confidence: medium. Evidence: `api/dependencies.py:42-118`, `database/sql/004_auth_clans_tokens.sql:47-60`.
- Reuse `plugin_rate_limiter` and `batch_rate_limiter` as design inspiration for per-token throttling, but not as the final ledger contract because they are in-memory and reset on process restart. Confidence: high. Evidence: `api/dependencies.py:292-364`.
- Reuse the `BatchPayload` shape as a packetization hint only; the live ledger spec needs event envelope fields such as `event_id`, `idempotency_key`, `payload_hash`, `privacy_class`, and source refs that the current batch model does not include. Confidence: high. Evidence: `api/schemas/plugin.py:335-380`, `.scribe/docs/dev_plans/catherby_live_sensory_spine_2026_05_15/SPEC_CATHERBY_LIVE_01.md:80-136`.
- Reuse `DatabaseConnection` for local SQLite access patterns if the first package stays SQLite-first, but do not assume its current migration runner can provision ledger tables automatically because the SQL files do not define them. Confidence: high. Evidence: `database/connection.py:1-257`, `database/sql/*.sql`.
- Reuse the snapshot report builder only for derived reporting after the ledger exists. It is not a ledger writer and should stay isolated from first-wave ingestion work. Confidence: high. Evidence: `core/report_builder.py:14-241`, `agents/report_agent.py:22-78`.

# Conflicts and gaps against CATHERBY-LIVE-01

- The live SPEC requires an append-only event envelope with idempotency, payload hashes, quarantine, privacy/export classification, and source refs, but the current plugin API stores separate domain tables and does not model those fields. Confidence: high. Evidence: `.scribe/docs/dev_plans/catherby_live_sensory_spine_2026_05_15/SPEC_CATHERBY_LIVE_01.md:80-136`, `api/endpoints/plugin.py:103-1116`, `api/schemas/plugin.py:15-405`.
- The SPEC lists candidate storage surfaces such as `ingested_events`, `event_payloads`, `event_validation_errors`, `event_source_refs`, `event_batches`, `rate_limit_records`, `quarantine_records`, `derived_facts`, `report_jobs`, and `report_event_links`, but the runtime SQL migrations only provide snapshot-era tables plus `api_tokens`, `rate_limit_store`, and `audit_log`. Confidence: high. Evidence: `.scribe/docs/dev_plans/catherby_live_sensory_spine_2026_05_15/SPEC_CATHERBY_LIVE_01.md:121-136`, `database/sql/001_initial_schema.sql:1-209`, `database/sql/004_auth_clans_tokens.sql:1-196`, `database/sql/009_rate_limiting.sql:1-23`, `database/sql/011_audit_log.sql:1-21`.
- The current plugin route handlers write to `plugin_*` tables, but no `database/sql/*.sql` migration defines those tables. That means the ledger implementation cannot safely reuse the current write path without first fixing the storage contract. Confidence: high. Evidence: `api/endpoints/plugin.py:73-845`, `database/sql/001_initial_schema.sql:1-209`, `database/sql/004_auth_clans_tokens.sql:1-196`, `database/sql/009_rate_limiting.sql:1-23`, `database/sql/011_audit_log.sql:1-21`.
- The docs in `docs/dev_plans/PLUGIN_API_SCHEMA.md` describe an 11-table append-only plugin schema with `plugin_sync_log`, but the runtime code currently implements a smaller, ad hoc version of that shape and never defines the tables in migrations. Confidence: high. Evidence: `docs/dev_plans/PLUGIN_API_SCHEMA.md:1-1269`, `api/endpoints/plugin.py:73-845`.
- `require_plugin_key` treats any scope string containing `plugin` as valid, including substrings such as `my_plugin_api`. That behavior is documented by the tests and may be too loose for a public live ledger if Blueprint wants explicit scope semantics. Confidence: high. Evidence: `api/dependencies.py:63-87`, `tests/test_api_dependencies.py:69-198`.
- `docs/dev_plans/RUNELITE_PLUGIN_NEXT_STEPS.md` still frames the backend around `/api/v1/player/{player}/current`, `/history`, and `/snapshot` endpoints plus plugin UI work, which conflicts with the actual `/api/v1/plugin` ingestion router and the live-ledger problem statement. Confidence: high. Evidence: `docs/dev_plans/RUNELITE_PLUGIN_NEXT_STEPS.md:159-200`, `api/main.py:176-204`, `api/endpoints/plugin.py:1-1116`.
- `README.md` still describes the repo as a snapshot/diff/report toolkit and does not mention the live telemetry ledger contract, so it is not a reliable statement of the Catherby-LIVE-01 target state. Confidence: high. Evidence: `README.md:1-82`.

# Test surfaces

- `tests/test_plugin_schemas.py` covers the full schema set: base payload, session event rules, XP snapshot validation, collection log, quest state, diary defaults, combat achievement tiers, equipment snapshots, loot drop shape, activity updates, bank snapshot validation, batch payload composition, and status response. Confidence: high. Evidence: `tests/test_plugin_schemas.py:1-517`.
- `tests/test_api_dependencies.py` covers `require_plugin_key` failure and success paths, SHA-256 hashing, revoked token handling, scope filtering, and the current substring-scope behavior. Confidence: high. Evidence: `tests/test_api_dependencies.py:1-198`.
- No endpoint-integration tests for `api/endpoints/plugin.py` were found in the inspected test surface. Confidence: medium. Evidence: `tests/test_plugin_schemas.py:1-517`, `tests/test_api_dependencies.py:1-198`.
- No tests were found in the inspected surface for the plugin-specific SQLite tables or migration presence. Confidence: medium. Evidence: `database/sql/*.sql`, `tests/test_plugin_schemas.py:1-517`, `tests/test_api_dependencies.py:1-198`.

# Blueprint questions and risks

- Should Blueprint preserve `/api/v1/plugin` and convert the handler family into an append-only event ledger, or is a new prefix and new DTO surface required? Confidence: high. Evidence: `api/main.py:176-204`, `.scribe/docs/dev_plans/catherby_live_sensory_spine_2026_05_15/SPEC_CATHERBY_LIVE_01.md:58-136`.
- Should `api_tokens` remain the auth truth for plugin traffic, or should a dedicated ledger-key table be introduced for event ingestion while keeping existing token auth separate? Confidence: medium. Evidence: `database/sql/004_auth_clans_tokens.sql:47-60`, `.scribe/docs/dev_plans/catherby_live_sensory_spine_2026_05_15/SPEC_CATHERBY_LIVE_01.md:121-136`.
- Should the first package remain SQLite-first with raw SQL migrations, or should it introduce a dual-path storage abstraction that can later target Postgres without rewriting the route layer? Confidence: high. Evidence: `database/connection.py:1-257`, `database/models.py:1-359`, `docs/dev_plans/PLUGIN_API_SCHEMA.md:873-1000`.
- Should the live ledger keep the current table-per-family model for derived analytics, or collapse into a single event table plus typed derived views? Confidence: high. Evidence: `api/endpoints/plugin.py:73-845`, `.scribe/docs/dev_plans/catherby_live_sensory_spine_2026_05_15/SPEC_CATHERBY_LIVE_01.md:80-136`.
- The biggest implementation risk is drift between raw SQLite migrations and Python runtime assumptions. If Blueprint does not choose one storage source of truth for the first package, the ledger work will continue to break at startup or first insert. Confidence: high. Evidence: `database/connection.py:1-257`, `database/models.py:1-359`, `api/endpoints/plugin.py:73-845`.

# Recommended first package boundary candidates

- Likely owns first: `api/endpoints/plugin.py`, `api/schemas/plugin.py`, `api/dependencies.py`, and one or more `database/sql/*.sql` migrations for the ledger tables. Confidence: high. Evidence: those files currently own the live plugin contract and storage writes.
- Likely also owns `api/main.py` only if the router prefix or application middleware needs to change. Confidence: medium. Evidence: `api/main.py:176-204`.
- Forbidden / out of scope for the first package unless Blueprint explicitly widens the boundary: `core/report_builder.py`, `agents/report_agent.py`, `README.md`, and the snapshot-era ORM in `database/models.py`. Confidence: medium. Evidence: those surfaces are downstream or documentation layers, not the live event writer.
- If Blueprint chooses an ORM-backed ledger path, `database/models.py` becomes in-scope; otherwise it should stay untouched in package one. Confidence: medium. Evidence: `database/models.py:1-359`, `database/connection.py:1-257`.
- Blueprint should design around the live event envelope and storage truth, preserve the current auth/rate-limit intent where safe, and verify that no plugin write path depends on tables that are still only documented but not migrated. Confidence: high.
## Recommendations
<!-- ID: recommendations -->
# Recommendations

### Immediate Next Steps
- Blueprint should define the first ledger package around storage truth, ledger envelope shape, and auth/rate-limit policy before touching reporting.
- The first implementation package should own the plugin router, plugin schemas, plugin auth dependency, and the initial ledger migrations together so inserts cannot outpace schema.
- Preserve `api_tokens` only if the live ledger keeps a token-based auth story; otherwise introduce a ledger-specific auth boundary and leave the existing token system intact.
- Do not let report generation or README prose drive the ledger contract; those surfaces should be updated only after the ledger contract is fixed.

### Long-Term Opportunities
- Convert the current table-per-family plugin design into ledger events plus typed derived views.
- Move from in-memory token rate limiting to durable persistence that can support restart-safe throttling and quarantine.
- Align the runtime database path with the plugin schema doc so SQLite and Postgres migrations share one source of truth.
## Appendix
<!-- ID: appendix -->
# Appendix

## Relevant files
- `api/main.py:1-204`
- `api/endpoints/plugin.py:1-1116`
- `api/schemas/plugin.py:1-405`
- `api/dependencies.py:42-364`
- `database/connection.py:1-257`
- `database/models.py:1-359`
- `database/sql/001_initial_schema.sql:1-209`
- `database/sql/004_auth_clans_tokens.sql:1-196`
- `database/sql/009_rate_limiting.sql:1-23`
- `database/sql/011_audit_log.sql:1-21`
- `core/report_builder.py:14-241`
- `agents/report_agent.py:22-78`
- `README.md:1-82`
- `docs/dev_plans/PLUGIN_API_SCHEMA.md:1-1269`
- `docs/dev_plans/RUNELITE_PLUGIN_NEXT_STEPS.md:1-282`
- `.scribe/docs/dev_plans/catherby_live_sensory_spine_2026_05_15/SPEC_CATHERBY_LIVE_01.md:80-136`

## Unknowns
- `web/routes/admin.py`, `web/templates/admin/*.html`, `web/middleware/rate_limit.py`, and `web/services/audit.py` were named in the SPEC as research targets, but they were not part of the required surface set for this inventory and were not inspected here. Confidence: high.
- I did not find any endpoint-integration tests for the plugin router in the inspected test files, but a broader search outside the requested surface could still surface them. Confidence: medium.

## Handoff
Blueprint should design around the live event envelope and ledger storage truth, preserve the useful auth/rate-limit intent where safe, and verify that the first package owns the schema and route changes together so the plugin writer cannot target tables that do not exist yet.
