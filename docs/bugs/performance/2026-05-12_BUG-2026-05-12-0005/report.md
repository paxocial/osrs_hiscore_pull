
# 🐞 Council static OSRS icons lack cache headers and async decode hints — osrs_prod_audit_integrate_20260512
**Author:** Scribe
**Version:** v0.1
**Status:** PARTIAL LOCAL FIX / PACKAGE BLOCKED
**Last Updated:** 2026-05-12 06:51:24 UTC

This report captures the split RCA for slow OSRS icon loading: the cache-header defect is owned by the Council MCP `/council-static` route, while this repo owns the client-side icon markup that can reduce image decode/load contention.

---
## Bug Overview
<!-- ID: bug_overview -->
**Bug ID:** BUG-2026-05-12-0005

**Reported By:** mantis

**Date Reported:** 2026-05-12 06:51:24 UTC

**Severity:** HIGH

**Status:** PARTIAL LOCAL FIX / PACKAGE BLOCKED

**Component:** Council custom static OSRS pages

**Environment:** local Council web / future catherby.net public site

**Customer Impact:** Slow repeated icon requests degrade OSRS snapshot/detail/comparison pages in local Council and would make the future catherby.net public UI feel blocked or unreliable during first content inspection.


---
## Description
<!-- ID: description -->
### Summary
Operator observed many `/council-static/img/game/game_icon_*.png` requests during OSRS page load/render taking roughly 1.3s-3.2s each, appearing slow, uncached, and potentially blocking core snapshot/history UI readiness.

### Expected Behaviour
Stable OSRS icon URLs should use browser cache best practices, and client-rendered icon images should not block core snapshot/history UI loading or force synchronous decode/layout work during icon-heavy renders.

### Actual Behaviour
The current Council MCP static route returns a plain `FileResponse` for each `/council-static` file and does not set explicit `Cache-Control` policy for immutable static assets. Repo-local icon helpers already used `loading="lazy"`, but they lacked `decoding="async"`, `fetchpriority="low"`, and intrinsic dimensions.

### Steps to Reproduce
- [x] Load or render an OSRS Council page/detail/comparison path that produces many game icon tags.
- [x] Observe or use logged evidence that many `/council-static/img/game/game_icon_*.png` requests take seconds during render.
- [x] Inspect Council MCP static route source and repo-local icon rendering helpers.



---
## Investigation
<!-- ID: investigation -->
**Root Cause Analysis:**
Confirmed split root cause:

1. Static-serving owner is outside this repo. `/council-static/{file_path}` is implemented in `/home/austin/projects/MCP_SPINE/council_mcp/src/council_mcp/web/routes/pages.py` by `council_static_file`, which resolves the active council repo and returns `FileResponse(path=full_path, media_type=content_type)` without explicit cache policy. That leaves browser behavior dependent on default validators/revalidation rather than an intentional max-age/immutable static asset policy.
2. Repo-local OSRS icon helpers in `.council/web/static/js/osrs-common.js` generated many image tags with only `loading="lazy"`. They did not tell the browser to decode asynchronously, deprioritize fetches, or reserve intrinsic 20x20 dimensions before image bytes arrive.
3. First-render page templates do not embed all game icons directly; bulk game icon requests are produced when JS inserts snapshot detail/activity/comparison content. The UI should therefore keep core tables/history usable while those icons load.

**Affected Areas:**
- .council/web/static/js/osrs-common.js
- /home/austin/projects/MCP_SPINE/council_mcp/src/council_mcp/web/routes/pages.py


**Related Issues:**
- Scribe progress entries for `STATIC-ICON-CACHE-NONBLOCKING`.
- Council MCP owner path: `/home/austin/projects/MCP_SPINE/council_mcp/src/council_mcp/web/routes/pages.py:546`.


---
## Resolution Plan
<!-- ID: resolution_plan -->
### Immediate Actions
- [x] Repo-local fix: update `.council/web/static/js/osrs-common.js` so `renderSkillIcon` and `renderGameIcon` emit `width="20"`, `height="20"`, `loading="lazy"`, `decoding="async"`, and `fetchpriority="low"`.
- [x] Add recurrence guard `tests/test_osrs_icon_markup.py`.
- [ ] Package-owner fix still required: Council MCP should add a cache policy for `/council-static` assets, ideally long-lived for stable static URLs or conditional by asset type/path. This repo should not edit that package source without explicit owner approval.


### Long-Term Fixes
- [ ] In Council MCP, update `council_static_file` to set explicit `Cache-Control` headers for custom static assets and preserve validator behavior (`ETag`/`Last-Modified`) from `FileResponse`.
- [ ] Consider unauthenticated/public static serving or a public-site static pipeline for catherby.net if those assets do not need operator auth; the current route depends on `get_current_user_or_redirect`.
- [ ] Add package-level tests in `/home/austin/projects/MCP_SPINE/council_mcp/tests/test_council_static.py` for cache headers and conditional request behavior.

### Testing Strategy
- [x] RED: `pytest tests/test_osrs_icon_markup.py -v` failed before the JS fix because `decoding="async"` was missing.
- [x] GREEN: `pytest tests/test_osrs_icon_markup.py -v` passed after the JS fix.
- [x] Syntax/import smoke: `node --check .council/web/static/js/osrs-common.js` passed; `python -c "import tests.test_osrs_icon_markup as t; assert t.ICON_HELPERS.exists()"` passed.
- [x] Live read-only probes: `HEAD` to `/council-static/...` returns 405 and unauthenticated `GET` redirects to login on port 8015, so authenticated header/timing proof was not completed in this lane.
- [ ] Package-owner verification still required after Council MCP cache-header fix: authenticated `GET -D -` should show intentional `Cache-Control`, `ETag` or `Last-Modified`, and repeat/conditional requests should avoid full file work.


---
## Timeline & Ownership
<!-- ID: timeline -->
| Phase | Owner | Target Date | Notes |
| --- | --- | --- | --- |
| Investigation | Mantis | 2026-05-12 | Mapped repo-local page/JS sources and read-only Council MCP static route owner. |
| Fix Development | Mantis | 2026-05-12 | Applied repo-local image markup fix only; did not edit Council MCP package source. |
| Testing | Mantis | 2026-05-12 | RED/GREEN focused test, JS syntax check, Python import smoke. |
| Deployment | Council MCP package owner | BLOCKED | Required cache-header fix is outside this repo. |


---
## Appendix
<!-- ID: appendix -->
- **Logs & Evidence:** Active Scribe project `osrs_prod_audit_integrate_20260512`, entries tagged `static-icons`.
- **Fix References:** `.council/web/static/js/osrs-common.js:350`; `tests/test_osrs_icon_markup.py`.
- **Open Questions:** Exact public-site cache policy and authentication boundary for catherby.net static OSRS assets must be decided in Council MCP/public deployment owner context.


---
