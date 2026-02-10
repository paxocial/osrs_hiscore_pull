# Council OSRS Runtime Route + UI Pass Plan

Date: 2026-02-10
Owner: osrs-atlas
Scope: Let Council manage this repo's backend runtime from a custom page and align the page style with Command Center.

## Goals

1. Add a small Council API route for OSRS backend lifecycle management (status/start/stop), modeled after VoiceLab runtime.
2. Wire OSRS custom page JS to use authenticated Council API calls so process/runtime requests do not fail with 401.
3. Align OSRS custom page CSS tokens and component styling with `http://localhost:8015/command-center` visual language.
4. Keep existing OSRS backend API/server behavior intact and reusable.

## Implementation Steps

1. Review `voicelab_runtime.py` and route registration in Council MCP to copy the runtime-management pattern safely.
2. Add `osrs_runtime.py` in Council MCP routes with:
   - `GET /api/osrs/runtime/status`
   - `POST /api/osrs/runtime/start`
   - `POST /api/osrs/runtime/stop`
3. Register the new router in Council route bootstrap.
4. Add local startup script in this repo (`scripts/start_osrs_backend.sh`) for deterministic launch command.
5. Update `.council/web/static/js/osrs-control.js` to:
   - include Council auth headers (`window.API.getAuthHeaders()`) for Council API calls
   - call OSRS runtime endpoints for lifecycle controls
   - keep existing backend direct API controls for account/snapshot actions
6. Update `.council/web/static/css/osrs-control.css` to mirror Command Center token usage:
   - typography (`Outfit` + heading variable)
   - background/surface/accent token family
   - panel/card/table/button styling consistency
7. Validate syntax + quick runtime checks:
   - Python compile check for new Council route
   - spot-check page behavior in browser
   - verify non-zero diffs for edited files

## Constraints

1. Council repo is outside current writable root, so edits there require escalated permissions.
2. OSRS page still depends on backend CORS settings for cross-origin direct backend calls.
3. Lifecycle controls should fail clearly if runtime manager or command paths are unavailable.

## Deliverables

1. `src/council_mcp/web/routes/osrs_runtime.py` (Council repo)
2. `src/council_mcp/web/routes/__init__.py` update (Council repo)
3. `scripts/start_osrs_backend.sh` (this repo)
4. `.council/web/static/js/osrs-control.js`
5. `.council/web/static/css/osrs-control.css`
6. Scribe logs for plan start, implementation, and validation checkpoints
