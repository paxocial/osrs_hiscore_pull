# Council OSRS Custom Page Implementation Plan

Date: 2026-02-10
Owner: Codex
Scope: Add Council custom pages that expose this repo's existing OSRS accounts and snapshot workflows inside Council Web UI.

## Objectives

1. Provide a usable Council page for account and snapshot operations without duplicating backend business logic.
2. Preserve the existing backend (`web.main` / `api.main`) as source of truth for accounts, snapshots, and job execution.
3. Support a practical operator workflow when backend and Council run on separate ports.

## Constraints

1. Council custom pages in this repo are template/static only (`.council/web/pages`, `.council/web/static`).
2. Council Web UI does not expose a generic project-defined process start/stop API by default.
3. Cross-origin API calls from Council page to backend require CORS (`CORS_ALLOWED_ORIGINS` must include Council URL, typically `http://localhost:8015`).

## Implementation Approach

### A) Create Custom Pages

1. Add `osrs-dashboard.html.j2` as primary command page.
2. Add `osrs-jobs.html.j2` and `osrs-snapshots.html.j2` as focused pages matching existing `chat.page_agents` mappings.
3. Use YAML frontmatter for nav label/order/grouping.

### B) Add Shared Static Assets

1. Add `osrs-control.css` for page layout and card/table styling.
2. Add `osrs-control.js` to implement:
   - backend URL persistence
   - health checks
   - account list/create
   - snapshot run
   - latest snapshot listing
   - embedded backend iframe control
   - Council process visibility (`/api/processes`)

### C) Integration Behavior

1. Prefer existing backend API endpoints:
   - `GET/POST /api/accounts/`
   - `POST /api/snapshots/run`
   - `GET /api/snapshots/latest`
2. Provide embedded fallback (`iframe`) to the existing backend web UI if API/CORS access is unavailable.
3. Surface clear operator instructions for startup commands and CORS configuration.

## Validation

1. Confirm page templates and static assets exist in expected `.council/web` paths.
2. Run `council update --from-yaml --dry-run` to ensure council config/template generation remains healthy.
3. Verify references to `osrs-atlas` remain slug-consistent.
4. Ensure no zero-diff edits; verify with `git status --short`.

## Deliverables

1. `.council/web/pages/osrs-dashboard.html.j2`
2. `.council/web/pages/osrs-jobs.html.j2`
3. `.council/web/pages/osrs-snapshots.html.j2`
4. `.council/web/static/css/osrs-control.css`
5. `.council/web/static/js/osrs-control.js`
6. Scribe progress entries for implementation and validation.
