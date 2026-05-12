
# 🔒 Public web app mounts unauthenticated mutating backend API under /api — osrs_prod_audit_integrate_20260512
**Author:** Scribe
**Version:** v0.1
**Status:** INVESTIGATING
**Last Updated:** 2026-05-12 05:00:04 UTC

> Summarise why this document exists and what decisions it captures.

---
## Security Overview
<!-- ID: security_overview -->
**Case ID:** SEC-2026-05-12-0001

**Reported By:** sentinel

**Date Reported:** 2026-05-12 05:00:04 UTC

**Severity:** CRITICAL

**Status:** INVESTIGATING

**Component:** public-api-boundary

**Environment:** pre-production/public catherby.net launch

**Customer Impact:** Unauthenticated public users could alter or delete tracked account/snapshot data, trigger expensive snapshot jobs, and access operator/test API surfaces if `/api` is reachable on catherby.net.

**CVE ID:** [CVE-YYYY-NNNNN or N/A]

**CVSS Score:** [0.0-10.0 or N/A]


---
## Description
<!-- ID: description -->
### Summary
`web/main.py` mounts the backend API app at `/api`; the API app includes account and snapshot create/update/delete/run routes without an authentication or admin dependency. If the Catherby web process is exposed directly to catherby.net, anonymous internet clients can mutate account/snapshot data and trigger snapshot jobs through `/api/*`.

### Expected Behaviour
Public deployment should expose only intentionally public read endpoints. Any state-changing account/snapshot/job/admin operation must require an authenticated, authorized principal or remain local/operator-only behind reverse-proxy denies.

### Actual Behaviour
`web/main.py` mounts the backend API app at `/api`; the API app includes account and snapshot create/update/delete/run routes without an authentication or admin dependency. If the Catherby web process is exposed directly to catherby.net, anonymous internet clients can mutate account/snapshot data and trigger snapshot jobs through `/api/*`.

### Steps to Reproduce
- [ ] From source: `web/main.py:67-68` mounts `api_app` at `/api`.
- [ ] From source: `api/main.py:246-287` includes account, snapshot, analytics, test, runelite, and plugin routers.
- [ ] From source: `api/endpoints/accounts.py:334-337`, `398-403`, and `480-484` define account create/update/delete with only `get_database_connection` dependency.
- [ ] From source: `api/endpoints/snapshots.py:564-567`, `591-595`, and `714-718` define snapshot run/create/delete with no auth dependency.
- [ ] Launch proof command after server start: `curl -i -X POST https://catherby.net/api/accounts/ -H 'Content-Type: application/json' --data '{...}'` should be rejected with 401/403 before any fix; current source has no such guard.



---
## Affected Systems
<!-- ID: affected_systems -->
**Affected Areas:**
- web/main.py
- api/main.py
- api/endpoints/accounts.py
- api/endpoints/snapshots.py
- api/endpoints/analytics.py
- api/test_accounts.py


**Trust Boundary Violations:**
[Describe which trust boundaries are crossed or violated]

**Attack Vector:**
[local/network/adjacent — CVSS AV metric]


---
## Investigation
<!-- ID: investigation -->
**Root Cause Analysis:**
The public web app composes the private backend API app wholesale under `/api`, and backend routers rely on open dependencies rather than an explicit public/private route contract. Auth exists for web session routes and plugin token routes, but not for core mutating backend API routes.

**Related Issues:**
- Link to related bugs, CVEs, or documentation.

**Compliance Impact:**
[GDPR, SOC2, PCI-DSS, HIPAA — list applicable frameworks]


---
## Resolution Plan
<!-- ID: resolution_plan -->
### Immediate Actions
- [ ] Before public launch, split public read APIs from private operator APIs or add explicit auth/authorization dependencies to mutating backend routes and block private `/api` paths at the reverse proxy. Disable `/docs`, `/redoc`, `/openapi.json`, and `/test` on public hosts unless intentionally exposed.


### Mitigation Status
[not-started/in-progress/mitigated/resolved]

### Long-Term Fixes
- [ ] Outline long-term remedial work or hardening.

### Testing Strategy
- [ ] Define validation steps for the fix (security scan, pen test, regression).


---
## Timeline & Ownership
<!-- ID: timeline -->
| Phase | Owner | Target Date | Notes |
| --- | --- | --- | --- |
| Investigation | [Name] | [Date] | [Details] |
| Fix Development | [Name] | [Date] | [Details] |
| Testing | [Name] | [Date] | [Details] |
| Deployment | [Name] | [Date] | [Details] |


---
## Appendix
<!-- ID: appendix -->
- **Logs & Evidence:** [Link to relevant logs, traces, screenshots]
- **Fix References:** [Git commits, PRs, or documentation]
- **Open Questions:** [List unresolved unknowns or next investigations]


---