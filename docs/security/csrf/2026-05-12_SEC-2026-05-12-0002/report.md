
# 🔒 State-changing web routes omit CSRF verification outside auth/profile/clan flows — osrs_prod_audit_integrate_20260512
**Author:** Scribe
**Version:** v0.1
**Status:** INVESTIGATING
**Last Updated:** 2026-05-12 05:00:35 UTC

> Summarise why this document exists and what decisions it captures.

---
## Security Overview
<!-- ID: security_overview -->
**Case ID:** SEC-2026-05-12-0002

**Reported By:** sentinel

**Date Reported:** 2026-05-12 05:00:35 UTC

**Severity:** HIGH

**Status:** INVESTIGATING

**Component:** web-session-routes

**Environment:** pre-production/public catherby.net launch

**Customer Impact:** A malicious page could cause a logged-in user or admin to perform unwanted account/admin/job/webhook mutations if the route is reachable from the public site.

**CVE ID:** [CVE-YYYY-NNNNN or N/A]

**CVSS Score:** [0.0-10.0 or N/A]


---
## Description
<!-- ID: description -->
### Summary
Multiple authenticated POST/DELETE routes rely only on the signed session cookie and do not require `csrf_token` form data or `verify_csrf`. Admin role checks prevent anonymous access, but a public origin could still attempt browser-driven state changes against logged-in users/admins if these routes are reachable.

### Expected Behaviour
Every cookie-authenticated state-changing route should require a CSRF token validated with `verify_csrf`, and templates/HTMX requests should send that token consistently.

### Actual Behaviour
Multiple authenticated POST/DELETE routes rely only on the signed session cookie and do not require `csrf_token` form data or `verify_csrf`. Admin role checks prevent anonymous access, but a public origin could still attempt browser-driven state changes against logged-in users/admins if these routes are reachable.

### Steps to Reproduce
- [ ] Source search `verify_csrf\(|csrf_token` shows CSRF use in `web/routes/auth.py`, `web/routes/profiles.py`, and `web/routes/clans.py`, but not in admin, webhooks, jobs, snapshots_ui, or profile_detail destructive routes.
- [ ] `web/routes/admin.py:118-180` toggles users/admins/unlocks accounts without CSRF form tokens.
- [ ] `web/routes/admin.py:279-292` unblocks IPs without CSRF form tokens.
- [ ] `web/routes/webhooks.py:29-65` creates/updates webhooks without CSRF form tokens.
- [ ] `web/routes/jobs.py:35-101` schedules/deletes jobs without CSRF form tokens.
- [ ] `web/routes/snapshots_ui.py:18-24` triggers snapshot jobs without CSRF form tokens.
- [ ] `web/routes/profile_detail.py:162-207` refreshes mode/deletes snapshot artifacts without CSRF form tokens.



---
## Affected Systems
<!-- ID: affected_systems -->
**Affected Areas:**
- web/routes/admin.py
- web/routes/webhooks.py
- web/routes/jobs.py
- web/routes/snapshots_ui.py
- web/routes/profile_detail.py


**Trust Boundary Violations:**
[Describe which trust boundaries are crossed or violated]

**Attack Vector:**
[local/network/adjacent — CVSS AV metric]


---
## Investigation
<!-- ID: investigation -->
**Root Cause Analysis:**
CSRF protection is implemented as a helper in `web/deps.py` and applied manually per route. Several later state-changing route modules did not adopt the helper, leaving protection inconsistent.

**Related Issues:**
- Link to related bugs, CVEs, or documentation.

**Compliance Impact:**
[GDPR, SOC2, PCI-DSS, HIPAA — list applicable frameworks]


---
## Resolution Plan
<!-- ID: resolution_plan -->
### Immediate Actions
- [ ] Add a shared dependency/decorator or explicit form parameter for all cookie-authenticated POST/PUT/PATCH/DELETE routes. Regression test should enumerate web routes and fail state-changing cookie-auth routes that do not call `verify_csrf` or an approved shared guard.


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