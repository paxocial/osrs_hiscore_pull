---
id: catherby_live_sensory_spine_2026_05_15-research-catherby-admin-frontend-boundary
title: "\U0001F52C Catherby Admin Frontend Boundary Research \u2014 catherby_live_sensory_spine_2026_05_15"
doc_type: RESEARCH_CATHERBY_ADMIN_FRONTEND_BOUNDARY
doc_name: RESEARCH_CATHERBY_ADMIN_FRONTEND_BOUNDARY
category: engineering
status: ready
version: '0.1'
last_updated: 2026-05-15 06:59:04 UTC
maintained_by: agent-20260515-064725-1b5cc64c
created_by: agent-20260515-064725-1b5cc64c
owners:
- loom
related_docs: []
tags:
- catherby
- frontend
- admin
- telemetry
- boundary
summary: Catherby hosted/admin frontend boundary research complete for Blueprint/Loom
  synthesis.
edit_trace:
  tool: manage_docs
  created_at: 2026-05-15 06:59:04 UTC
  created_via: frontmatter_update
  last_edited_at: 2026-05-15 06:59:04 UTC
  last_edited_by: agent-20260515-064725-1b5cc64c
  last_action: frontmatter_update
  stage: research
  work_item_id: RESEARCH-CATHERBY-ADMIN-FRONTEND-BOUNDARY-01
---

# 🔬 Catherby Admin Frontend Boundary Research — catherby_live_sensory_spine_2026_05_15
**Author:** Scribe
**Version:** v0.1
**Status:** ready
**Last Updated:** 2026-05-15 06:54:48 UTC

> Research for Catherby hosted/admin frontend boundary and future live telemetry operations UI.

---
## Executive Summary
<!-- ID: executive_summary -->
Catherby already has a hosted FastAPI web surface with session auth, public pages, API-token self-service, and a protected `/admin` area. The current admin UI is account/security oriented: dashboard counters, users, audit logs, rate-limit unblocking, clans, and read-only config. It does not yet expose the live telemetry operations surface required by `SPEC_CATHERBY_LIVE_01.md`.

The future Catherby website/admin should show live telemetry intake health, plugin/API-key client status, per-key/IP rate limiting, backpressure/disable state, event batches, recent validated/rejected events, quarantine review, payload hash/source-ref lineage, and derived reports. Those views must remain Catherby operational controls only. They must not connect to Council runtime controls, mutate Dungeon Crawl, or show raw unsafe payloads by default.

Research status: READY for Blueprint/Loom synthesis once this document quality-checks clean. This is not a design contract and contains no implementation changes.
## Research Scope
<!-- ID: research_scope -->
**Research Lead:** loom

**Investigation Window:** 2026-05-15 — 2026-05-15

**Focus Areas:**
- Existing hosted Catherby web/admin entrypoints, navigation, templates, CSS, auth, security headers, audit logging, and startup test coverage.
- Operator-visible live telemetry needs from `SPEC_CATHERBY_LIVE_01.md`: intake health, API keys, rate limits, quarantine, batches/events, payload hashes, derived reports, and disable/backpressure controls.
- Product boundary controls that keep Catherby as telemetry/evidence infrastructure and prevent Council runtime control or Dungeon Crawl mutation.
- Later frontend/design-contract requirements for Loom and implementation-package splitting for Blueprint.

**Dependencies & Constraints:**
- No implementation, code edits, tests, or commits were performed for this task.
- This report is frontend/product-surface research, not a Loom `DESIGN_SYSTEM` or component contract.
- Evidence is from current source only; no live browser/runtime validation was requested for this package.
- Current Scribe reminders mention unrelated active-phase scaffold blockers elsewhere; this research handoff depends on this document's own quality check.
## Findings
<!-- ID: findings -->
### Executive Finding
- **Summary:** Existing admin/frontend surfaces are usable as a Catherby-hosted operations shell, but they are not a live telemetry operations console yet.
- **Evidence:** The SPEC requires Catherby to be an authenticated append-only telemetry spine with validation, hashing, replay-safe records, derived facts/reports, and vetted observations to Dungeon Crawl (`SPEC_CATHERBY_LIVE_01.md:31-45`). The current admin dashboard shows user/clan/login counters only (`web/routes/admin.py:28-62`, `web/templates/admin/dashboard.html:4-43`).
- **Confidence:** High.

### Existing Admin Surface Inventory With File-Level Evidence
- **App shell:** `web/main.py` creates FastAPI app metadata for Catherby, mounts static files, adds security/session middleware, mounts existing API under `/api`, includes public/auth/profile/clan/job/webhook/compare/admin routers, initializes DB, and starts worker/scheduler (`web/main.py:29-91`).
- **Admin protection:** `web/middleware/admin.py` gates routes with `@require_admin`, checks the signed session user id and admin flag, logs denied admin access, and re-checks the DB for admin state (`web/middleware/admin.py:16-97`).
- **Security headers:** `SecurityHeadersMiddleware` adds HSTS, no-sniff, frame deny, CSP with `connect-src 'self'`, referrer policy, and disabled camera/mic/geolocation permissions (`web/middleware/security_headers.py:11-43`).
- **Global navigation:** `web/templates/base.html` exposes `API Tokens` to logged-in users and `Admin` only when the session carries `is_admin`; the same logic appears in desktop and mobile nav (`web/templates/base.html:38-49`, `web/templates/base.html:67-79`).
- **Admin navigation:** `web/templates/admin/base_admin.html` adds a secondary admin nav for Dashboard, Users, Audit Logs, Rate Limits, Clans, and Config (`web/templates/admin/base_admin.html:7-19`).
- **Dashboard:** Current admin overview counts total/active/locked users, clans, recent logins, and failed logins (`web/routes/admin.py:28-62`; `web/templates/admin/dashboard.html:9-34`).
- **Users:** Admin can search users and perform HTMX-backed enable/disable, grant/revoke admin, and unlock actions; actions are logged (`web/routes/admin.py:68-180`; `web/templates/admin/users.html:16-80`).
- **Audit logs:** Admin can filter audit logs by event type, optional user id, and time window; UI shows time, event type, user id, email, IP address, and user agent (`web/routes/admin.py:186-251`; `web/templates/admin/audit_logs.html:28-63`).
- **Rate limits:** Admin can view current `rate_limit_store` entries from the last hour and delete rows by IP address through an unblock action (`web/routes/admin.py:257-292`; `web/templates/admin/rate_limits.html:9-62`).
- **Clans:** Admin can view clans, owners, member counts, creation dates, and link to public clan detail (`web/routes/admin.py:298-324`; `web/templates/admin/clans.html:9-47`).
- **Config:** Admin can view environment, session/security settings, rate limits, password policy, account lockout, and feature flags; template labels it read-only (`web/routes/admin.py:330-376`; `web/templates/admin/config.html:4-76`).
- **API token self-service:** Logged-in users can issue/revoke scoped API tokens; plain token is shown once, storage uses token hash and lists label/scopes/created/last-used/revoked state (`web/routes/auth.py:142-177`; `web/services/auth.py:184-217`; `web/templates/auth_tokens.html:1-60`).
- **Audit service:** Auth, admin, and security events are written to `audit_log` with event type, user/email, IP, user-agent, JSON metadata, and UTC timestamp (`web/services/audit.py:53-174`).
- **Current startup tests:** Frontend tests cover public page rendering and TemplateResponse request-signature correctness, but do not cover admin pages or telemetry operations (`tests/test_catherby_frontend_startup.py:15-61`).

### Required Future Operator Views
- **Operations overview:** Intake enabled/disabled state, backpressure reason, latest accepted/rejected event time, intake throughput, validation error counts, quarantine count, batch lag, and downstream feed freshness. This maps to SPEC controls for auth, replay, idempotency, payload/batch caps, validation, quarantine, audit, backpressure, privacy/export classification, source refs, and payload hashes (`SPEC_CATHERBY_LIVE_01.md:106-119`).
- **Plugin/API-key clients:** Per-key owner, label, scopes, plugin/client identity, last seen, last accepted/rejected event, rate-limit state, revoked/disabled state, and safe key rotation. Current `/auth/tokens` is user self-service; hosted operations need an admin/client operations view without revealing token secrets after issue (`web/routes/auth.py:142-177`; `web/services/auth.py:184-217`).
- **Rate limits and backpressure:** Per-key and per-IP pressure, endpoint family, request counts, windows, threshold source, unblock/disable actions, and audit evidence. Current UI is IP-only and last-hour oriented (`web/routes/admin.py:257-292`).
- **Event batches:** Batch id, submitting key/client, received time, item count, accepted/rejected/duplicate/conflict counts, payload size, schema version, and replay/idempotency outcomes. Candidate storage includes `event_batches` and validation records (`SPEC_CATHERBY_LIVE_01.md:121-136`).
- **Recent events:** Event id, source event id, idempotency key, observed/received times, event family, player/session refs, plugin version, validation status, privacy/export class, payload hash, and source refs. These fields come from the candidate envelope (`SPEC_CATHERBY_LIVE_01.md:80-104`).
- **Quarantine review:** Rejected/suspicious submissions with stable error code, reason, source/client metadata, payload hash, scrubbed payload summary, review state, and audited operator action. Raw unsafe payload should require explicit drill-in and permission.
- **Payload hash and source-ref lineage:** Evidence view showing how accepted events, derived facts, reports, and report links preserve hashes/source refs. Required because the SPEC says hashes/source refs must survive derived facts/reports (`SPEC_CATHERBY_LIVE_01.md:118-119`).
- **Derived reports/facts:** Report job status, generated fact summaries, linked event ids/hashes, export eligibility, and failure reasons. Candidate storage names `derived_facts`, `report_jobs`, and `report_event_links` (`SPEC_CATHERBY_LIVE_01.md:133-135`).

### Forbidden Interactions And Boundary Controls
- **No Council runtime control:** The frontend/admin must not call `.council` runtime APIs, show Council process controls, start/stop agents, edit Council config, or impersonate orchestration controls. The SPEC explicitly forbids connecting Catherby frontend/admin web to Council controls (`SPEC_CATHERBY_LIVE_01.md:47-56`).
- **No Dungeon Crawl mutation:** Catherby remains telemetry, analytics, and advisory evidence only; it must expose vetted observations, not direct campaign mutations (`SPEC_CATHERBY_LIVE_01.md:37-45`, `SPEC_CATHERBY_LIVE_01.md:58-78`).
- **No raw RuneLite-to-Dungeon-Crawl path:** UI must reinforce that RuneLite sends to Catherby ingestion only, never directly to Dungeon Crawl (`SPEC_CATHERBY_LIVE_01.md:74-78`).
- **No raw unsafe payload exposure by default:** List/detail views should default to scrubbed summaries, hashes, schema metadata, privacy/export class, and source refs. Raw payload drill-in needs explicit privilege, warning, audit event, and copy/export controls.
- **No secret redisplay:** Admin/client views may show token id/label/hash prefix/last-used/revoked state, but not plaintext API keys after issue. Current user token UI already states the token is shown only once (`web/templates/auth_tokens.html:3-10`).
- **No ambiguous global disable:** Disable/backpressure controls must name Catherby intake scope, affected key/source/endpoint, reason, duration, and audit trail. They must not suggest disabling Dungeon Crawl, Council, or RuneLite itself.
- **No one-click destructive high-impact actions:** Quarantine release/drop, intake disable, client revoke, or report purge should require accessible confirmation, reason capture, and audit logging.

### Design-System / Front-End Risks For Later Loom Contract
- Current admin CSS has raw rem/px values and hardcoded status colors, while theme variables are only partial aliases (`web/static/css/admin.css:1-156`; `web/static/css/theme.css:1-28`). Later UI work needs token mapping before Quill implementation.
- Admin templates use inline styles for layout, forms, panels, and truncation (`web/templates/admin/dashboard.html:36-42`; `web/templates/admin/users.html:9-13`; `web/templates/admin/audit_logs.html:9-25`; `web/templates/admin/config.html:9-76`). This will make telemetry UI drift unless Loom defines reusable admin primitives.
- Admin tables are dense and operationally useful, but there is no admin-specific responsive table strategy in `admin.css`; global responsive CSS only handles topbar/drawer/main and some unrelated page layouts (`web/static/css/admin.css:73-98`; `web/static/css/theme.css:192-232`, `web/static/css/theme.css:1458-1475`).
- HTMX actions reload the page after user mutations and do not specify pending/disabled/error states or focus restoration (`web/templates/admin/users.html:52-75`). Telemetry operations will need explicit optimistic/pending/error contracts.
- Status badges combine colors and symbols/text, but later telemetry severity states need WCAG AA contrast, non-color meaning, screen-reader labels, and consistent vocabulary for accepted/rejected/quarantined/duplicate/conflict/backpressured.
- Current CSP allows HTMX from CDN and inline scripts/styles (`web/middleware/security_headers.py:27-35`); any richer admin UI should keep data fetches same-origin and avoid requiring wider connect/script permissions without security review.

### Accessibility / Responsive / Information-Density Concerns
- Operational tables must support keyboard navigation, clear focus, sortable/filterable columns, sticky context, and safe horizontal overflow on small screens.
- Mobile should prioritize status overview, active incidents, and safe action review rather than trying to compress all event columns into a card pile.
- 200 percent text scale must not hide action buttons, status badges, payload hash values, or confirmation controls.
- Hashes, IDs, IPs, and timestamps need copy affordances, truncation with full-value access, and accessible labels.
- Empty/loading/error states are primary admin states: no intake, no quarantined events, stale backend, disabled intake, schema mismatch, and rate-limit-store unavailable each need distinct copy and severity.
- Admin actions need visible confirmation result, no reliance on native `confirm()` alone for critical telemetry controls, and audit-reason capture for disable/release/revoke decisions.

### Blueprint Questions And Recommended Package Split
- **Question:** Which backend read models/endpoints are authoritative for telemetry admin views: direct DB-backed server-rendered routes, JSON endpoints consumed by HTMX, or a mixed approach?
- **Question:** Are API tokens sufficient for plugin keys, or should Blueprint introduce plugin-specific key/client records with scope, owner, disable state, and rate-limit attribution?
- **Question:** What is the exact safe raw-payload access policy: who can view, under what audit event, and what redaction/export classes apply?
- **Question:** Should backpressure/disable be global, per-key, per-source-adapter, per-event-family, or endpoint scoped?
- **Question:** Which derived report/fact objects are operator-facing first, and which remain backend-only evidence for Dungeon Crawl adapters?
- **Recommended split 1:** Backend telemetry ops read models and admin-safe routes for intake health, batch/event summaries, quarantine counts, and derived report lineage.
- **Recommended split 2:** Plugin/API-key operations package: client inventory, scope/disable/revoke/rotate flows, last-seen and rate-limit visibility.
- **Recommended split 3:** Intake/rate/backpressure package: operational overview, rate pressure, safe disable/backpressure actions, audit reasons.
- **Recommended split 4:** Event ledger/quarantine package: batches, recent events, scrubbed event detail, payload hash/source-ref lineage, quarantine review.
- **Recommended split 5:** Loom design contract package before UI implementation: admin density tokens, status vocabulary, table/detail components, action confirmations, a11y/responsive behavior, and microcopy.
## Technical Analysis
<!-- ID: technical_analysis -->
**Code Patterns Identified:**
- Server-rendered Jinja templates are the current frontend architecture, with HTMX used for admin mutations and form submissions rather than a client-side app shell (`web/templates/base.html:10-13`, `web/templates/admin/users.html:52-75`).
- Admin routes directly query SQLite-backed tables through `DatabaseConnection`, assemble context dictionaries, and return `TemplateResponse` (`web/routes/admin.py:40-62`, `web/routes/admin.py:205-251`, `web/routes/admin.py:262-276`).
- Current privileged admin actions mutate users and rate-limit rows from admin routes and log via `log_admin_action` (`web/routes/admin.py:118-180`, `web/routes/admin.py:279-292`, `web/services/audit.py:110-137`).
- Existing token operations are user scoped rather than admin scoped: issue, revoke, and list are under `/auth/tokens` and keyed by the current user id (`web/routes/auth.py:142-177`, `web/services/auth.py:184-217`).

**System Interactions:**
- Catherby web owns its own app surface and mounts existing API under `/api`; this is the correct place to expose Catherby telemetry operations, provided those operations remain same-origin Catherby endpoints (`web/main.py:67-79`).
- Admin role state currently travels through signed session values and is rechecked against `users` for admin route access (`web/middleware/admin.py:16-97`).
- Audit evidence is centralized in `audit_log`, so future telemetry operator actions should use the same trail or a deliberately extended audit table rather than isolated UI-only state (`web/services/audit.py:53-174`).
- The SPEC separates Catherby telemetry/advisory evidence from Dungeon Crawl authority; UI architecture should preserve that boundary at route naming, copy, permissions, and available actions (`SPEC_CATHERBY_LIVE_01.md:37-45`, `SPEC_CATHERBY_LIVE_01.md:58-78`).

**Risk Assessment:**
- **High:** If UI controls are named or wired as generic runtime controls, operators may confuse Catherby intake disable/backpressure with Council or Dungeon Crawl controls.
- **High:** Raw payload display can leak unsafe/private RuneLite-derived data unless default views are scrubbed and raw access is audited.
- **Medium:** Reusing current API tokens without plugin/client-specific metadata may make per-key telemetry operations hard to attribute.
- **Medium:** Existing direct DB-query route pattern may be acceptable for server-rendered admin pages, but Blueprint should define read-model boundaries before telemetry tables arrive.
- **Medium:** Current admin tables and inline styles may not survive telemetry scale, small screens, or accessibility requirements without a Loom contract.
## Recommendations
<!-- ID: recommendations -->
### Immediate Next Steps
- Blueprint should decide the telemetry admin backend contract before any UI work: read-model tables/views, route style, permissions, audit events, and same-origin delivery shape.
- Blueprint should explicitly separate Catherby intake/backpressure controls from Dungeon Crawl and Council runtime controls in architecture docs and package names.
- Sentinel findings should be merged before UI planning for raw payload access, token/key operations, quarantine review, and public-hosted exposure.
- Later Loom design-contract work should be required before Quill touches admin telemetry UI, because implementation will need status taxonomy, table/detail specs, tokens, confirmation flows, and accessibility rules.
- Crucible/Witness later should require at least startup/template tests for any new admin routes plus access-control tests for privileged operator views.

### Long-Term Opportunities
- Treat the telemetry admin as an operational cockpit inside Catherby: evidence-first, dense, auditable, and built around intake state rather than account-management vanity metrics.
- Build a lineage-first interaction model where every derived report/fact can be traced back to event ids, hashes, source refs, validation status, and privacy/export classification.
- Add a clear incident posture for hosted operations: disabled intake, degraded intake, rate pressure, quarantine spike, stale feed, and report generation failure.
- Keep public website/account-tracker navigation distinct from privileged telemetry operations, even if they share the same FastAPI/Jinja stack.
## Appendix
<!-- ID: appendix -->
- **References:**
  - `SPEC_CATHERBY_LIVE_01.md`
  - `web/main.py`
  - `web/routes/admin.py`
  - `web/routes/auth.py`
  - `web/templates/admin/base_admin.html`
  - `web/templates/admin/dashboard.html`
  - `web/templates/admin/users.html`
  - `web/templates/admin/audit_logs.html`
  - `web/templates/admin/rate_limits.html`
  - `web/templates/admin/clans.html`
  - `web/templates/admin/config.html`
  - `web/templates/base.html`
  - `web/templates/auth_tokens.html`
  - `web/static/css/admin.css`
  - `web/static/css/theme.css`
  - `web/middleware/admin.py`
  - `web/middleware/security_headers.py`
  - `web/services/audit.py`
  - `web/services/auth.py`
  - `tests/test_catherby_frontend_startup.py`
- **Attachments:** None. No screenshots, runtime traces, code changes, or test outputs were produced for this read-only research task.
