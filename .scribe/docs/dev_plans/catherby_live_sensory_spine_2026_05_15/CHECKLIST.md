---
id: catherby_live_sensory_spine_2026_05_15-checklist
title: "\u2705 Acceptance Checklist \u2014 catherby_live_sensory_spine_2026_05_15"
doc_type: checklist
doc_name: checklist
category: engineering
status: ready
version: v1.0
last_updated: 2026-05-15 09:13:22 UTC
maintained_by: agent-20260515-090040-ba9972e8
created_by: agent-20260515-071009-2c5bfb98
owners: []
related_docs: []
tags: []
summary: CATHERBY-LIVE-01 checklist mirroring package IDs and gates.
edit_trace:
  tool: manage_docs
  created_at: 2026-05-15 07:27:23 UTC
  created_via: frontmatter_update
  last_edited_at: 2026-05-15 09:13:22 UTC
  last_edited_by: agent-20260515-090040-ba9972e8
  last_action: replace_text
  stage: blueprint_ready
---

# ✅ Acceptance Checklist — catherby_live_sensory_spine_2026_05_15
**Author:** Scribe
**Version:** v0.1
**Status:** ready
**Last Updated:** 2026-05-15 06:42:06 UTC

> Acceptance checklist for catherby_live_sensory_spine_2026_05_15.

---
## Documentation Hygiene
<!-- ID: documentation_hygiene -->
- [x] `ARCHITECTURE_GUIDE.md` contains `APPROACH_SUMMARY`, source-backed architecture decisions, storage path, route boundary, testing strategy, and security constraints.
- [x] `PHASE_PLAN.md` contains ordered packages/gates with `CATHERBY-LIVE-01A` as the first executable package.
- [x] `CHECKLIST.md` mirrors package IDs and gate items for auditability.
- [x] `ARCHITECTURE_GUIDE.md`, `PHASE_PLAN.md`, and `CHECKLIST.md` frontmatter/status updated to ready through `manage_docs(frontmatter_update)`.
- [x] `quality_check` passes for `architecture`, `phase_plan`, and `checklist` with zero blocking scaffold warnings.
## Phase 0
<!-- ID: phase_0 -->
### `CATHERBY-LIVE-01A` Checklist
- [x] Forge reads the required inputs and modifies only the files listed in `PHASE_PLAN.md` for `CATHERBY-LIVE-01A`.
- [x] `api/schemas/ledger.py` defines event envelope, batch, response, family, privacy, and export contracts for session/xp only.
- [x] `api/endpoints/ledger.py` exposes authenticated `/api/v1/ledger/osrs/events`, `/events/batch`, and `/status` routes.
- [x] `api/dependencies.py` preserves fail-closed key behavior and adds exact delimiter-aware ingest scope checks; substring false positives fail.
- [x] `database/sql/013_live_event_ledger.sql` creates local SQLite ledger tables for events, payloads, batches, validation errors, source refs, quarantine, durable rate records, and intake control.
- [x] Accepted events store payload hash, validation status, privacy/export class, source refs, token/user refs, and source metadata.
- [x] Duplicate replay with same idempotency key and hash returns the original accepted event; conflicting replay rejects or quarantines without export eligibility.
- [x] Persistent per-key/per-IP ledger rate records are used; in-memory limiters are not treated as readiness proof.
- [x] Payload and batch caps reject oversized submissions before accepted writes.
- [x] Disabled/status-only intake rejects writes while authenticated status remains available.
- [x] No RuneLite exporter, admin UI, report generation, public marketplace claim, or Dungeon Crawl mutation/export is implemented.
- [x] Required verification commands pass: `pytest tests/test_live_event_ledger_schemas.py -q`, `pytest tests/test_live_event_ledger_api.py -q`, `pytest tests/test_api_dependencies.py -q`, `pytest tests/test_plugin_schemas.py -q`, and all listed import smokes.
- [x] Crucible gives package-specific PASS before `CATHERBY-LIVE-01B`, `CATHERBY-LIVE-01C`, RuneLite exporter, admin/frontend, or Dungeon Crawl mapping routes.
## Phase 1
<!-- ID: phase_1 -->
### `CATHERBY-LIVE-01B` Checklist
- [x] `CATHERBY-LIVE-01A` has package-specific Crucible PASS before routing.
- [x] Public/private route inventory is explicit and tested in `tests/test_public_route_separation.py`.
- [x] Anonymous public mode cannot reach private backend APIs, docs/OpenAPI, test routes, admin routes, local operator pages, or Council/runtime surfaces.
- [x] Ledger ingestion/status routes remain authenticated and do not claim legacy `/api/v1/plugin` readiness.
- [x] Sentinel gives PASS before any public/plugin readiness claim. PASS is scoped to CATHERBY-LIVE-01B route separation only; broader public/plugin readiness remains blocked by the Sentinel security report.

### `CATHERBY-LIVE-01C` Checklist
- [x] `CATHERBY-LIVE-01A` has package-specific Crucible PASS before routing.
- [ ] Advisory observations are derived only from accepted, non-quarantined ledger events.
- [ ] Every advisory observation preserves event ids, payload hashes, source refs, privacy class, and export eligibility.
- [ ] Advisory feed is read-only and does not mutate Dungeon Crawl or local LLM state.
- [ ] Sentinel or Arbiter confirms privacy/export and authority boundaries before any Dungeon Crawl adapter package.
## Phase 2
<!-- ID: phase_2 -->
### Future RuneLite Exporter Gate
- [ ] Lens inventories the actual RuneLite plugin source root before Forge receives exporter work.
- [ ] Blueprint updates `PHASE_PLAN.md` with exact Java files, forbidden files, Gradle/test commands, and API contract references before exporter implementation.
- [ ] First exporter scope is session + XP only: `GameStateChanged`, `GameTick`, and `StatChanged`.
- [ ] Plugin has an API-key config gate and sends no network request when no API key is configured.
- [ ] Bank, inventory, equipment, chat, collection-log, and container telemetry remain forbidden until a later package.

### Future Admin/Frontend Gate
- [ ] Backend read models exist before UI implementation planning.
- [ ] Loom writes `DESIGN_SYSTEM` and relevant `COMPONENT_SPECS` before Quill implementation.
- [ ] Quill does not implement telemetry admin UI from research docs or Blueprint prose alone.
- [ ] UI remains Catherby operations only: no Council runtime controls and no Dungeon Crawl mutation controls.
## Final Verification
<!-- ID: final_verification -->
- [ ] Witness verifies managed docs exist, contain real content, and match the claimed package boundary.
- [ ] Arbiter intent review passes before Forge starts `CATHERBY-LIVE-01A`.
- [ ] Forge implementation remains blocked until pre-implementation review passes or the operator explicitly waives that gate.
- [ ] After Forge, Crucible runs package-specific validation for `CATHERBY-LIVE-01A`; dependent Forge routing remains blocked until PASS.
- [ ] Sentinel reviews auth/rate/idempotency/quarantine/privacy/public-readiness controls before any public/plugin readiness claim.
- [ ] No code edits, source tests, git commits, or implementation changes were performed by Blueprint in this planning package.
