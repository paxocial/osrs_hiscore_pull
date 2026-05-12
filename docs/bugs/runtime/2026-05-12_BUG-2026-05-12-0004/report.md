
# 🐞 Main-port OSRS proxy 503s during backend warmup, with stale proxy regression contract — osrs_prod_audit_integrate_20260512
**Author:** Scribe
**Version:** v0.1
**Status:** RESOLVED
**Last Updated:** 2026-05-12 06:46:04 UTC

This report records the RCA for the main-port OSRS web proxy 503 window and the narrow regression-test fix that preserves the public Catherby-facing proxy contract.

---
## Bug Overview
<!-- ID: bug_overview -->
**Bug ID:** BUG-2026-05-12-0004

**Reported By:** mantis

**Date Reported:** 2026-05-12 06:46:04 UTC

**Severity:** HIGH

**Status:** RESOLVED

**Component:** main-port-web-proxy

**Environment:** local Council web main port 8015 with OSRS backend on 8001

**Customer Impact:** During backend warmup, operators may see proxy 503s in logs and transient degraded UI state. The main-port hosting readiness gate should not treat that transient API dependency state as a whole-site source failure once the page loads and exposes degraded state.


---
## Description
<!-- ID: description -->
### Summary
Operator saw the main/frontend host path that catherby.net would serve show server error while Council web logs recorded GET /api/osrs/health and GET /api/osrs/snapshots/latest returning 503. Focused proxy tests also failed because they expected 14 routes and authenticated proxy endpoints despite the current public OSRS game-data proxy contract.

### Expected Behaviour
The main page should load while OSRS backend dependencies are warming up or temporarily offline, API state should degrade visibly, and regression tests should match the current public proxy route contract.

### Actual Behaviour
Operator saw the main/frontend host path that catherby.net would serve show server error while Council web logs recorded GET /api/osrs/health and GET /api/osrs/snapshots/latest returning 503. Focused proxy tests also failed because they expected 14 routes and authenticated proxy endpoints despite the current public OSRS game-data proxy contract.

### Steps to Reproduce
- [x] Review web_ui.log around 2026-05-12T06:40:26Z through 06:40:35Z for transient /api/osrs health/latest 503s around runtime start.
- [x] Probe existing local runtime without restart: curl http://127.0.0.1:8015/api/osrs/health and curl http://127.0.0.1:8015/api/osrs/snapshots/latest after warmup.
- [x] Run pytest tests/test_osrs_proxy.py -v before the test-contract fix.



---
## Investigation
<!-- ID: investigation -->
**Root Cause Analysis:**
Historical 503s came from the OSRS backend dependency not being ready during a short warmup window after /api/osrs/runtime/start. Current dashboard JS already catches 502/503 from health/latest and renders offline/degraded state; current runtime probes return 200. The confirmed failing source-adjacent defect was stale proxy regression tests that no longer matched the 15-route public proxy contract.

**Affected Areas:**
- .council/web/routes/osrs_proxy.py
- .council/web/static/js/osrs-control.js
- tests/test_osrs_proxy.py


**Related Issues:**
- Atlas frontend host blocker logged in `osrs_prod_audit_integrate_20260512` at 2026-05-12 06:36 UTC.
- Related active packages: report/materialization/delta hotfixes are separate and were not modified by this fix.


---
## Resolution Plan
<!-- ID: resolution_plan -->
### Immediate Actions
- [x] Production source did not require a change. Updated tests/test_osrs_proxy.py to expect 15 proxy routes including snapshot report passthrough and to assert the public game-data proxy contract rather than requiring current_user auth on /api/osrs endpoints.


### Long-Term Fixes
- [ ] If catherby.net is intended to expose a public unauthenticated landing page on the Council web host, define that route/deployment boundary explicitly outside this bug package.
- [ ] Consider reducing log severity for expected short backend warmup 503s if the proxy continues to surface them as handled degraded dependency state.

### Testing Strategy
- [x] Run focused proxy regression tests before the test fix to capture RED.
- [x] Run focused proxy regression tests after the test fix to confirm GREEN.
- [x] Probe existing live local ports read-only; do not restart or reload runtime.


---
## Timeline & Ownership
<!-- ID: timeline -->
| Phase | Owner | Target Date | Notes |
| --- | --- | --- | --- |
| Investigation | mantis | 2026-05-12 | Mapped Council main port, OSRS backend port, proxy routes, dashboard boot calls, and web logs. |
| Fix Development | mantis | 2026-05-12 | Updated `tests/test_osrs_proxy.py` only; no production source change required. |
| Testing | mantis | 2026-05-12 | `pytest tests/test_osrs_proxy.py -v` passed after RED failure; import smoke passed in the uap environment. |
| Deployment | operator | TBD | No runtime reload performed by this package. |


---
## Appendix
<!-- ID: appendix -->
- **Logs & Evidence:** `web_ui.log` showed `/api/osrs/health` and `/api/osrs/snapshots/latest` returning 503 at 2026-05-12T06:40:26Z-06:40:28Z, then 200 by 2026-05-12T06:40:35Z.
- **Fix References:** `tests/test_osrs_proxy.py`.
- **Open Questions:** Whether catherby.net should map to a public standalone landing page instead of the authenticated Council web root is outside this bug package.


---
