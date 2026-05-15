---
id: catherby_live_sensory_spine_2026_05_15-phase-plan
title: "\u2699\uFE0F Phase Plan \u2014 catherby_live_sensory_spine_2026_05_15"
doc_type: phase_plan
doc_name: phase_plan
category: engineering
status: ready
version: v1.0
last_updated: 2026-05-15 07:27:08 UTC
maintained_by: agent-20260515-071009-2c5bfb98
created_by: agent-20260515-071009-2c5bfb98
owners: []
related_docs: []
tags: []
summary: CATHERBY-LIVE-01 ordered phase plan with CATHERBY-LIVE-01A executable and
  later gates blocked by dependencies.
edit_trace:
  tool: manage_docs
  created_at: 2026-05-15 07:27:08 UTC
  created_via: frontmatter_update
  last_edited_at: 2026-05-15 07:27:08 UTC
  last_edited_by: agent-20260515-071009-2c5bfb98
  last_action: frontmatter_update
  stage: blueprint_ready
---

# ⚙️ Phase Plan — catherby_live_sensory_spine_2026_05_15
**Author:** Scribe
**Version:** Draft v0.1
**Status:** ready
**Last Updated:** 2026-05-15 06:42:06 UTC

> Execution roadmap for catherby_live_sensory_spine_2026_05_15.

---
## Phase Overview
<!-- ID: phase_overview -->
| Phase | Package / Gate | Goal | Routing Status | Key Proof |
|-------|----------------|------|----------------|-----------|
| Phase 0 | `CATHERBY-LIVE-01A` | Authenticated OSRS event ledger core: auth, storage, idempotency, durable limits, quarantine, caps, backpressure | READY for pre-implementation review, then Forge | Package tests, neighbor tests, import smoke, migration smoke |
| Phase 1 | `CATHERBY-LIVE-01B` | Public/private route separation and hosted-readiness hardening for intended ledger routes | NOT ROUTABLE until 01A Crucible PASS | Sentinel review plus route inventory tests |
| Phase 2 | `CATHERBY-LIVE-01C` | Derived advisory observation feed from accepted ledger events, with no Dungeon Crawl mutation | NOT ROUTABLE until 01A and 01B pass | Export/privacy tests and source-ref lineage tests |
| Phase 3 | Future RuneLite exporter | First exporter must be session + XP only using `GameStateChanged`, `GameTick`, and `StatChanged` | BLOCKED until ledger API is verified and plugin source root is inventoried | Java/plugin tests plus HTTP contract tests |
| Phase 4 | Future admin/frontend | Catherby telemetry ops UI/read models | BLOCKED until backend read models exist and Loom writes design contracts | Loom `DESIGN_SYSTEM`/`COMPONENT_SPECS`, Quill implementation tests |

Only `CATHERBY-LIVE-01A` is immediately executable from this Blueprint package. Later phases are ordered gates; they must not route until their dependencies and exact source inventories are satisfied.
## Phase 0 — CATHERBY-LIVE-01A Authenticated OSRS Event Ledger Core
<!-- ID: phase_0 -->
## Task Package: CATHERBY-LIVE-01A - authenticated_osrs_event_ledger_core

**APPROACH_SUMMARY**
- Goal: establish the ledger/auth/storage/idempotency spine before any RuneLite exporter, report UI, bank/chat/container telemetry, or Dungeon Crawl consumer exists.
- Files to modify: `api/schemas/ledger.py`, `api/endpoints/ledger.py`, `api/dependencies.py`, `api/main.py`, `database/sql/013_live_event_ledger.sql`, `tests/test_live_event_ledger_schemas.py`, `tests/test_live_event_ledger_api.py`, `tests/test_api_dependencies.py`.
- Files forbidden: RuneLite Java/plugin implementation, Dungeon Crawl consumer/adapter files, `web/**`, `database/models.py`, `core/report_builder.py`, `agents/report_agent.py`, README/public marketplace docs, generated instruction/config surfaces, and legacy plugin broad telemetry expansion.
- Out of scope: public/plugin readiness claim, hosted Postgres dependency, bank/inventory/equipment/chat/container telemetry, report generation, admin/frontend UI, local LLM process management, and direct Dungeon Crawl mutation/export.
- Verification plan: run package tests, direct neighbor tests, SQLite migration smoke, and import smoke for modified Python modules.

**Goal**
- Add the first Catherby live OSRS event ledger path with authenticated session/xp event ingestion, durable local storage, exact scope checks, persistent key/IP rate records, idempotency, payload hashing, caps, quarantine, validation errors, privacy/export classes, source refs, and backpressure state.

**Depends On**
- Wave 1 research synthesis ready.
- Sentinel security report accepted as blocking input.
- No prior Forge package dependency.

**Files to Read**
- `api/main.py`
- `api/endpoints/plugin.py`
- `api/schemas/plugin.py`
- `api/dependencies.py`
- `database/connection.py`
- `database/sql/004_auth_clans_tokens.sql`
- `database/sql/009_rate_limiting.sql`
- `database/sql/011_audit_log.sql`
- `tests/test_plugin_schemas.py`
- `tests/test_api_dependencies.py`
- `.scribe/docs/dev_plans/catherby_live_sensory_spine_2026_05_15/ARCHITECTURE_GUIDE.md`
- `docs/security/security/2026-05-15_catherby-live-ingestion/report.md`

**Files to Modify**
- `api/schemas/ledger.py` (new)
- `api/endpoints/ledger.py` (new)
- `api/dependencies.py`
- `api/main.py`
- `database/sql/013_live_event_ledger.sql` (new)
- `tests/test_live_event_ledger_schemas.py` (new)
- `tests/test_live_event_ledger_api.py` (new)
- `tests/test_api_dependencies.py`

**Files Forbidden**
- `api/endpoints/plugin.py` except read-only reference; do not expand legacy table-per-family endpoints.
- `api/schemas/plugin.py` except read-only neighbor reference.
- `database/models.py`
- `web/**`
- `core/report_builder.py`
- `agents/report_agent.py`
- RuneLite Java/plugin files or external plugin repos.
- Dungeon Crawl consumer/adapter files.
- README/public marketplace/plugin distribution docs.
- `.scribe/**` except implementation agents may append progress; do not edit managed planning docs unless routed back to Blueprint.

**Public Contracts / Signatures**
- `class EventFamily(str, Enum)` with first values `SESSION = "session"` and `XP = "xp"` only.
- `class PrivacyClass(str, Enum)` with at least `OPERATOR_PRIVATE`, `DERIVED_INTERNAL`, `PUBLIC_SAFE`, and `DUNGEON_CRAWL_EXPORTABLE`.
- `class ExportEligibility(str, Enum)` with at least `BLOCKED`, `SCRUB_REQUIRED`, and `EXPORTABLE`.
- `class CatherbyEventEnvelope(BaseModel)` requiring the envelope fields defined in `ARCHITECTURE_GUIDE` and forbidding unsupported first-package event families.
- `class CatherbyEventBatch(BaseModel)` with capped event list size and capped total serialized payload size.
- `class LedgerIngestResponse(BaseModel)` containing `status`, `event_id`, `idempotency_key`, `payload_hash`, `validation_status`, and optional `reason_code`.
- `def parse_token_scopes(scopes: str) -> set[str]` in `api/dependencies.py`.
- `async def require_plugin_ingest_key(...) -> dict` in `api/dependencies.py`, preserving fail-closed key behavior and requiring exact `plugin:ingest` or transitional exact `plugin` scope.
- `router` in `api/endpoints/ledger.py`, mounted by `api/main.py` at `/api/v1/ledger/osrs`.

**Implementation Constraints**
1. Add the SQLite migration first so route code cannot target tables that do not exist.
2. Keep schema validation deterministic; generate `payload_hash` from canonical JSON after validation and before storage.
3. Enforce first-package event-family allowlist: only `session` and `xp` are accepted.
4. Implement durable rate records keyed by token id plus source IP/window for ledger endpoints. Existing in-memory limiters are not readiness proof.
5. Enforce request/body/batch caps before durable accepted writes; policy-invalid submissions must create validation/quarantine records when safely capturable.
6. Idempotent duplicate replay with same idempotency key and same hash must return the original accepted event without a second accepted row.
7. Same idempotency key with different hash must reject or quarantine and must not create an exportable accepted row.
8. Disabled/status-only intake must reject write endpoints before DB-heavy payload work while `GET /status` remains authenticated and available.
9. Do not write plaintext API keys or raw unsafe payloads to application logs or audit records.
10. Do not claim public/plugin readiness; 01A only builds the core controls.

**Required Tests**
- Add `tests/test_live_event_ledger_schemas.py` for required envelope fields, session/xp family allowlist, unsupported family rejection, payload caps, timestamp skew, privacy/export enums, and source refs.
- Add `tests/test_live_event_ledger_api.py` for migration smoke, accepted event storage, idempotent replay, conflict quarantine/rejection, durable key/IP rate record behavior, disabled intake, batch caps, validation errors, and no export eligibility for quarantine.
- Update `tests/test_api_dependencies.py` to preserve missing/invalid/revoked key behavior, prove exact `plugin` and/or `plugin:ingest` scope acceptance, and prove substring false positives fail.
- Preserve `tests/test_plugin_schemas.py` as direct neighbor regression for the legacy schema module.

**Verification Commands**
- `pytest tests/test_live_event_ledger_schemas.py -q`
- `pytest tests/test_live_event_ledger_api.py -q`
- `pytest tests/test_api_dependencies.py -q`
- `pytest tests/test_plugin_schemas.py -q`
- `python -c 'from api.schemas.ledger import CatherbyEventEnvelope, CatherbyEventBatch'`
- `python -c 'from api.endpoints.ledger import router'`
- `python -c 'from api.dependencies import require_plugin_key, require_plugin_ingest_key, parse_token_scopes'`
- `python -c 'from api.main import app'`

**Acceptance Criteria**
- [ ] `/api/v1/ledger/osrs/events`, `/api/v1/ledger/osrs/events/batch`, and `/api/v1/ledger/osrs/status` exist and are mounted without removing existing snapshot routes.
- [ ] Missing, invalid, revoked, and insufficient-scope keys fail closed; substring scopes such as `my_plugin_api` and `readplugin` fail.
- [ ] Ledger tables initialize in local SQLite through the existing migration runner.
- [ ] Accepted session/xp events persist with event metadata, payload hash, privacy/export class, source refs, validation status, and token/source metadata.
- [ ] Duplicate replay returns the prior accepted event; conflicting replay is rejected or quarantined and non-exportable.
- [ ] Persistent per-key/per-IP rate records are used for ledger write endpoints.
- [ ] Payload and batch caps reject oversized submissions before accepted writes.
- [ ] Quarantine and validation error records exist for policy-invalid or conflicting submissions and are not exportable.
- [ ] Disabled/status-only intake blocks writes while authenticated status remains available.
- [ ] No RuneLite exporter, admin UI, report generation, or Dungeon Crawl mutation/export is implemented.

**Out of Scope**
- RuneLite Java/plugin implementation.
- Bank, inventory, equipment, collection log, quest/diary, combat achievement, activity, loot, chat, or container telemetry.
- Dungeon Crawl adapter/consumer code.
- Admin/frontend UI.
- Public marketplace readiness and public host route separation claims.
- Managed Postgres-only test requirements.

**Review Gate Impact**
- Security-sensitive: Sentinel review required after Forge because auth, rate limiting, quarantine, privacy/export, and public-readiness blockers are touched.
- High blast radius: Arbiter review required after Crucible PASS to confirm package boundaries and no readiness overclaim.
- Dependent packages are blocked until Crucible gives a package-specific PASS for CATHERBY-LIVE-01A.

**Handoff Notes**
- Forge: STOP if implementation requires files outside the modify list or a broader event-family scope.
- Crucible: validate every acceptance criterion with targeted tests and import smoke; coordinator verification is not a substitute.
- Sentinel: verify public/plugin readiness remains blocked unless all listed controls and public route separation are proven.
- Arbiter: review for blueprint adherence, additive migration safety, no duplicate ledger system, and no Dungeon Crawl authority drift.
## Phase 1+ — Dependent Packages And Gates
<!-- ID: phase_1 -->
## Task Package: CATHERBY-LIVE-01B - public_private_route_separation

**Goal**
- Prove hosted Catherby exposes only intended public/ledger surfaces and blocks private backend, docs/test, admin, local operator, and Council/runtime surfaces from anonymous public reachability.

**Depends On**
- `CATHERBY-LIVE-01A` Crucible PASS.
- Sentinel review of 01A findings.

**Files to Read**
- `web/main.py`
- `api/main.py`
- `web/middleware/security_headers.py`
- `web/middleware/admin.py`
- `docs/security/security/2026-05-15_catherby-live-ingestion/report.md`

**Files to Modify**
- `web/main.py`
- `api/main.py`
- `web/middleware/security_headers.py` only if route/CSP separation requires it
- `tests/test_public_route_separation.py` (new)

**Files Forbidden**
- Ledger schema/storage changes except bug fixes explicitly routed from 01A validation.
- RuneLite exporter files.
- Dungeon Crawl consumer files.
- Admin UI templates except access-control tests require read-only inspection.

**Public Contracts / Signatures**
- No public contract expansion beyond route exposure policy.
- Add route inventory test helpers only inside `tests/test_public_route_separation.py`.

**Implementation Constraints**
1. Do not remove local development access by accident; separate public-host exposure from local app startup behavior.
2. Public host mode must deny private `/api`, docs/OpenAPI, test routes, admin routes without auth, local operator pages, and Council/runtime surfaces.
3. Ledger ingestion/status routes may remain exposed only with required plugin auth.
4. Preserve existing admin auth checks.

**Required Tests**
- Anonymous public-mode route inventory denies private/test/docs/admin/runtime surfaces.
- Authenticated local/admin route tests remain valid.
- Ledger route auth still fails closed without key.

**Verification Commands**
- `pytest tests/test_public_route_separation.py -q`
- `pytest tests/test_live_event_ledger_api.py -q`
- `pytest tests/test_catherby_frontend_startup.py -q`
- `python -c 'from web.main import app'`
- `python -c 'from api.main import app'`

**Acceptance Criteria**
- [ ] Public-mode route inventory is explicit and tested.
- [ ] Anonymous users cannot reach private/admin/test/docs/runtime surfaces in public mode.
- [ ] Ledger routes remain authenticated and do not expose legacy plugin readiness.
- [ ] Sentinel PASS is required before any public/plugin readiness claim.

**Out of Scope**
- Marketplace release, RuneLite plugin code, admin UI redesign, Dungeon Crawl adapter.

**Review Gate Impact**
- Security-sensitive. Sentinel PASS required. Dependent packages blocked until Crucible and Sentinel both pass.

## Task Package: CATHERBY-LIVE-01C - derived_advisory_observation_feed

**Goal**
- Add a read-only advisory observation feed derived from accepted ledger events with source refs/hashes and privacy/export gating. This is Catherby output only; it does not implement Dungeon Crawl consumer mutation.

**Depends On**
- `CATHERBY-LIVE-01A` Crucible PASS.
- `CATHERBY-LIVE-01B` Sentinel PASS if public route exposure is involved.

**Files to Read**
- `api/endpoints/ledger.py`
- `api/schemas/ledger.py`
- `database/sql/013_live_event_ledger.sql`
- `core/report_builder.py` read-only reference
- `docs/security/security/2026-05-15_catherby-live-ingestion/report.md`

**Files to Modify**
- `api/schemas/ledger.py`
- `api/endpoints/ledger_observations.py` (new)
- `api/main.py`
- `database/sql/014_ledger_derived_observations.sql` (new)
- `tests/test_ledger_observations.py` (new)

**Files Forbidden**
- Dungeon Crawl consumer/adapter files.
- Local LLM process/config files.
- RuneLite exporter files.
- Admin/frontend UI files.
- `core/report_builder.py` unless Blueprint updates this plan.

**Public Contracts / Signatures**
- `class AdvisoryObservation(BaseModel)` with `observation_id`, `event_ids`, `source_refs`, `payload_hashes`, `privacy_class`, `export_eligibility`, `summary`, and `created_at`.
- `GET /api/v1/ledger/osrs/observations` returns only export-eligible advisory summaries.

**Implementation Constraints**
1. Consume only accepted, non-quarantined ledger events.
2. Preserve event id, payload hash, and source refs through every derived observation.
3. Do not expose raw payloads in advisory responses.
4. Do not mutate Dungeon Crawl state.

**Required Tests**
- Exportable observations include lineage fields.
- Non-exportable/quarantined events never appear.
- Endpoint is read-only and source-cited.

**Verification Commands**
- `pytest tests/test_ledger_observations.py -q`
- `pytest tests/test_live_event_ledger_api.py -q`
- `python -c 'from api.endpoints.ledger_observations import router'`
- `python -c 'from api.schemas.ledger import AdvisoryObservation'`

**Acceptance Criteria**
- [ ] Advisory feed exists only as Catherby read model/output.
- [ ] Every observation traces back to event ids, payload hashes, and source refs.
- [ ] No raw payload or Dungeon Crawl mutation is introduced.

**Out of Scope**
- Dungeon Crawl integration implementation.
- Report UI.
- LLM prompt/runtime changes.

**Review Gate Impact**
- Arbiter review required for authority-boundary adherence. Sentinel review required if privacy/export behavior changes.

## Future Gate: RuneLite Session/XP Exporter
- Not routable from this Blueprint package because no local RuneLite plugin source root was present in the inspected repo. Before Forge can implement, Lens must inventory the actual plugin source location and Blueprint must update this phase plan with exact Java files, tests, and Gradle commands.
- The first exporter must be session + XP only using `GameStateChanged`, `GameTick`, and `StatChanged`, async OkHttp, client-thread-safe UI handling, API-key config gate, and no network request when no API key is configured.
- Bank, inventory, equipment, chat, and container telemetry remain forbidden until a later Blueprint package after ledger controls and privacy/export policy are proven.

## Future Gate: Admin/Frontend Telemetry Operations
- Not routable to Quill until Loom writes a real `DESIGN_SYSTEM` plus relevant `COMPONENT_SPECS`, `INTERACTION_PATTERNS`, `A11Y_REQUIREMENTS`, and `VISUAL_HIERARCHY` for Catherby telemetry operations.
- Loom research is input only and is not the design contract.
- Quill must not implement admin telemetry UI from this phase plan alone.
## Milestone Tracking
<!-- ID: milestone_tracking -->
| Milestone | Target Date | Owner | Status | Evidence/Link |
|-----------|-------------|-------|--------|---------------|
| Research gate complete | 2026-05-15 | Atlas + Wave 1 specialists | Done | `RESEARCH_SYNTHESIS_CATHERBY_LIVE_01.md`; Sentinel report |
| Blueprint planning complete | 2026-05-15 | Blueprint | In review | `ARCHITECTURE_GUIDE.md`, `PHASE_PLAN.md`, `CHECKLIST.md` quality checks |
| Pre-implementation review | Next gate | Witness + Arbiter | Required | Full plan truth and intent review before Forge |
| `CATHERBY-LIVE-01A` Forge implementation | After pre-imp PASS | Forge | Blocked until review | Package-specific Scribe handoff and targeted tests |
| `CATHERBY-LIVE-01A` validation | After Forge | Crucible + Sentinel | Blocked until Forge | Crucible package PASS plus Sentinel security validation |
| Dependent packages | After 01A PASS | Atlas routing | Blocked | No dependent Forge routing without 01A Crucible PASS |

Routing rule: if `CATHERBY-LIVE-01A` lacks package-specific Crucible PASS, every dependent package remains forbidden to route.
## Retro Notes & Adjustments
<!-- ID: retro_notes -->
- Blueprint intentionally made only `CATHERBY-LIVE-01A` immediately executable because the first implementation must remove the ledger/auth/storage/idempotency landmine before exporter, reporting, frontend, or Dungeon Crawl mapping work.
- RuneLite exporter work is intentionally a future gate because the inspected repo does not contain a local plugin source root. The first exporter scope is still fixed: session + XP only.
- Admin/frontend implementation is intentionally blocked until Loom writes design contracts; the existing Loom artifact is research, not implementation authority.
- Any operator or review correction to package boundaries must update `ARCHITECTURE_GUIDE.md`, `PHASE_PLAN.md`, and `CHECKLIST.md` through `manage_docs` before implementation resumes.
