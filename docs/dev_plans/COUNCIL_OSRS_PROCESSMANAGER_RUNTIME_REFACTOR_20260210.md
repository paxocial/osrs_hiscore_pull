# Council OSRS Runtime ProcessManager Refactor Plan

Date: 2026-02-10
Owner: osrs-atlas
Scope: Replace PID-file/process-scan runtime control with authenticated ProcessManager-backed control.

## Goals

1. Make OSRS runtime lifecycle fully ProcessManager-driven (`spawn`, `stop`, `get_status`).
2. Keep web authentication requirements unchanged.
3. Ensure `/api/processes` reflects OSRS runtime entries when web uses the SDK fallback ProcessManager.
4. Preserve current UI contract (`/api/osrs/runtime/status|start|stop` response shape).

## Implementation Steps

1. Refactor `src/council_mcp/web/routes/osrs_runtime.py`:
   - remove PID-file and `/proc` discovery logic.
   - add ProcessManager resolver (`process_manager` then `_sdk_process_manager` fallback).
   - use `ProcessType.PLUGIN` + metadata tag (`service=osrs_backend`) for OSRS runtime entries.
   - use `spawn()` for start and `stop()` for stop.
   - compute runtime status from `get_status()` entries.
2. Update `src/council_mcp/web/routes/system.py`:
   - make `/api/processes` read from `_sdk_process_manager` when `process_manager` is `None`.
3. Update `scripts/start_osrs_backend.sh`:
   - support optional `OSRS_BACKEND_LOG_PATH` redirection for ProcessManager launches.
4. Validate:
   - syntax checks for patched Python and JS/bash checks.
   - browser verification of start/stop/status and `/api/processes`.

## Constraints

1. In some run modes, daemon-owned ProcessManager is not attached to web app state; fallback manager must be used.
2. ProcessManager currently tracks OSRS backend under `plugin` type with metadata filter.
3. Keep diffs focused to avoid regressions in unrelated Council routes.
