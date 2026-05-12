
# 🔒 Profile report routes allow unauthenticated report traversal and unescaped HTML rendering — osrs_prod_audit_integrate_20260512
**Author:** Scribe
**Version:** v0.1
**Status:** INVESTIGATING
**Last Updated:** 2026-05-12 05:02:28 UTC

> Summarise why this document exists and what decisions it captures.

---
## Security Overview
<!-- ID: security_overview -->
**Case ID:** SEC-2026-05-12-0005

**Reported By:** sentinel

**Date Reported:** 2026-05-12 05:02:28 UTC

**Severity:** HIGH

**Status:** INVESTIGATING

**Component:** profile-report-routes

**Environment:** pre-production/public catherby.net launch

**Customer Impact:** Public users may read unintended markdown files from the application tree and may receive executable HTML if report content includes markup.

**CVE ID:** [CVE-YYYY-NNNNN or N/A]

**CVSS Score:** [0.0-10.0 or N/A]


---
## Description
<!-- ID: description -->
### Summary
Several profile report/json/detail routes do not require authentication and construct filesystem paths from route/query parameters. Report content is returned inside raw HTML `\<pre\>` without escaping. Path traversal is possible against existing report directories and can read arbitrary `.md` files reachable from the repo root pattern; unescaped report content can also become stored/reflected HTML if report data contains markup.

### Expected Behaviour
Public profile routes should validate account/snapshot identifiers against database records, normalize and constrain filesystem reads under the intended reports/data directories, require authorization for private profile artifacts, and render text with template escaping or PlainTextResponse.

### Actual Behaviour
Several profile report/json/detail routes do not require authentication and construct filesystem paths from route/query parameters. Report content is returned inside raw HTML `\<pre\>` without escaping. Path traversal is possible against existing report directories and can read arbitrary `.md` files reachable from the repo root pattern; unescaped report content can also become stored/reflected HTML if report data contains markup.

### Steps to Reproduce
- [ ] `web/routes/profile_detail.py:111-118` reads `Path(f"reports/{safe_rsn}/{snapshot_id}.md")` and returns `HTMLResponse(f"<pre class='report-view'>{content}</pre>")` without `require_user` or escaping.
- [ ] `web/routes/profile_detail.py:121-130` returns JSON payload content without `require_user`.
- [ ] `web/routes/profile_detail.py:133-159` renders snapshot detail without `require_user`.
- [ ] Local proof of traversal primitive: `test -e 'reports/Flamelborn/../../README.md' && echo yes || echo no` returned `yes`, showing an existing report directory plus `../..` can escape to repo-root `.md` files when used as the path pattern.
- [ ] A live negative probe after remediation should request a traversal-style `snapshot_id` and expect 400/404, not file contents.



---
## Affected Systems
<!-- ID: affected_systems -->
**Affected Areas:**
- web/routes/profile_detail.py


**Trust Boundary Violations:**
[Describe which trust boundaries are crossed or violated]

**Attack Vector:**
[local/network/adjacent — CVSS AV metric]


---
## Investigation
<!-- ID: investigation -->
**Root Cause Analysis:**
The route trusts `rsn` and `snapshot_id` as path components and bypasses both authorization and safe path resolution. Rendering bypasses Jinja escaping by concatenating file content into an `HTMLResponse`.

**Related Issues:**
- Link to related bugs, CVEs, or documentation.

**Compliance Impact:**
[GDPR, SOC2, PCI-DSS, HIPAA — list applicable frameworks]


---
## Resolution Plan
<!-- ID: resolution_plan -->
### Immediate Actions
- [ ] Resolve requested report paths through `Path.resolve()`, verify they remain under the expected `reports/\<safe_account\>/` directory, validate snapshot IDs against database records, require user/public-profile authorization, and render report text through escaped templates or `PlainTextResponse` with safe content type.


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