---
id: catherby_live_sensory_spine_2026_05_15-catherby-live-01b-public-route-gate
title: "\U0001F512 CATHERBY-LIVE-01B Sentinel Public Route Security Gate \u2014 catherby_live_sensory_spine_2026_05_15"
doc_type: catherby-live-01b-public-route-gate
doc_name: catherby-live-01b-public-route-gate
category: engineering
status: ready
version: '0.1'
last_updated: 2026-05-15 09:12:21 UTC
maintained_by: agent-20260515-090040-ba9972e8
created_by: agent-20260515-090040-ba9972e8
owners: []
related_docs: []
tags: []
summary: Sentinel PASS for CATHERBY-LIVE-01B route-separation gate only; broader public/plugin
  readiness remains blocked.
verdict: PASS
gate: CATHERBY-LIVE-01B
edit_trace:
  tool: manage_docs
  created_at: 2026-05-15 09:12:21 UTC
  created_via: frontmatter_update
  last_edited_at: 2026-05-15 09:12:21 UTC
  last_edited_by: agent-20260515-090040-ba9972e8
  last_action: frontmatter_update
---

# 🔒 CATHERBY-LIVE-01B Sentinel Public Route Security Gate — catherby_live_sensory_spine_2026_05_15
**Author:** Scribe
**Version:** v0.1
**Status:** ready
**Last Updated:** 2026-05-15 09:08:06 UTC

> Sentinel follow-up security gate for CATHERBY-LIVE-01B public/private route separation after Forge implementation and Crucible PASS.

---
## Security Overview
<!-- ID: security_overview -->
**Verdict: PASS for `CATHERBY-LIVE-01B` Sentinel gate only.**

This PASS is narrow. It permits moving past the 01B security follow-up gate for public/private route separation after Forge implementation `c5b7ef2` and Crucible PASS. It does **not** grant RuneLite marketplace readiness, public plugin readiness, public user readiness, or deployment readiness for `catherby.net`.

**Blocking findings for 01B:** none found.

**Still blocked outside 01B:** broader public/plugin readiness remains blocked by the prior Sentinel report at `docs/security/security/2026-05-15_catherby-live-ingestion/report.md`, including durable production-safe rate limiting, replay/idempotency guarantees, payload/body caps, quarantine lifecycle, backpressure/disable controls, privacy/export classification, and deployment/reverse-proxy proof.

**Severity:** High before public exposure. The specific 01B route-separation vulnerability is remediated for the tested in-process FastAPI surfaces when `CATHERBY_PUBLIC_HOST_MODE=true` is set before module import.
## Description
<!-- ID: description -->
### Summary

CATHERBY-LIVE-01B remediates the public-host route mixing risk identified in the prior Sentinel ingestion report. The vulnerable condition was that the hosted web app mounted the backend API under `/api` while private backend, docs/test, admin, local operator, and Council/runtime-like paths were not explicitly separated from anonymous public traffic.

### Expected Behaviour

When `CATHERBY_PUBLIC_HOST_MODE=true` is set before import:

- Direct API public mode denies anonymous access to `/docs`, `/redoc`, `/openapi.json`, `/test`, `/accounts`, `/snapshots`, `/analytics`, and legacy `/api/v1/plugin` paths.
- Mounted web public mode denies private `/api` paths except authenticated ledger, plus `/admin`, `/jobs`, `/webhooks`, `/operator`, `/ops`, `/runtime`, `/council`, and local dot-runtime-like prefixes.
- Ledger routes remain mounted but fail closed without a valid `X-API-Key` carrying plugin/plugin:ingest authority.
- Default local mode keeps existing docs, legacy plugin auth behavior, and admin auth behavior available for local/operator use.

### Actual Behaviour

Verified behaviour matches the expected 01B gate. In public mode, direct API forbidden paths returned 404, mounted web forbidden paths returned 404, ledger status returned 401 without a key, and no forbidden direct API public-mode route registrations remained. In default mode, API docs returned 200, legacy plugin status remained auth-gated with 401, mounted plugin status remained auth-gated with 401, `/admin` redirected normally to `/admin/`, and `/admin/` returned 401 without a session.

### Steps to Reproduce

1. Set `CATHERBY_PUBLIC_HOST_MODE=true` before importing `api.main` and `web.main`.
2. Create `TestClient` instances for direct API and mounted web apps.
3. Request docs/openapi/test/account/snapshot/analytics/legacy-plugin/admin/operator/runtime/Council-like paths anonymously.
4. Confirm those paths return 404 while `/api/v1/ledger/osrs/status` and `/api/api/v1/ledger/osrs/status` return 401 without `X-API-Key`.
5. Unset `CATHERBY_PUBLIC_HOST_MODE`, reload modules, and confirm default local docs/plugin/admin auth behavior remains intact.
## Affected Systems
<!-- ID: affected_systems -->
**Affected Areas:**

- `api/main.py` direct FastAPI app construction, documentation URLs, and router registration.
- `web/main.py` mounted web app, public surface guard, and `/api` mount boundary.
- `api/endpoints/ledger.py` ledger ingestion/status routes.
- `api/dependencies.py` plugin/API-key auth dependency.
- `tests/test_public_route_separation.py` public/private route regression coverage.

**Threat Analysis:**

The relevant trust boundary is anonymous internet traffic hitting a hosted Catherby web/API process. Without explicit public-host separation, visitors could discover or reach internal backend routes, OpenAPI documentation, test routes, legacy plugin endpoints, admin paths, local operator paths, or Council/runtime-like surfaces through the hosted web mount.

**Attack Vector:** Network/public HTTP.

**Vulnerability:** Prior to 01B, public-host route separation was unresolved. The web app mounted `api_app` under `/api`, and the public deployment boundary relied on older local/default routes rather than an explicit public-host allow/deny policy.

**Impact:** Accidental exposure of private API surface area, documentation/openapi schema, local/admin/operator controls, and legacy plugin readiness paths. The highest risk was readiness confusion and mixed public/private authority rather than a confirmed anonymous ledger-auth bypass.
## Investigation
<!-- ID: investigation -->
**Root Cause Analysis:**

The route-mixing risk came from two older assumptions colliding with hosted public use: the backend API was mounted into the web app for convenience, and local/default routes were suitable for operator development but not for anonymous public hosting. CATHERBY-LIVE-01B adds a first-class public-host mode instead of weakening default local behavior.

**Findings:**

- `api/main.py` sets `docs_url`, `redoc_url`, and `openapi_url` to `None` in public mode and conditionally excludes test/accounts/snapshots/analytics/runelite/legacy-plugin routers.
- `api/main.py` keeps `ledger.router` mounted at `/api/v1/ledger/osrs` in all modes.
- `api/endpoints/ledger.py` uses `Depends(require_plugin_ingest_key)` for `/events`, `/events/batch`, and `/status`.
- `api/dependencies.py` fails missing/invalid keys closed with 401 and rejects tokens without exact `plugin` or `plugin:ingest` scope with 403.
- `web/main.py` installs a public-mode guard before routing that denies private `/api` paths except ledger, plus admin/jobs/webhooks/operator/ops/runtime/council and local dot-runtime-like prefixes.
- The implementation does not remove default-mode docs, legacy plugin auth behavior, or admin auth behavior.

**Privacy and Compliance Impact:**

This 01B gate does not newly expose sensitive user telemetry. It reduces accidental anonymous exposure of private API and local/operator surfaces. Broader telemetry privacy/export controls remain unresolved outside 01B and still block public/plugin readiness.

**Nonblocking Risks:**

- `CATHERBY_PUBLIC_HOST_MODE` is evaluated at import/app-construction time. Deployment must set it before importing `api.main` or `web.main`.
- The web app still mounts backend API under `/api`; the public guard passed the in-process probes, but reverse-proxy deny rules remain useful defense in depth.
- The direct API root still returns informational links that include old docs/accounts/snapshots/analytics names, but those linked paths return 404 in public mode. Treat this as documentation polish, not an exposure blocker for 01B.
## Resolution Plan
<!-- ID: resolution_plan -->
### Immediate Actions

Completed by Forge in `c5b7ef2 feat: gate catherby public routes`:

- Added `CATHERBY_PUBLIC_HOST_MODE` handling in `api/main.py`.
- Disabled direct API docs/redoc/openapi in public mode.
- Mounted ledger routes in all modes while excluding test/accounts/snapshots/analytics/runelite/legacy-plugin routers in public mode.
- Added `CATHERBY_PUBLIC_HOST_MODE` handling and a public surface guard in `web/main.py`.
- Added `tests/test_public_route_separation.py` route-separation coverage.

### Mitigation Status

Resolved for the 01B public/private route-separation gate. Sentinel PASS is granted for 01B only.

### Remediation

The accepted remediation is route separation by explicit public-host mode:

- Direct API public mode now exposes ledger only and denies anonymous docs/test/private/legacy plugin paths by not registering those routes.
- Mounted web public mode denies private API/admin/operator/runtime/Council-like paths before normal route dispatch.
- Ledger remains protected by existing API-key auth instead of being made anonymous.
- Default local/admin mode remains available when public host mode is absent.

### Long-Term Fixes

Still required before any public/plugin readiness claim:

- Persistent production-safe per-key and per-IP rate limits.
- Replay/idempotency controls and deterministic duplicate handling.
- Request body and schema caps.
- Quarantine and validation-status lifecycle.
- Intake backpressure/disable controls.
- Privacy/export classification for raw telemetry and downstream Dungeon Crawl export.
- Deployment proof that `CATHERBY_PUBLIC_HOST_MODE=true` is set before import and that reverse-proxy routing does not bypass the in-app guard.

### Testing Strategy

Use the existing 01B route-separation tests, ledger API tests, frontend startup tests, import smokes, and adversarial TestClient path-variant probes as the regression set for this gate.
## Timeline & Ownership
<!-- ID: timeline -->
| Phase | Owner | Target Date | Notes |
|---|---|---|---|
| Prior security research | Sentinel | 2026-05-15 | Broader public/plugin readiness BLOCK recorded in `docs/security/security/2026-05-15_catherby-live-ingestion/report.md`. |
| 01B implementation | Forge | 2026-05-15 | Landed as `c5b7ef2 feat: gate catherby public routes`. |
| 01B validation | Crucible | 2026-05-15 | PASS recorded in `.scribe/docs/dev_plans/catherby_live_sensory_spine_2026_05_15/REVIEW_REPORT_validation_2026-05-15_0855.md`. |
| 01B security follow-up | Sentinel | 2026-05-15 | PASS for 01B route-separation gate only, with broader public/plugin readiness still blocked. |
| Public/plugin readiness | Blueprint/Forge/Crucible/Sentinel | Future gate | BLOCKED until non-01B controls from the prior security report are implemented and verified. |
## Appendix
<!-- ID: appendix -->
### Logs And Evidence

- Scribe project: `catherby_live_sensory_spine_2026_05_15`.
- Prior report: `docs/security/security/2026-05-15_catherby-live-ingestion/report.md`.
- 01B plan: `.scribe/docs/dev_plans/catherby_live_sensory_spine_2026_05_15/PHASE_PLAN.md` lines 173-233.
- 01B checklist: `.scribe/docs/dev_plans/catherby_live_sensory_spine_2026_05_15/CHECKLIST.md` lines 58-72.
- Crucible report: `.scribe/docs/dev_plans/catherby_live_sensory_spine_2026_05_15/REVIEW_REPORT_validation_2026-05-15_0855.md`.
- Implementation commit: `c5b7ef2 feat: gate catherby public routes`.

### Verification Commands

- `git show --stat --oneline c5b7ef2` -> reviewed package files.
- `git show --oneline -- api/main.py web/main.py tests/test_public_route_separation.py c5b7ef2` -> reviewed implementation diff.
- `/home/austin/miniconda3/envs/uap/bin/python -m pytest tests/test_public_route_separation.py -q` -> 2 passed, 5 warnings.
- `/home/austin/miniconda3/envs/uap/bin/python -m pytest tests/test_live_event_ledger_api.py -q` -> 8 passed, 5 warnings.
- `/home/austin/miniconda3/envs/uap/bin/python -m pytest tests/test_catherby_frontend_startup.py -q` -> 3 passed.
- `/home/austin/miniconda3/envs/uap/bin/python -c 'from web.main import app; from api.main import app'` -> PASS.
- Additional TestClient probe for weird paths and default-mode preservation -> PASS.

### Fix References

- Fix artifact: `api/main.py`, `web/main.py`, and `tests/test_public_route_separation.py` in commit `c5b7ef2`.
- Linkage status: `link_fix` will be recorded for this Sentinel-verified 01B route-separation remediation.

### Open Questions

- Which deployment/reverse-proxy controls will be required as proof for actual `catherby.net` public hosting?
- Should the public-mode API root response stop advertising `/docs`, `/accounts`, `/snapshots`, and `/analytics` even though those paths now return 404?
- Which future package will own durable rate limiting, idempotency, quarantine, backpressure, and privacy/export controls before marketplace/public readiness?
