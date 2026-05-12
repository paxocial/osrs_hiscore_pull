
# 🔒 Local secret and production-like data artifacts are present inside the repo tree — osrs_prod_audit_integrate_20260512
**Author:** Scribe
**Version:** v0.1
**Status:** INVESTIGATING
**Last Updated:** 2026-05-12 05:01:38 UTC

> Summarise why this document exists and what decisions it captures.

---
## Security Overview
<!-- ID: security_overview -->
**Case ID:** SEC-2026-05-12-0004

**Reported By:** sentinel

**Date Reported:** 2026-05-12 05:01:38 UTC

**Severity:** HIGH

**Status:** INVESTIGATING

**Component:** secrets-and-data-hygiene

**Environment:** pre-production/public catherby.net launch

**Customer Impact:** If the repo tree or wrong static root is published, secrets and account/security data could leak. Even without direct web exposure, tracked mutable auth data increases accidental disclosure and environment drift risk.

**CVE ID:** [CVE-YYYY-NNNNN or N/A]

**CVSS Score:** [0.0-10.0 or N/A]


---
## Description
<!-- ID: description -->
### Summary
Repository inspection found a hardcoded Council hook secret key path in `opencode.json`, local env files with secret-bearing keys, and tracked SQLite database artifacts under `data/analytics.db` containing security-sensitive tables such as users, api_tokens, audit_log, password_reset_tokens, and webhooks. Secret values are not repeated here.

### Expected Behaviour
Public deployment and source artifacts should not contain local hook secrets, production credentials, password reset/token tables, or mutable runtime databases unless intentionally provisioned outside the web/static/repo artifact with strict permissions and backup policy.

### Actual Behaviour
Repository inspection found a hardcoded Council hook secret key path in `opencode.json`, local env files with secret-bearing keys, and tracked SQLite database artifacts under `data/analytics.db` containing security-sensitive tables such as users, api_tokens, audit_log, password_reset_tokens, and webhooks. Secret values are not repeated here.

### Steps to Reproduce
- [ ] `jq -r 'paths(scalars) | map(tostring) | join(".")' opencode.json` shows `mcp.channel.environment.COUNCIL_HOOK_SECRET`.
- [ ] `awk -F= '/^[A-Za-z_][A-Za-z0-9_]*=/{print FILENAME ":" NR ":" $1}' .council/.env .council/.env.example .scribe/.env.example` shows secret-bearing env keys without printing values.
- [ ] `git ls-files opencode.json .council/.env config/accounts.json data/analytics.db temp_simple_test.db-wal temp_simple_test.db-shm` shows `data/analytics.db`, `config/accounts.json`, and temp DB WAL/SHM files tracked; `opencode.json` is currently untracked but present in the repo root.
- [ ] `sqlite3 data/analytics.db '.tables'` lists auth/security-sensitive tables including users, api_tokens, audit_log, password_reset_tokens, and webhooks.



---
## Affected Systems
<!-- ID: affected_systems -->
**Affected Areas:**
- opencode.json
- .council/.env
- data/analytics.db
- config/accounts.json


**Trust Boundary Violations:**
[Describe which trust boundaries are crossed or violated]

**Attack Vector:**
[local/network/adjacent — CVSS AV metric]


---
## Investigation
<!-- ID: investigation -->
**Root Cause Analysis:**
Development/runtime secrets and mutable database state live inside the repo tree, and some database artifacts are tracked. The public deployment boundary has not yet defined a clean packaging rule separating source/static assets from local operator/runtime state.

**Related Issues:**
- Link to related bugs, CVEs, or documentation.

**Compliance Impact:**
[GDPR, SOC2, PCI-DSS, HIPAA — list applicable frameworks]


---
## Resolution Plan
<!-- ID: resolution_plan -->
### Immediate Actions
- [ ] Rotate the exposed hook secret, remove local secret-bearing files from any deploy/source artifact, untrack mutable SQLite/test DB artifacts if they are not intentional fixtures, keep production DB outside repo/static roots, and add deploy verification that denies access to dotfiles, config secrets, and data directories.


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