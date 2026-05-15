---
id: catherby_live_sensory_spine_2026_05_15-research-synthesis-catherby-live-01
title: "\U0001F52C CATHERBY-LIVE-01 Research Synthesis \u2014 catherby_live_sensory_spine_2026_05_15"
doc_type: RESEARCH_SYNTHESIS_CATHERBY_LIVE_01
doc_name: RESEARCH_SYNTHESIS_CATHERBY_LIVE_01
category: engineering
status: ready
version: '0.1'
last_updated: 2026-05-15 07:08:08 UTC
maintained_by: agent-20260515-020223-e707f87e
created_by: agent-20260515-020223-e707f87e
owners: []
related_docs: []
tags: []
summary: 'Wave 1 research synthesis for CATHERBY-LIVE-01: research ready for Blueprint,
  implementation blocked until ledger-first architecture and task packages exist.'
edit_trace:
  tool: manage_docs
  created_at: 2026-05-15 07:04:19 UTC
  created_via: replace_section
  last_edited_at: 2026-05-15 07:08:08 UTC
  last_edited_by: agent-20260515-020223-e707f87e
  last_action: frontmatter_update
---

# 🔬 CATHERBY-LIVE-01 Research Synthesis — catherby_live_sensory_spine_2026_05_15
**Author:** Scribe
**Version:** v0.1
**Status:** ready
**Last Updated:** 2026-05-15 07:03:55 UTC

> Synthesis of Catherby current-state, security, RuneLite prior-art, and admin/frontend boundary research for Blueprint routing.

---
## Executive Summary
<!-- ID: executive_summary -->
Wave 1 research confirms the product direction and blocks premature implementation. Catherby should become the live OSRS telemetry ledger, but the repo is currently a hiscore/snapshot app with a partial plugin API and admin shell. The existing pieces are useful; they are not enough for public/plugin traffic or Dungeon Crawl evidence export.

Key takeaways:

- The existing `/api/v1/plugin` surface is real but snapshot-era and table-per-family, not a unified append-only event ledger.
- Missing plugin API keys fail closed today, but hosted/public readiness is blocked by missing durable rate limits, exact scopes, replay/idempotency, payload caps, quarantine, backpressure, privacy/export classes, and public/private route separation.
- External RuneLite prior art points to a narrow first nerve: session plus XP from `GameStateChanged`, `GameTick`, and `StatChanged`.
- Bank, inventory, equipment, collection log, and chat are valid later telemetry families, not first-package scope.
- Catherby admin/frontend can become the operations console for ingestion health, API clients, rate pressure, event batches, quarantine, lineage, and backpressure, but it must never control Council runtime or mutate Dungeon Crawl authority.

Research gate result: READY for Blueprint planning. Implementation gate result: BLOCKED until Blueprint produces architecture, phase plan, checklist, task packages, and an `APPROACH_SUMMARY`.
## Research Scope
<!-- ID: research_scope -->
This synthesis combines the completed Wave 1 research artifacts for `CATHERBY-LIVE-01`:

- `SPEC_CATHERBY_LIVE_01.md`
- `research/RESEARCH_CATHERBY_CURRENT_API_LEDGER_INVENTORY.md`
- `research/RESEARCH_RUNELITE_TELEMETRY_PRIOR_ART.md`
- `research/RESEARCH_CATHERBY_ADMIN_FRONTEND_BOUNDARY.md`
- `docs/security/security/2026-05-15_catherby-live-ingestion/report.md`

The goal is not to design implementation. The goal is to hand Blueprint a single source-backed gate summary: what is known, what is blocked, and what the first architecture package must decide before Forge or Quill can touch code.

## Synthesis Verdict

Research is READY for Blueprint.

Implementation is NOT READY.

Catherby already contains useful plugin/auth/schema/admin ingredients, but the live sensory spine requires a new append-only event ledger contract. The existing `/api/v1/plugin` API is table-per-family and snapshot-era. It has Pydantic schemas, `X-API-Key` auth, process-local rate limiters, and route handlers, but it lacks ledger-wide idempotency, payload hashes, durable replay handling, quarantine, payload and batch caps, privacy/export classes, backpressure, and persistent per-key/per-IP rate limiting.

Blueprint must therefore design ledger-first ingestion. The first implementation package should not be reporting, bank telemetry, public marketplace distribution, or frontend polish. The first package should establish storage truth and the authenticated event envelope for a narrow session/XP nerve.
## Findings
<!-- ID: findings -->
### Finding 1: Existing plugin API is real but not the ledger

- **Summary:** `/api/v1/plugin` exists with many handlers plus batch/status, but it writes table-per-family records and does not model the unified live event envelope.
- **Evidence:** `RESEARCH_CATHERBY_CURRENT_API_LEDGER_INVENTORY.md` maps `api/main.py`, `api/endpoints/plugin.py`, `api/schemas/plugin.py`, and `api/dependencies.py` as the current surface. It also reports that route handlers write to `plugin_*` tables that are not present in `database/sql/*.sql` migrations.
- **Confidence:** High.

### Finding 2: Security blocks public/plugin traffic until first-class controls exist

- **Summary:** Missing API keys fail closed today, but the ingestion boundary is not public-ready. Persistent per-key/per-IP limits, exact scopes, replay/idempotency, payload/batch caps, quarantine, backpressure, privacy/export classes, and public/private route separation are mandatory before marketplace or public plugin posture.
- **Evidence:** `docs/security/security/2026-05-15_catherby-live-ingestion/report.md` gives a BLOCK verdict for public/plugin readiness and records `pytest -q tests/test_api_dependencies.py::TestRequirePluginKey` -> 8 passed, 1 warning.
- **Confidence:** High.

### Finding 3: First RuneLite nerve should be session + XP, not bank/chat/inventory

- **Summary:** External prior art points to a low-noise first exporter based on `GameStateChanged`, `GameTick`, and `StatChanged`: login baseline, XP dirty marking, logout/hop flush. Bank, equipment, inventory, collection log, and chat are valid later waves but too broad/privacy-sensitive for the first proof.
- **Evidence:** `RESEARCH_RUNELITE_TELEMETRY_PRIOR_ART.md` cites Wise Old Man, WikiSync, Bank Value, RuneLite core, and example plugins. It recommends session plus XP as the safe first exporter family.
- **Confidence:** High.

### Finding 4: Catherby admin can host ops views, but not Council controls

- **Summary:** Existing FastAPI/Jinja admin pages can become an operational Catherby console, but they currently show account/admin metrics, not live ingestion health. Future UI must expose intake state, API clients, rate pressure, event batches, recent events, hashes/source refs, quarantine, derived report lineage, and backpressure while explicitly forbidding Council runtime control and direct Dungeon Crawl mutation.
- **Evidence:** `RESEARCH_CATHERBY_ADMIN_FRONTEND_BOUNDARY.md` inventories `web/main.py`, `web/routes/admin.py`, admin templates, auth tokens, audit services, and frontend risks.
- **Confidence:** High.

### Finding 5: Storage authority must be resolved before implementation

- **Summary:** Runtime storage currently mixes SQLite migrations, SQLAlchemy snapshot models, and plugin handlers that assume undocumented `plugin_*` tables. Ledger implementation must choose a storage truth and first migration path before route code writes events.
- **Evidence:** Current inventory identifies `database/connection.py` as SQLite migration runner, `database/models.py` as snapshot-era ORM only, and `database/sql/*.sql` as lacking current plugin table definitions.
- **Confidence:** High.
## Technical Analysis
<!-- ID: technical_analysis -->
### Blueprint Must Decide

- Whether to preserve `/api/v1/plugin` as the ingestion prefix or introduce `/api/v1/events/osrs` while leaving current snapshot-era plugin endpoints untouched/deprecated.
- Whether `api_tokens` remains the plugin-key store or a dedicated plugin client/key table is introduced.
- Exact scope semantics: delimiter-aware `plugin` or a new `plugin:ingest`, never substring matching.
- Storage authority for the first package: SQLite migration-first local path, Postgres-compatible DDL, SQLAlchemy models, or a deliberate mixed bridge.
- The first event-envelope schema and stable validation error codes.
- Idempotency behavior for duplicate accepted events and same-key/different-hash conflicts.
- Quarantine lifecycle and whether invalid payloads are captured before or after Pydantic validation.
- Backpressure/disable state model: global, per key, per source adapter, per event family, or endpoint scoped.
- Public/private route split for hosted Catherby, including whether public web mounts backend `/api` at all.
- Future admin UI scope and required Loom design-contract work before Quill implementation.

### Recommended Blueprint Direction

- Ledger-first, session/XP-first.
- Keep bank, inventory, equipment, chat, collection-log, and broad activity telemetry out of the first implementation package.
- Treat the existing plugin API as reusable evidence, not as the final shape.
- Put the first hard boundary around auth, event envelope, storage, idempotency, validation, and tests.
- Delay frontend UI until backend ledger read models and operator actions exist; then route through Loom and Quill.

### Implementation Readiness Gate

Forge must not start until Blueprint produces:

- `APPROACH_SUMMARY`.
- File ownership and forbidden-file lists.
- Exact first package acceptance criteria.
- Verification commands for package tests, neighbor tests, and import smoke.
- Security controls from Sentinel translated into package-level requirements.
- Explicit non-goals: no RuneLite exporter yet, no public marketplace claim, no bank/chat/container telemetry, no Dungeon Crawl raw bypass.

### Likely First Package Shape For Blueprint To Refine

A plausible first package is `CATHERBY-LIVE-01A: Authenticated OSRS Event Ledger Core`:

- Own `api/schemas/plugin.py` or a new schema module if Blueprint chooses a new event-envelope surface.
- Own `api/endpoints/plugin.py` or a new events endpoint module if Blueprint chooses a new route.
- Own `api/dependencies.py` for exact plugin scope semantics and policy hooks.
- Own one migration under `database/sql/` for ledger tables and constraints.
- Own tests for schema validation, auth exact-scope behavior, idempotency, replay conflict, payload caps, quarantine/non-export, and route-level storage.

Blueprint must confirm exact files. This synthesis does not authorize implementation.
## Recommendations
<!-- ID: recommendations -->
### Immediate Next Steps

1. Route Blueprint to produce the CATHERBY-LIVE-01 architecture and phase plan from the SPEC plus four research artifacts plus this synthesis.
2. Require Blueprint `APPROACH_SUMMARY` before any Forge/Quill implementation.
3. Require the first task package to remove the storage/auth/idempotency landmine before any RuneLite exporter work.
4. Treat Sentinel's public/plugin readiness BLOCK as a planning constraint, not a reason to stop.
5. Keep `.scribe/` artifacts force-added explicitly because this repo ignores Scribe docs by default.

### Blueprint Must Preserve

- Catherby is telemetry/advisory evidence, not Dungeon Crawl authority.
- RuneLite plugin never sends raw events directly to Dungeon Crawl.
- No API key in plugin settings means no network request is sent.
- First nerve is session/XP only unless Blueprint proves another first slice is safer.
- Existing hiscore snapshots remain supplemental background metadata.
- Public/plugin distribution remains blocked until security controls land and verify.
- Catherby admin/frontend is Catherby-hosted operations UI only, not Council runtime UI.

### Long-Term Opportunities

- Event ledger plus typed derived views can replace the table-per-family plugin shape without throwing away snapshot/reporting history.
- WikiSync-style manifest/delta negotiation can become a later authenticated feature negotiation path.
- Bank/equipment/inventory telemetry can become a second-wave exporter once payload caps, privacy classes, quarantine, and operator visibility exist.

## Appendix
<!-- ID: appendix -->

### Research Artifacts

- `.scribe/docs/dev_plans/catherby_live_sensory_spine_2026_05_15/SPEC_CATHERBY_LIVE_01.md`
- `.scribe/docs/dev_plans/catherby_live_sensory_spine_2026_05_15/research/RESEARCH_CATHERBY_CURRENT_API_LEDGER_INVENTORY.md`
- `.scribe/docs/dev_plans/catherby_live_sensory_spine_2026_05_15/research/RESEARCH_RUNELITE_TELEMETRY_PRIOR_ART.md`
- `.scribe/docs/dev_plans/catherby_live_sensory_spine_2026_05_15/research/RESEARCH_CATHERBY_ADMIN_FRONTEND_BOUNDARY.md`
- `docs/security/security/2026-05-15_catherby-live-ingestion/report.md`

### Verification Evidence

- All four specialist outputs were verified by Atlas with `read_file` scans and Scribe `quality_check`.
- Sentinel reported `pytest -q tests/test_api_dependencies.py::TestRequirePluginKey` -> 8 passed, 1 warning.
- This synthesis must quality-check clean before Blueprint routing.
