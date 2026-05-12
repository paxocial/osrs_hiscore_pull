---
id: osrs_prod_audit_integrate_20260512-bug-2026-05-12-0001
title: "\U0001F41E Snapshot run API 500s when clipboard helper cannot spawn clip.exe\
  \ \u2014 osrs_prod_audit_integrate_20260512"
doc_type: BUG-2026-05-12-0001
doc_name: BUG-2026-05-12-0001
category: engineering
status: diagnosed
version: '0.1'
last_updated: 2026-05-12 05:02:24 UTC
maintained_by: agent-20260512-045153-6aaf4c18
created_by: agent-20260512-045153-6aaf4c18
owners: []
related_docs:
- .scribe/docs/dev_plans/osrs_prod_audit_integrate_20260512/research/research_RESEARCH_R1B_SNAPSHOT_RCA.md
tags: []
summary: 'Confirmed snapshot-run 500 root cause: optional clipboard copy raises FileNotFoundError
  for missing clip.exe and escapes backend request path.'
edit_trace:
  tool: manage_docs
  created_at: 2026-05-12 04:59:34 UTC
  created_via: replace_section
  last_edited_at: 2026-05-12 05:02:24 UTC
  last_edited_by: agent-20260512-045153-6aaf4c18
  last_action: frontmatter_update
---

# 🐞 Snapshot run API 500s when clipboard helper cannot spawn clip.exe — osrs_prod_audit_integrate_20260512
**Author:** Scribe
**Version:** v0.1
**Status:** DIAGNOSED
**Last Updated:** 2026-05-12 04:58:40 UTC

> Documents the confirmed root cause for the port 8001 snapshot-run 500 and hands a minimal fix boundary to planning/implementation.

---
## Bug Overview
<!-- ID: bug_overview -->
## Bug Overview

**Bug ID:** BUG-2026-05-12-0001

**Reported By:** mantis

**Date Reported:** 2026-05-12 04:58:40 UTC

**Severity:** HIGH

**Status:** DIAGNOSED

**Component:** snapshot-run

**Environment:** local port 8001 backend runtime under Council OSRS plugin

**Customer Impact:** Snapshot collection is blocked from the Council OSRS UI and any backend caller using `POST /api/snapshots/run` with a valid player body when the runtime lacks a working clipboard provider. The backend may fetch and write a JSON snapshot before the clipboard exception, but the API still returns 500, so callers see failure and downstream UI refresh/reporting/database ingest after the agent call may not run.
## Description
<!-- ID: description -->
## Description

### Summary
`POST /api/snapshots/run` on backend port 8001 returns 500 for a valid JSON body such as `{"player":"Lynx Titan","mode":"auto"}`. Council proxy path `/api/osrs/snapshots/run` mirrors the backend 500. Backend log traceback ends in `core.clipboard.copy_text -> pyperclip.copy -> FileNotFoundError: No such file or directory: clip.exe`.

### Expected Behaviour
Snapshot run should return a structured results response after fetch, persistence, and reporting. Optional clipboard export must never be required for server-side API success.

### Actual Behaviour
The request returns HTTP 500 with `{"error":"internal_error","message":"An unexpected error occurred. Please try again later."}`. The backend traceback shows the snapshot agent reached the clipboard-copy side effect after writing the snapshot JSON, then crashed because `clip.exe` is unavailable in the runtime environment.

### Steps to Reproduce
- Confirm backend is reachable: `curl -sS -i --max-time 10 http://127.0.0.1:8001/api/health` returns 200.
- Reproduce: `curl -sS -i --max-time 90 -X POST http://127.0.0.1:8001/api/snapshots/run -H 'Content-Type: application/json' --data '{"player":"Lynx Titan","mode":"auto"}'`.
- Observe HTTP 500 JSON error body and backend traceback in `.council/osrs_backend.log` ending at `pyperclip.copy` spawning missing `clip.exe`.
## Investigation
<!-- ID: investigation -->
## Investigation

**Root Cause Analysis:**
`SnapshotAgent.run` calls `copy_json_snippet` unconditionally after writing the snapshot payload. `core/clipboard.copy_text` catches only `pyperclip.PyperclipException`; in this runtime `pyperclip.copy` attempts to spawn `clip.exe` and raises `FileNotFoundError`, which is not caught. The exception escapes the worker thread and FastAPI returns 500.

**Affected Areas:**
- `api/endpoints/snapshots.py`: `run_snapshots` calls `_run_snapshots`, which calls `SnapshotAgent.run` in an AnyIO worker thread.
- `agents/osrs_snapshot_agent.py`: line 196 performs optional clipboard export after writing the snapshot JSON and before appending the successful `SnapshotResult`.
- `core/clipboard.py`: lines 19-22 catch only `pyperclip.PyperclipException`, leaving `FileNotFoundError` from the WSL `clip.exe` provider uncaught.

**Related Issues:**
- R1-B research artifact: `.scribe/docs/dev_plans/osrs_prod_audit_integrate_20260512/research/research_RESEARCH_R1B_SNAPSHOT_RCA.md`.
- Council proxy log confirms mirrored 500 at `/api/osrs/snapshots/run` at 2026-05-12T04:40:54Z, 04:41:06Z, and 04:41:36Z.
## Resolution Plan
<!-- ID: resolution_plan -->
## Resolution Plan

### Immediate Actions
- No implementation performed in R1-B.
- Minimal fix package should make clipboard export non-fatal in backend/server contexts.
- Candidate repair surfaces: catch `OSError`/unexpected clipboard-provider failures in `core/clipboard.copy_text`, or make `SnapshotAgent` skip clipboard side effects when called from API/runtime execution.

### Long-Term Fixes
- Separate interactive desktop conveniences such as clipboard copy from server-side snapshot orchestration.
- Ensure snapshot-run API failure semantics distinguish fetch/not-found/user errors from optional local-environment conveniences.

### Testing Strategy
- Add a unit or API-level regression where `pyperclip.copy` raises `FileNotFoundError`; expected result is a successful snapshot result or, at minimum, no HTTP 500 from clipboard failure.
- Add/import-smoke coverage for `core.clipboard.copy_text` if the fix lands there.
- Add a direct backend API probe after the fix: valid `POST /api/snapshots/run` returns 200 with one result and no new `clip.exe` traceback in `.council/osrs_backend.log`.
## Timeline & Ownership
<!-- ID: timeline -->
## Timeline & Ownership

| Phase | Owner | Target Date | Notes |
| --- | --- | --- | --- |
| Investigation | Mantis | 2026-05-12 | Direct backend reproduction, proxy-log correlation, and source traceback completed. |
| Fix Development | Forge | After Wave 1 synthesis and Blueprint planning | Not started in R1-B; minimal fix package should target optional clipboard failure boundary. |
| Testing | Crucible or package owner | After fix package | Validate regression test and direct port 8001 probe. |
| Deployment | Atlas or deployment owner | After validated fix | Outside R1-B scope. |
## Appendix
<!-- ID: appendix -->
## Appendix

- **Logs & Evidence:** `.council/osrs_backend.log` contains the direct traceback from the 2026-05-12 00:56 EDT reproduction; `/home/austin/projects/MCP_SPINE/council_mcp/web_ui.log` lines 29336-29350 and 29453-29454 contain prior Council proxy 500s.
- **Fix References:** None yet. R1-B is diagnose-only and did not modify source.
- **Open Questions:** Whether the eventual fix should live only in `core/clipboard.py` or also make `SnapshotAgent` explicitly configurable for interactive versus server runtime. Blueprint/Forge should decide after Wave 1 synthesis.
