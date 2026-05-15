---
id: catherby_live_sensory_spine_2026_05_15-architecture
title: "\U0001F3D7\uFE0F Architecture Guide \u2014 catherby_live_sensory_spine_2026_05_15"
doc_type: architecture
doc_name: architecture
category: engineering
status: ready
version: v1.0
last_updated: 2026-05-15 07:26:54 UTC
maintained_by: agent-20260515-071009-2c5bfb98
created_by: agent-20260515-071009-2c5bfb98
owners: []
related_docs: []
tags: []
summary: CATHERBY-LIVE-01 ledger-first architecture with APPROACH_SUMMARY and executable
  first package boundary.
edit_trace:
  tool: manage_docs
  created_at: 2026-05-15 07:26:54 UTC
  created_via: frontmatter_update
  last_edited_at: 2026-05-15 07:26:54 UTC
  last_edited_by: agent-20260515-071009-2c5bfb98
  last_action: frontmatter_update
  stage: blueprint_ready
---

# 🏗️ Architecture Guide — catherby_live_sensory_spine_2026_05_15
**Author:** Scribe
**Version:** Draft v0.1
**Status:** ready
**Last Updated:** 2026-05-15 06:42:06 UTC

> Architecture guide for catherby_live_sensory_spine_2026_05_15.

---
## 1. Problem Statement
<!-- ID: problem_statement -->
## APPROACH_SUMMARY

**Goal:** Build Catherby as the authenticated append-only OSRS telemetry ledger and advisory evidence source, with no raw RuneLite-to-Dungeon-Crawl path and no Dungeon Crawl authority mutation.

**Files to modify in first implementation package:** `api/schemas/ledger.py`, `api/endpoints/ledger.py`, `api/dependencies.py`, `api/main.py`, `database/sql/013_live_event_ledger.sql`, `tests/test_live_event_ledger_schemas.py`, `tests/test_live_event_ledger_api.py`, `tests/test_api_dependencies.py`.

**Files forbidden in first implementation package:** RuneLite Java/plugin files, Dungeon Crawl consumer/adapter files, `core/report_builder.py`, `agents/report_agent.py`, `database/models.py`, `web/**`, README/public marketplace docs, bank/inventory/equipment/chat/container telemetry surfaces, and generated `.scribe/.council/.codex/.claude` surfaces outside managed planning docs.

**Out of scope for first package:** RuneLite exporter implementation, report UI, admin/frontend UI, bank/chat/container telemetry, direct Dungeon Crawl export or mutation, public/plugin marketplace readiness claims, local LLM process management, and hosted Postgres dependency for tests.

**Verification plan:** package tests for ledger schemas/API/auth/idempotency/quarantine/rate/backpressure, direct neighbor tests for existing plugin schemas and API dependencies, migration smoke on a temporary SQLite database, and import smoke for every modified Python module.

## Problem Statement

Catherby must move from a hiscore/snapshot reporting app with a partial plugin API into a live OSRS event ledger. Wave 1 research shows the existing `/api/v1/plugin` surface is real and authenticated, but it writes table-per-family `plugin_*` rows that current SQL migrations do not define. It also lacks unified event envelopes, durable idempotency, payload hashes, replay handling, quarantine, privacy/export classes, persistent per-key/per-IP rate limiting, and a backpressure/disable state.

The target product boundary is explicit: Catherby accepts and validates RuneLite-derived telemetry, stores source-cited append-only evidence, derives reports/facts later, and exposes only vetted advisory observations downstream. Dungeon Crawl remains the campaign authority. RuneLite raw events must never bypass Catherby and must never mutate Dungeon Crawl directly.

Hiscore snapshots remain useful supplemental context. They are not the primary live sensory input for CATHERBY-LIVE-01.
## 2. Requirements & Constraints
<!-- ID: requirements_constraints -->
**Functional requirements**
- Ingest OSRS event envelopes from authenticated plugin clients through a ledger-specific API surface.
- Accept only `session` and `xp` event families in the first ledger package.
- Store accepted events append-only with `event_id`, `source_event_id`, `idempotency_key`, `payload_hash`, `schema_version`, source adapter/domain, player/session refs, plugin version, privacy/export class, validation status, source refs, and received timestamp.
- Store batch metadata, validation errors, quarantine records, source refs, durable rate records, and backpressure/intake state before any derived facts or reports are produced.
- Return deterministic replay results: same idempotency key plus same payload hash returns the original accepted event; same key plus different hash is rejected or quarantined without creating an exportable event.
- Keep `api_tokens` as the first key store only if Forge tightens scope parsing to delimiter-aware exact `plugin` or `plugin:ingest` scope semantics.
- Keep local development and package tests on SQLite; managed Postgres remains a target direction, not a first-package runtime dependency.

**Security and boundary constraints**
- No public/plugin readiness claim until exact-scope auth, persistent per-key/per-IP rate limiting, replay/idempotency, payload and batch caps, quarantine, backpressure/disable switch, privacy/export classes, source refs/hashes, and public/private route separation are planned and verified.
- Raw RuneLite events never go directly to Dungeon Crawl.
- Catherby may later export only privacy-classified, source-cited advisory observations; it must not mutate Dungeon Crawl authority.
- Hosted Catherby routes must not expose Council runtime controls, local operator pages, test routes, private backend APIs, or unsafe docs/OpenAPI surfaces without explicit protected routing.
- Admin/frontend packages require Loom `DESIGN_SYSTEM` and `COMPONENT_SPECS` before Quill implementation. The completed Loom research artifact is not a design contract.

**Assumptions**
- Existing FastAPI/Pydantic/SQLite patterns remain the implementation substrate for CATHERBY-LIVE-01A.
- Existing snapshot and hiscore storage remain intact and supplemental.
- The local LLM is a downstream consumer after mapping/advisory export; implementation packages must not start, stop, or manage it.
## 3. Architecture Overview
<!-- ID: architecture_overview -->
**Selected architecture path:** additive ledger boundary plus legacy plugin quarantine.

**Components**
- **Ledger schema layer:** new Pydantic models define `CatherbyEventEnvelope`, `CatherbyEventBatch`, stable validation error codes, privacy/export enums, source refs, and session/xp payload contracts. First package accepts `session` and `xp` only.
- **Ledger ingestion router:** new FastAPI router handles `/api/v1/ledger/osrs/events`, `/api/v1/ledger/osrs/events/batch`, and `/api/v1/ledger/osrs/status`. It uses exact plugin ingest auth, durable rate checks, body/batch caps, backpressure checks, idempotency handling, and quarantine writes.
- **Auth/policy dependencies:** `api/dependencies.py` keeps existing token lookup but adds delimiter-aware scope parsing and ledger-specific dependency helpers. Existing in-memory limiters may remain for non-ledger/local paths, but ledger readiness depends on durable rate records.
- **SQLite-first ledger migration:** `database/sql/013_live_event_ledger.sql` creates the first local storage truth for `ingested_events`, `event_payloads`, `event_validation_errors`, `event_source_refs`, `event_batches`, `rate_limit_records`, `quarantine_records`, and `intake_control`. DDL should avoid SQLite-only naming where possible, but tests run on SQLite.
- **Legacy plugin router:** existing `/api/v1/plugin` table-per-family handlers remain untouched except for shared auth-scope behavior if required by dependency changes. They must be documented as legacy/local and must not be used as the public ledger claim.

**Data flow**
`RuneLite Plugin -> Catherby ledger API -> auth/scope check -> durable key/IP rate check -> backpressure check -> envelope validation and payload hash -> idempotency decision -> accepted ledger/quarantine/audit -> later derived observations -> later Dungeon Crawl advisory adapter`.

**Forbidden flow**
`RuneLite Plugin -> Dungeon Crawl raw` remains forbidden in every package.
## 4. Detailed Design
<!-- ID: detailed_design -->
**Event envelope contract**
- `CatherbyEventEnvelope` must require: `schema_version`, `source_event_id`, `idempotency_key`, `observed_at`, `source_domain`, `source_adapter`, `event_family`, `player_ref`, `session_id`, `plugin_version`, `privacy_class`, `export_eligibility`, and `payload`.
- Server-generated fields: `event_id`, `received_at`, `payload_hash`, validation status, token id/user id, source IP, and storage timestamps.
- Allowed first-family payloads: `session` and `xp`. `session` covers login/logout/world-hop lifecycle. `xp` covers full 23-skill XP snapshots or XP delta payloads if Forge proves deterministic validation. Bank, inventory, equipment, collection log, quest/diary, combat achievement, activity, loot, chat, and container telemetry are forbidden in CATHERBY-LIVE-01A.
- `payload_hash` must be SHA-256 over canonical JSON after validation and before storage. Source refs must be stored as explicit rows or JSON summaries linked to the accepted event.

**Auth and scope contract**
- Preserve missing/invalid/revoked key fail-closed behavior.
- Replace substring scope behavior with `parse_token_scopes(scopes: str) -> set[str]` and require exact `plugin:ingest` or exact `plugin` during the transitional package.
- Add negative coverage for `my_plugin_api`, `readplugin`, empty strings, malformed delimiters, and revoked tokens.

**Storage contract**
- `ingested_events`: one accepted/rejected event ledger row with unique `idempotency_key`, `payload_hash`, source metadata, family, validation status, privacy/export class, timestamps, and token/user refs.
- `event_payloads`: payload body for accepted events, separated so future retention/redaction can operate without rewriting ledger metadata.
- `event_batches`: batch request metadata and accepted/rejected/duplicate/conflict counts.
- `event_validation_errors`: stable validation/policy error code records linked to event or batch.
- `event_source_refs`: source hashes/refs linked to accepted events and later facts/reports.
- `quarantine_records`: suspicious, conflicting, or policy-invalid submissions with reason code, payload hash, source metadata, review state, and non-export guarantee.
- `rate_limit_records`: durable key/IP/window counters for ledger endpoints. Use SQLite transaction semantics for first package; note Postgres atomic upsert as target direction.
- `intake_control`: global and scoped intake state with `enabled`, `degraded`, `status_only`, and `disabled` semantics plus reason/audit metadata.

**Route contract**
- Mount a new router from `api/endpoints/ledger.py` in `api/main.py` at `/api/v1/ledger/osrs`.
- Endpoints: `POST /events`, `POST /events/batch`, and `GET /status`.
- `GET /status` remains available under auth when intake is disabled and must report intake state without writing event payloads.
- Existing `/api/v1/plugin` endpoints remain legacy/local; they are not public CATHERBY-LIVE-01 readiness evidence.

**Frontend boundary**
- No UI implementation is included in CATHERBY-LIVE-01A.
- Any later admin/frontend package must depend on backend read models and a Loom design contract. Loom research named required operator surfaces; it did not define component specs, tokens, a11y states, motion, or microcopy.
## 5. Directory Structure (Keep Updated)
<!-- ID: directory_structure -->
Planned implementation touchpoints for CATHERBY-LIVE-01 are intentionally narrow:

```text
api/
  main.py                         # mount new ledger router only when package 01A implements it
  dependencies.py                 # shared DB/auth plus exact plugin ingest scope and ledger policy helpers
  endpoints/
    ledger.py                     # new ledger ingestion/status router
    plugin.py                     # existing legacy table-per-family router; not public ledger readiness
  schemas/
    ledger.py                     # new ledger envelope, batch, enum, response, validation contracts
    plugin.py                     # existing legacy payload schemas; only neighbor tests unless explicitly required
database/
  connection.py                   # migration runner remains source of local SQLite bootstrap
  models.py                       # forbidden in 01A unless a later ORM package is approved
  sql/
    013_live_event_ledger.sql     # additive local ledger migration
tests/
  test_live_event_ledger_schemas.py
  test_live_event_ledger_api.py
  test_api_dependencies.py
  test_plugin_schemas.py          # direct neighbor regression for legacy schema surface
web/                              # later admin packages only after Loom design contract
```

Managed planning docs live under `.scribe/docs/dev_plans/catherby_live_sensory_spine_2026_05_15/` and remain the execution contract until replaced by later managed updates.
## 6. Data & Storage
<!-- ID: data_storage -->
**Storage decision:** SQLite migration-first for CATHERBY-LIVE-01A, with managed Postgres as a future deployment target. Package tests must not require a hosted database.

**Why this path**
- `database/connection.py` is the current local migration runner and executes `database/sql/*.sql`.
- `database/models.py` is snapshot-era SQLAlchemy and does not currently own plugin or ledger tables.
- Existing plugin handlers assume `plugin_*` tables that migrations do not define; the first package must close this schema/runtime gap before any exporter or report work.

**Migration design rules**
- Add `database/sql/013_live_event_ledger.sql`; do not edit older migrations except for a documented blocker.
- Use append-only ledger tables and explicit unique constraints for idempotency.
- Keep payload storage separate from event metadata so retention/redaction/export can evolve later.
- Use stable string enums in storage for event family, validation status, privacy class, export eligibility, quarantine state, and intake state.
- Store token id/user id/IP/user agent/request id references without storing plaintext API keys or raw unsafe payloads in logs.
- Add cleanup/indexes for rate windows and event lookups needed by package tests.

**Postgres direction**
- Name constraints and columns so a later Postgres migration can preserve semantics.
- Do not introduce SQLAlchemy ORM ledger models in 01A. A later storage package may add an abstraction or ORM only after Crucible verifies the SQLite ledger contract and Blueprint updates this plan.
## 7. Testing & Validation Strategy
<!-- ID: testing_strategy -->
**Package verification policy**
- Run all tests named in the active task package.
- Run direct neighbor tests for modules imported by or importing modified files.
- Run import smoke for every modified Python module.
- Do not run the full suite unless the operator explicitly widens verification.

**Required first-package proof**
- Schema tests reject missing envelope fields, unsupported event families, oversized payload fields, stale/future timestamps, malformed source refs, and invalid privacy/export classes.
- API tests prove missing/invalid/revoked keys fail closed; exact plugin ingest scope passes; substring false positives fail; durable key/IP limits persist across dependency instances; disabled intake blocks event writes while status remains available.
- Storage tests prove migration creates ledger tables, idempotent duplicate replay returns the original accepted event, conflicting replay is quarantined or rejected without export eligibility, and quarantine records do not create accepted export rows.
- Neighbor tests preserve existing plugin schema behavior where not intentionally changed and update auth tests for exact scope semantics.

**Minimum commands for CATHERBY-LIVE-01A**
- `pytest tests/test_live_event_ledger_schemas.py -q`
- `pytest tests/test_live_event_ledger_api.py -q`
- `pytest tests/test_api_dependencies.py -q`
- `pytest tests/test_plugin_schemas.py -q`
- `python -c 'from api.schemas.ledger import CatherbyEventEnvelope, CatherbyEventBatch'`
- `python -c 'from api.endpoints.ledger import router'`
- `python -c 'from api.dependencies import require_plugin_key'`
- `python -c 'from api.main import app'`
## 8. Deployment & Operations
<!-- ID: deployment_operations -->
**Local development**
- CATHERBY-LIVE-01A must initialize and test against local SQLite via existing `DatabaseConnection` and `database/sql/*.sql` migrations.
- Package tests may create temporary SQLite databases and apply migrations, but must not require live managed Postgres.

**Hosted/public readiness**
- Public/plugin readiness remains BLOCKED until Sentinel-listed controls are implemented and verified: exact scope auth, persistent per-key/per-IP rate limiting, replay/idempotency, payload and batch caps, quarantine, backpressure/disable switch, privacy/export classes, source refs/hashes, and public/private route separation.
- Public host route separation is a later security package unless the operator explicitly pulls it into the first implementation wave. No package may claim marketplace/public readiness before that gate passes.

**Operations controls**
- Backpressure states are Catherby intake controls only. They must not start, stop, or manage RuneLite, Dungeon Crawl, Council agents, or local LLM processes.
- Audit records must include token/user refs, request id, source IP, result, reason code, counts/hashes, and operator action reason where applicable; plaintext keys and raw unsafe payloads must not appear in logs.
## 9. Open Questions & Follow-Ups
<!-- ID: open_questions -->
| Item | Owner | Status | Notes |
|------|-------|--------|-------|
| Should `plugin:ingest` become the only accepted scope after transitional support? | Blueprint/Sentinel | Open for post-01A hardening | 01A may accept exact `plugin` and `plugin:ingest`; public launch should prefer purpose-specific scopes. |
| What hosted reverse-proxy trust contract will provide source IP truth? | Sentinel/Forge | Later security package | Persistent per-IP limits need trusted proxy config before public host readiness. |
| Which raw payload fields require retention/redaction policy first? | Sentinel/Blueprint | Later privacy package | 01A separates payload storage and classification but does not define long-term retention. |
| Which derived observation shape should Dungeon Crawl consume? | Blueprint | Later mapping package | Must depend on accepted ledger and privacy/export classes; no raw event bypass. |
| Which admin telemetry components should Loom specify first? | Loom | Blocked until backend read models exist | Loom research is input only; design contract still required before Quill UI. |

Closed decision: first implementation package is ledger/auth/storage/idempotency first, not report UI, RuneLite exporter, or bank/chat/container telemetry.
## 10. References & Appendix
<!-- ID: references_appendix -->
**Managed research inputs**
- `.scribe/docs/dev_plans/catherby_live_sensory_spine_2026_05_15/SPEC_CATHERBY_LIVE_01.md`
- `.scribe/docs/dev_plans/catherby_live_sensory_spine_2026_05_15/research/RESEARCH_SYNTHESIS_CATHERBY_LIVE_01.md`
- `.scribe/docs/dev_plans/catherby_live_sensory_spine_2026_05_15/research/RESEARCH_CATHERBY_CURRENT_API_LEDGER_INVENTORY.md`
- `.scribe/docs/dev_plans/catherby_live_sensory_spine_2026_05_15/research/RESEARCH_RUNELITE_TELEMETRY_PRIOR_ART.md`
- `.scribe/docs/dev_plans/catherby_live_sensory_spine_2026_05_15/research/RESEARCH_CATHERBY_ADMIN_FRONTEND_BOUNDARY.md`
- `docs/security/security/2026-05-15_catherby-live-ingestion/report.md`

**Source evidence inspected for planning**
- `api/main.py`
- `api/endpoints/plugin.py`
- `api/schemas/plugin.py`
- `api/dependencies.py`
- `database/connection.py`
- `database/models.py`
- `database/sql/*.sql`
- `tests/test_plugin_schemas.py`
- `tests/test_api_dependencies.py`

**Review requirements**
- Sentinel review is required for packages that change auth, durable rate limiting, public/private route exposure, quarantine, privacy/export classes, or hosted public readiness.
- Arbiter review is required after implementation validation to ensure Forge stayed inside package boundaries.
- Crucible must give a package-specific PASS before any dependent Forge package can route.
