
# 🔒 User-configured webhooks allow unchecked outbound requests — osrs_prod_audit_integrate_20260512
**Author:** Scribe
**Version:** v0.1
**Status:** INVESTIGATING
**Last Updated:** 2026-05-12 05:01:07 UTC

> Summarise why this document exists and what decisions it captures.

---
## Security Overview
<!-- ID: security_overview -->
**Case ID:** SEC-2026-05-12-0003

**Reported By:** sentinel

**Date Reported:** 2026-05-12 05:01:07 UTC

**Severity:** HIGH

**Status:** INVESTIGATING

**Component:** webhooks

**Environment:** pre-production/public catherby.net launch

**Customer Impact:** A public user account could coerce the server to contact internal services or attacker-controlled endpoints whenever webhook dispatch runs.

**CVE ID:** [CVE-YYYY-NNNNN or N/A]

**CVSS Score:** [0.0-10.0 or N/A]


---
## Description
<!-- ID: description -->
### Summary
Authenticated users can store arbitrary webhook URLs, and background dispatch posts to those URLs without scheme, host, private-network, redirect, or allowlist validation. On a public deployment this can become an SSRF/egress abuse path from the server network.

### Expected Behaviour
Webhook creation should validate URL scheme and destination, reject localhost/private/link-local/metadata/internal hosts, limit payload size and redirects, and sign outbound requests with per-hook secrets where appropriate.

### Actual Behaviour
Authenticated users can store arbitrary webhook URLs, and background dispatch posts to those URLs without scheme, host, private-network, redirect, or allowlist validation. On a public deployment this can become an SSRF/egress abuse path from the server network.

### Steps to Reproduce
- [ ] `web/routes/webhooks.py:29-65` accepts `url` form data and passes `url.strip()` directly into `WebhookService.upsert_webhook`.
- [ ] `web/services/webhooks.py:17-53` persists the URL without validation.
- [ ] `web/services/webhooks.py:70-90` dispatches `httpx.post(url, json=payload, timeout=5.0)` to the stored URL.
- [ ] A concrete post-fix negative probe should try to save destinations such as loopback, link-local metadata, private RFC1918 hosts, non-HTTP schemes, and redirecting URLs and expect rejection before persistence.



---
## Affected Systems
<!-- ID: affected_systems -->
**Affected Areas:**
- web/routes/webhooks.py
- web/services/webhooks.py


**Trust Boundary Violations:**
[Describe which trust boundaries are crossed or violated]

**Attack Vector:**
[local/network/adjacent — CVSS AV metric]


---
## Investigation
<!-- ID: investigation -->
**Root Cause Analysis:**
Webhook URL handling treats user-provided URLs as trusted configuration and lacks an egress policy at both persistence and dispatch time.

**Related Issues:**
- Link to related bugs, CVEs, or documentation.

**Compliance Impact:**
[GDPR, SOC2, PCI-DSS, HIPAA — list applicable frameworks]


---
## Resolution Plan
<!-- ID: resolution_plan -->
### Immediate Actions
- [ ] Add centralized URL validation and dispatch-time enforcement. Recommended minimal controls: only `https` except explicit dev mode, DNS/IP resolution with private-network denylist, redirect disabled or revalidated, bounded timeout/payload, audit logs, and optional per-hook HMAC signature using the existing `secret` column.


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