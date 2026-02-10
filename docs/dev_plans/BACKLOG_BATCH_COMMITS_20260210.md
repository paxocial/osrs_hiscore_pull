# Backlog Batch Commits Plan

Date: 2026-02-10
Owner: Codex
Scope: Commit pending backlog in coherent batches with clear boundaries.

## Batch Strategy

1. Council and template scaffolding
   - `.council/*` (excluding runtime/secret artifacts)
   - `.claude/*`
   - `.mcp.json`
   - root `AGENTS.md`, `CLAUDE.md`
   - council/dev plan docs generated during bridge/runtime work

2. Plugin API schemas + endpoints
   - `api/schemas` package split
   - plugin endpoints and dependency auth/rate-limit updates
   - API router wiring
   - plugin/dependency tests

3. Web compare + UI pass
   - compare routes/services/templates/css/js
   - profile/clan/admin/base template and theme updates
   - startup script for OSRS backend launch from council workflows

4. Data and operational state updates
   - `config/mode_cache.json`
   - `docs/dev_plans/osrs_snapshot_agent/PROGRESS_LOG.md`
   - tracked SQLite runtime artifacts (`data/analytics.db*`) if intentionally included in backlog

## Guardrails

1. Exclude local-only artifacts not suitable for shared history by default:
   - `.scribe/`
   - `.council/.sync_state.json`
   - ignored files (`.env`, `*.log`, etc.)
2. Keep each commit independently reviewable.
3. Run focused validation before final commit completion.
