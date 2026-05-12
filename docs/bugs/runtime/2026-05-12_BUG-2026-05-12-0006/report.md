---
id: osrs_prod_audit_integrate_20260512-bug-2026-05-12-0006
title: "\U0001F41E Standalone Catherby frontend routes 500 after TemplateResponse\
  \ signature change \u2014 osrs_prod_audit_integrate_20260512"
doc_type: BUG-2026-05-12-0006
doc_name: BUG-2026-05-12-0006
category: engineering
status: ready
version: '0.1'
last_updated: 2026-05-12 07:28:59 UTC
maintained_by: agent-20260512-070556-f68eddcf
created_by: agent-20260512-070556-f68eddcf
owners: []
related_docs: []
tags: []
summary: Standalone Catherby frontend route 500 fixed in source by updating TemplateResponse
  calls to the current request-first FastAPI/Starlette contract; live process requires
  restart/reload by Atlas/operator.
edit_trace:
  tool: manage_docs
  created_at: 2026-05-12 07:24:07 UTC
  created_via: replace_range
  last_edited_at: 2026-05-12 07:28:59 UTC
  last_edited_by: agent-20260512-070556-f68eddcf
  last_action: replace_section
---

# 🐞 Standalone Catherby frontend routes 500 after TemplateResponse signature change — osrs_prod_audit_integrate_20260512
**Author:** Scribe
**Version:** v0.1
**Status:** FIXED_PENDING_RUNTIME_RESTART
**Last Updated:** 2026-05-12 07:13:10 UTC

This report captures the root cause and source-owned fix for the standalone Catherby frontend route failure on port 8001. The backend process was alive, but server-rendered frontend routes were failing under the current FastAPI/Starlette template response contract.

---
## Bug Overview
<!-- ID: bug_overview -->
**Bug ID:** BUG-2026-05-12-0006

**Reported By:** mantis

**Date Reported:** 2026-05-12 07:13:10 UTC

**Severity:** CRITICAL

**Status:** FIXED_PENDING_RUNTIME_RESTART

**Component:** standalone-catherby-frontend

**Environment:** local Council-managed backend process

**Customer Impact:** Blocks Catherby website readiness because the public/panel frontend root returns 500 even when the API health endpoint is healthy. Users cannot rely on the standalone website until the fixed source is loaded by a fresh backend process.


---
## Description
<!-- ID: description -->
### Summary
The standalone Catherby app on `127.0.0.1:8001` was listening and `/api/health` returned 200, but `GET /` returned HTTP 500. `.council/osrs_backend.log` showed `web/routes/pages.py` calling `templates.TemplateResponse` with old positional arguments, ending in Jinja2 `TypeError: unhashable type: 'dict'`.

### Expected Behaviour
When the backend starts the standalone Catherby website, server-rendered frontend routes should render HTML instead of raising TemplateResponse/Jinja errors. The API may remain mounted under /api, but frontend readiness must be proven by page routes such as GET /.

### Actual Behaviour
Before the source fix, the standalone Catherby app on `127.0.0.1:8001` was listening and `/api/health` returned 200, but `GET /` returned HTTP 500. The running process still returns 500 until Atlas/operator restarts or starts a fresh backend process, because no restart/reload command was run during this RCA.

### Steps to Reproduce
- [x] Ensure the existing Council-managed backend process is listening on 127.0.0.1:8001.
- [x] Run curl -sS -i --max-time 10 http://127.0.0.1:8001/.
- [x] Observe HTTP 500 while curl -sS -i --max-time 10 http://127.0.0.1:8001/api/health returns HTTP 200.


---
## Investigation
<!-- ID: investigation -->
**Root Cause Analysis:**
FastAPI 0.135.2 / Starlette 1.0.0 exposes `Jinja2Templates.TemplateResponse(request, name, context=None, ...)`. The Catherby route modules still used the old `TemplateResponse(name, context)` call shape, so Starlette treated the template filename as the request and the context dict as the template name. Jinja then attempted to use that dict in its template cache key and raised `TypeError: unhashable type: 'dict'`.

This is a frontend rendering compatibility bug, not a backend process liveness bug and not a Council `/api/osrs/*` proxy bug.

**Affected Areas:**
- web/routes/pages.py
- web/routes/auth.py
- web/routes/profiles.py
- web/routes/clans.py
- web/routes/snapshots_ui.py
- web/routes/profile_detail.py
- web/routes/jobs.py
- web/routes/webhooks.py
- web/routes/admin.py
- web/routes/compare.py


**Related Issues:**
- Operator correction in Scribe progress log at 2026-05-12 07:05 UTC: standalone Catherby frontend/panel is separate from Council pages/proxy path and blocks `catherby.net` readiness.


---
## Resolution Plan
<!-- ID: resolution_plan -->
### Immediate Actions
Fix landed with status: **merged**

### Fix Details
- Artifact: web/routes/pages.py:21
- Execution ID: aea5a2ff-0d59-4d8a-82cc-835d4da016df
## Timeline & Ownership
<!-- ID: timeline -->
| Phase | Owner | Target Date | Notes |
| --- | --- | --- | --- |
| Investigation | Mantis | 2026-05-12 | Confirmed API liveness but frontend 500; traced to TemplateResponse signature mismatch. |
| Fix Development | Mantis | 2026-05-12 | Patched `web/routes/*.py` TemplateResponse calls and added regression test. |
| Testing | Mantis | 2026-05-12 | Targeted regression, compile smoke, and import smoke passed. |
| Deployment | Atlas/operator | Pending | Restart/start backend with `scripts/start_osrs_backend.sh` or Council runtime start flow; Mantis did not run restart/reload. |


---
## Appendix
<!-- ID: appendix -->
- **Fix Reference:** web/routes/pages.py:21 (execution: aea5a2ff-0d59-4d8a-82cc-835d4da016df)
- **Landing Status:** merged
- **Fix Linked By:** mantis
