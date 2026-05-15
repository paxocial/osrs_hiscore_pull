---
id: catherby_live_sensory_spine_2026_05_15-catherby-live-ingestion
title: Catherby Live Ingestion Security Review
doc_type: catherby-live-ingestion
doc_name: catherby-live-ingestion
category: security
status: ready
version: '0.1'
last_updated: 2026-05-15 07:01:30 UTC
maintained_by: agent-20260515-064653-6cb0c5d2
created_by: agent-20260515-064653-6cb0c5d2
owners: []
related_docs: []
tags: []
summary: Security research for Catherby live plugin ingestion; verdict BLOCK for public/plugin
  readiness until persistent rate limits, idempotency, quarantine, payload caps, backpressure,
  privacy/export classes, and route separation are planned and implemented.
severity: high
edit_trace:
  tool: manage_docs
  created_at: 2026-05-15 07:01:30 UTC
  created_via: frontmatter_update
  last_edited_at: 2026-05-15 07:01:30 UTC
  last_edited_by: agent-20260515-064653-6cb0c5d2
  last_action: frontmatter_update
---

# 🔒 Catherby Live Ingestion Security Review — catherby_live_sensory_spine_2026_05_15
**Author:** Sentinel
**Version:** v0.1
**Status:** ready
**Last Updated:** 2026-05-15 07:01 UTC

> Security review for Catherby live RuneLite/plugin ingestion before public traffic. Captures current controls, missing mandatory safeguards, threat scenarios, and a BLOCK recommendation for public/plugin readiness until Blueprint plans the required controls.

---
## Security Overview
<!-- ID: security_overview -->
### Security verdict

**Recommendation: BLOCK public/plugin implementation readiness.**

Catherby has a useful starting control for plugin access: missing `X-API-Key` fails closed with `401`, invalid/revoked keys fail with `401`, and tokens without a plugin scope fail with `403` in the current auth dependency. I verified the existing dependency tests with `pytest -q tests/test_api_dependencies.py::TestRequirePluginKey` and all 8 tests passed.

That is not enough for RuneLite marketplace or public plugin traffic. The current ingestion surface is still a snapshot-era, table-per-family API with process-local rate limiters, open-ended batch/list payloads, no replay or idempotency key, no quarantine path, no durable backpressure/disable switch, and no explicit privacy/export classification. Existing hosted web findings also remain relevant because `web/main.py` mounts the backend API under `/api`, while earlier reports identify public `/api` exposure, CSRF gaps, webhook SSRF risk, local secret/runtime data exposure, and unauthenticated report traversal/XSS.

Severity: **High** before public exposure. The likely failure mode is not immediate anonymous plugin access without a key; it is authenticated or key-abuse traffic overwhelming or poisoning the future ledger, plus public-host route exposure that can cross from the Catherby website into operator/admin/backend controls.

### Answer to research questions

- No API key reliably denies plugin API access today on the inspected plugin dependency path: yes, source and tests support this.
- Rate limits are not production-safe for plugin ingestion: plugin limits are in memory and per process, while persistent IP rate limiting exists only in separate web auth middleware.
- Replay/idempotency/quarantine/payload caps are not implemented for the live ledger requirement.
- API keys are stored as SHA-256 hashes, but scope matching is substring-based and token creation/listing needs public-host audit constraints.
- Public RuneLite traffic requires persistent per-key and per-IP controls, strict payload caps, idempotent append-only storage, quarantine, backpressure, and route separation from Council/local operator controls.
- Blueprint must separate public Catherby ingestion/admin/web routes from local Council runtime controls and never rely on Council-only middleware or local generated surfaces for hosted security.
## Description
<!-- ID: description -->
### Current controls with file-level evidence

- **Plugin routes require API-key auth.** `api/endpoints/plugin.py` imports `require_plugin_key` and every inspected plugin route uses `token: Dict = Depends(require_plugin_key)`, including `/session` at lines 103-107, `/batch` at lines 769-773, and `/status` at lines 1092-1095. The route module states all endpoints require `X-API-Key` with plugin scope at lines 1-8.
- **Missing keys fail closed.** `api/dependencies.py:51-74` accepts `X-API-Key`, logs the missing header, and raises `401` when absent. `tests/test_api_dependencies.py:37-43` covers that path; the targeted test class passed locally.
- **Invalid and revoked keys fail closed.** `api/dependencies.py:76-95` hashes the submitted token with SHA-256, checks `api_tokens.token_hash` where `revoked_at IS NULL`, and raises `401` when no active row is found. `tests/test_api_dependencies.py:46-66` covers invalid/revoked behavior.
- **Plugin scope is required but currently loose.** `api/dependencies.py:99-106` checks `if "plugin" not in scopes`, so `my_plugin_api` passes. `tests/test_api_dependencies.py:179-198` documents this as current behavior.
- **Token storage is hash-only in the table.** `database/sql/004_auth_clans_tokens.sql:47-60` defines `api_tokens.token_hash TEXT UNIQUE NOT NULL`, and `web/services/auth.py:184-196` issues a random token, stores only its SHA-256 hash, and returns the plaintext once to the caller.
- **Plugin traffic has per-token process-local limits.** `api/dependencies.py:329-364` defines in-memory `TokenRateLimiter` and global `plugin_rate_limiter` (30/min) plus `batch_rate_limiter` (10/min). `api/endpoints/plugin.py:119-124` and `785-790` enforce these for ordinary and batch routes.
- **Global API traffic has process-local IP limits.** `api/main.py:116-130` applies the in-memory `RateLimiter` at 100 requests/minute per `request.client.host` before route dispatch.
- **Separate web auth rate limiting is persistent but not plugin-wired.** `database/sql/009_rate_limiting.sql:5-23` creates `rate_limit_store`; `web/middleware/rate_limit.py:69-137` reads/writes it by IP and endpoint. The plugin routes do not call this decorator or table path.
- **Hosted web hardening exists but is incomplete for public API exposure.** `web/middleware/security_headers.py:18-41` adds HSTS, nosniff, frame deny, CSP, referrer, and permissions headers. `web/main.py:67-68` still mounts the backend `api_app` under `/api`, which pulls the backend API into the hosted web app boundary.

### Actual security posture

The current plugin API is defensible only as a local or controlled pre-public surface. It authenticates requests, uses parameterized SQL, and has some schema validation. It does not yet satisfy the live sensory spine controls in `SPEC_CATHERBY_LIVE_01.md`, which require replay-safe ledger records, payload hashing, privacy/export classes, quarantine, and backpressure before public or plugin marketplace exposure.
## Affected Systems
<!-- ID: affected_systems -->
### Missing mandatory controls

- **Persistent production-safe plugin rate limiting:** absent. Current plugin limits are in-memory Python dictionaries keyed only by token id; they reset on process restart and do not coordinate across workers or hosts. The persistent `rate_limit_store` is IP/endpoint oriented and lives in web auth middleware, not plugin ingestion.
- **Per-key plus per-IP abuse policy:** incomplete. There is per-token limiting after auth and global in-memory IP limiting, but no durable, production-safe combined key/IP/device policy and no trusted-proxy parsing contract for hosted traffic.
- **Replay/idempotency:** absent. Current schemas do not require `event_id`, `idempotency_key`, `payload_hash`, nonce, request timestamp bounds, or source sequence; route handlers use plain `INSERT` into table-per-family storage.
- **Quarantine:** absent. Invalid Pydantic payloads are rejected by FastAPI before route logic, but there is no durable rejected-payload quarantine with reason, token id, hash, or operator review lifecycle.
- **Payload and batch caps:** incomplete. Some strings and integers are bounded, but `BatchPayload` list fields, bank `items`, equipment/inventory dictionaries, `completed_tasks`, request body bytes, and total events per batch are not capped.
- **Backpressure and disable switch:** absent for plugin intake. No config flag, DB flag, or admin/offline switch can reject ingestion before DB writes while keeping health/status available.
- **Privacy/export classification:** absent. Live payloads can include bank value, equipment, inventory, loot source, activity detail, RSN, world, timestamps, and plugin version, but no schema or storage field marks public/private/exportable classes.
- **Storage contract for live ledger:** absent. The current required SQL migrations define auth, rate-limit, and audit tables but no live `ingested_events`, `event_payloads`, `event_batches`, `quarantine_records`, or current `plugin_*` tables used by route handlers.
- **Public-host route separation:** unresolved. `web/main.py:67-68` mounts backend API under `/api`; previous security reports show anonymous mutating backend API exposure, inconsistent CSRF, SSRF-capable webhooks, repo/runtime data exposure, and report traversal/XSS risks.

### Trust boundaries

- RuneLite plugin/client to public Catherby API: untrusted client, potentially compromised key, hostile network, replayable payloads.
- Public Catherby website to private/operator backend API: hosted visitors must not inherit local operator or Council control surfaces.
- Catherby application to SQLite/runtime storage: ingestion must not write unbounded or unaudited data directly into durable state.
- Catherby to Dungeon Crawl export: only vetted, privacy-classified observations should cross into downstream game systems.
- Catherby to Council runtime controls: local Council pages, generated surfaces, and operator tooling are not public security controls and must remain separate from catherby.net.
## Investigation
<!-- ID: investigation -->
### Threat scenarios

1. **Compromised plugin key floods ingestion.** A leaked key can send 30 ordinary requests/minute plus 10 batch requests/minute per process, with no persistent cross-worker limit and no durable per-key/IP abuse ledger. Restarting or scaling the app resets in-memory counters.
2. **Replay creates false world state.** An attacker or buggy client can resend the same event/batch because the payload has no `event_id`, idempotency key, nonce, payload hash, or unique storage constraint. Current inserts do not deduplicate.
3. **Oversized batch exhausts CPU, memory, or SQLite write capacity.** `BatchPayload` optional lists and bank/equipment/inventory containers lack max item counts and total batch caps. Pydantic will parse before route logic, so body size controls need to sit at middleware/proxy and schema levels.
4. **Malicious but authenticated payload poisons downstream facts.** Without quarantine and validation status, suspicious telemetry either rejects without forensic capture or writes directly into durable domain tables. Future Dungeon Crawl export could consume unvetted observations.
5. **Scope false positive grants plugin access.** A token scope string such as `my_plugin_api` passes the current substring check. This is not an anonymous bypass, but it is too permissive for public scoped-key semantics.
6. **Hosted web route mixing exposes private controls.** Because the web app mounts the backend API under `/api`, public catherby.net deployment can accidentally expose snapshot/account/job/operator routes beside plugin ingestion. Prior reports already identify public API, CSRF, SSRF, secret/data, and traversal/XSS issues.
7. **Privacy leak through future exports.** Bank value, equipment, inventory, loot, world, timestamps, activity details, and RSN can reveal play patterns or wealth. Without privacy/export classes, downstream reports or Dungeon Crawl integrations may expose more than intended.
8. **Council/local runtime confusion.** Local Council pages and generated surfaces are useful for operator workflows, but they are not public-host access controls. Any Blueprint that depends on local Council runtime behavior to secure catherby.net would cross the wrong boundary.

### Root cause analysis

The current code grew from a snapshot/reporting application into a plugin ingestion concept before the live-ledger security contract existed. Auth was centralized early, but rate limiting, replay handling, storage, quarantine, and public/private route boundaries remain split across older web/API surfaces. The security fix is not a one-line guard; Blueprint needs to define a first-class ingestion boundary with durable controls before Forge implements public traffic support.

### Privacy and compliance impact

This is not a regulated payment or health-data surface, but it does process account-linked telemetry and can reveal gameplay behavior, inventory/bank state, wealth estimates, timestamps, world numbers, and user/token audit metadata. Treat it as sensitive user telemetry with least-privilege collection, explicit export classes, retention policy, and operator-only audit access.
## Resolution Plan
<!-- ID: resolution_plan -->
### Required implementation safeguards

1. **Keep `require_plugin_key`, but tighten scope semantics.** Parse scopes as a delimiter-aware set and require exact `plugin` or a purpose-specific `plugin:ingest` scope. Add negative tests for `my_plugin_api`, `readplugin`, and empty/malformed scopes.
2. **Move plugin limits to durable storage.** Implement persistent per-key and per-IP rate records with atomic updates, cleanup, and trusted-proxy handling. Treat IP headers as trustworthy only from configured reverse proxies. Keep a cheaper in-process prefilter optional, not authoritative.
3. **Add request body and schema caps.** Enforce max body bytes at app/proxy level; add Pydantic max lengths/item counts for every list/dict payload; cap total batch events; cap string fields; reject old/future timestamps beyond a configured skew.
4. **Design append-only idempotent ledger storage.** Require `event_id` or idempotency key, payload hash, source/plugin version, received timestamp, token id, account id, validation status, privacy class, and optional source refs. Use unique constraints/`ON CONFLICT` semantics so replay returns the prior accepted record rather than duplicating events.
5. **Introduce quarantine before derived facts.** Suspicious or schema-valid-but-policy-invalid payloads should write to quarantine with token id, source IP, hash, reason code, payload class, retention deadline, and operator review state. Do not export quarantined data to Dungeon Crawl.
6. **Add a disable/backpressure switch.** Provide config and DB-controlled intake states such as enabled, read-only/status-only, degraded, and disabled. Disabled intake must reject writes before DB-heavy work while `/status` remains available for clients.
7. **Separate public Catherby routes from private/operator routes.** Public catherby.net should expose only intended read routes and plugin ingestion. Private backend APIs, admin routes, docs/OpenAPI, test routes, Council pages, local operator pages, and runtime controls need explicit auth or reverse-proxy denies.
8. **Define privacy/export classes.** At minimum classify raw/private telemetry, derived/internal facts, public-safe observations, and Dungeon Crawl exportable events. Every storage/export path needs an allowlist based on these classes.
9. **Audit without leaking secrets.** Log token id, user id, scope, request id, IP, user agent, result, reason code, and payload hash/counts. Do not log plaintext API keys or full sensitive payloads.
10. **Keep existing public-host security cases in the plan.** Before public launch, the old `/api` exposure, CSRF, SSRF, secret/data exposure, and traversal/XSS reports must be resolved or explicitly blocked at deployment.

### Verification requirements for future packages

- Auth: tests for missing key `401`, invalid/revoked key `401`, no plugin scope `403`, exact-scope positive, substring-scope negative, and no plaintext token logging.
- Rate limiting: tests prove counters persist across app instances/restarts, are atomic under concurrent requests, combine per-key and per-IP behavior, and respect trusted-proxy configuration.
- Payload caps: tests reject oversized body, oversized batch, too many bank/items/inventory entries, too-long strings, stale/future timestamps, and malformed event envelopes before durable writes.
- Replay/idempotency: tests submit the same event twice and prove one accepted ledger record with deterministic response; conflicting replay with same key but different hash must reject or quarantine.
- Quarantine: tests prove invalid/suspicious payloads create quarantine records with reason codes and do not create exportable derived facts.
- Backpressure: tests prove disabled/degraded intake returns the expected status without DB-heavy writes and keeps authenticated status/health behavior intact.
- Public-host separation: route inventory tests or integration probes must prove private `/api`, docs, test, admin, Council/local pages, and runtime controls are not reachable anonymously on the public host.
- Privacy/export: tests prove only explicitly exportable privacy classes reach Dungeon Crawl or public reports.

### BLOCK/PASS recommendation for implementation readiness

**BLOCK for public/plugin readiness.** Blueprint may proceed with planning only if these safeguards become explicit task-package acceptance criteria. Forge should not implement public RuneLite/plugin traffic until Blueprint owns the auth/rate/idempotency/quarantine/backpressure/privacy/public-host boundary as first-class work.
## Timeline & Ownership
<!-- ID: timeline -->
| Phase | Owner | Target Date | Notes |
|---|---|---|---|
| Security research | Sentinel | 2026-05-15 | Source-backed review completed for SECURITY-RESEARCH-CATHERBY-INGEST-01. |
| Blueprint planning | Blueprint | Next gate | Must translate this BLOCK verdict into explicit package safeguards before Forge. |
| Implementation | Forge | Blocked | No implementation authorized in this package; public/plugin traffic work remains blocked until planned. |
| Validation | Crucible/Sentinel | Future package gate | Must prove auth, persistent limits, idempotency, caps, quarantine, backpressure, route separation, and privacy/export controls. |

No fix has landed in this package. `link_fix` is not applicable yet because the task is research-only and no remediation artifact was implemented or verified.
## Appendix
<!-- ID: appendix -->
### Evidence and commands

- SPEC: `.scribe/docs/dev_plans/catherby_live_sensory_spine_2026_05_15/SPEC_CATHERBY_LIVE_01.md`, especially required controls around auth, rate, idempotency, quarantine, privacy/export, and backpressure.
- Source reads: `api/dependencies.py`, `api/endpoints/plugin.py`, `api/schemas/plugin.py`, `api/main.py`, `web/main.py`, `web/middleware/rate_limit.py`, `web/middleware/security_headers.py`, `web/middleware/admin.py`, `web/services/auth.py`, `web/services/audit.py`, `database/sql/004_auth_clans_tokens.sql`, `database/sql/009_rate_limiting.sql`, `database/sql/010_account_security.sql`, `database/sql/011_audit_log.sql`, and `docs/security/INDEX.md`.
- Existing security reports consulted: `SEC-2026-05-12-0001` public `/api` exposure, `SEC-2026-05-12-0002` CSRF gaps, `SEC-2026-05-12-0003` webhook SSRF, `SEC-2026-05-12-0004` local secret/runtime data exposure, and `SEC-2026-05-12-0005` report traversal/XSS.
- Verification command: `pytest -q tests/test_api_dependencies.py::TestRequirePluginKey` -> `8 passed, 1 warning in 0.30s`.

### Fix references

No code fix exists for this research package. Future fix artifacts must link back to this report and to any reopened/continued security cases after Forge implementation and Sentinel verification.

### Open questions

- Should Blueprint keep the existing `/api/v1/plugin` prefix or introduce a new versioned live-ledger prefix?
- Should plugin keys stay in `api_tokens`, or should live ingestion use a dedicated key table with tighter issuance, scope, quotas, and revocation metadata?
- Should first storage remain SQLite-first or introduce an abstraction compatible with a managed/Postgres future?
- Which telemetry classes are allowed for Dungeon Crawl export on day one, and which must remain raw/private only?
- Which reverse proxy and deployment controls will be considered part of acceptance proof for catherby.net public hosting?
