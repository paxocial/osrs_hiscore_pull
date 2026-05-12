---
id: osrs_prod_audit_integrate_20260512-bug-2026-05-12-0002
title: "\U0001F41E Snapshot API run bypasses history/report materialization \u2014\
  \ osrs_prod_audit_integrate_20260512"
doc_type: BUG-2026-05-12-0002
doc_name: BUG-2026-05-12-0002
category: engineering
status: ready
version: '0.1'
last_updated: 2026-05-12 06:21:08 UTC
maintained_by: agent-20260512-060448-00b69c00
created_by: agent-20260512-060448-00b69c00
owners: []
related_docs: []
tags: []
summary: ''
edit_trace:
  tool: manage_docs
  created_at: 2026-05-12 06:17:30 UTC
  created_via: replace_section
  last_edited_at: 2026-05-12 06:21:08 UTC
  last_edited_by: agent-20260512-060448-00b69c00
  last_action: replace_section
bug_status: fixed
case_id: BUG-2026-05-12-0002
---

# 🐞 Snapshot API run bypasses history/report materialization — osrs_prod_audit_integrate_20260512
**Author:** Scribe
**Version:** v0.1
**Status:** INVESTIGATING
**Last Updated:** 2026-05-12 06:10:34 UTC

> Summarise why this document exists and what decisions it captures.

---
## Bug Overview
<!-- ID: bug_overview -->
**Bug ID:** BUG-2026-05-12-0002

**Reported By:** mantis

**Date Reported:** 2026-05-12 06:10:34 UTC

**Severity:** CRITICAL

**Status:** INVESTIGATING

**Component:** snapshot-api

**Environment:** local live backend via Council proxy

**Customer Impact:** Users cannot confirm successful snapshot runs, browse newly generated snapshots, or open generated reports from the UI.


---
## Description
<!-- ID: description -->
### Summary
Frontend/Council page shows snapshot run success, but the new snapshot does not appear in latest/history and no markdown report is generated or discoverable. Operator live evidence shows POST /api/osrs/snapshots/run returned 200 followed by GET /api/osrs/snapshots/latest?limit=25 returning 502 through the Council proxy.

### Expected Behaviour
A successful snapshot run from the API must persist the snapshot into the database used by latest/history, generate a markdown report at the report path exposed by the API, and latest/history serialization must not crash on valid run metadata such as requested_mode=auto.

### Actual Behaviour
Frontend/Council page shows snapshot run success, but the new snapshot does not appear in latest/history and no markdown report is generated or discoverable. Operator live evidence shows POST /api/osrs/snapshots/run returned 200 followed by GET /api/osrs/snapshots/latest?limit=25 returning 502 through the Council proxy.

### Steps to Reproduce
- [ ] POST to /api/snapshots/run with a valid player/mode through the backend or Council proxy.
- [ ] Refresh /api/snapshots/latest?limit=25.
- [ ] Attempt to open /api/snapshots/{snapshot_id}/report for the run result.



---
## Investigation
<!-- ID: investigation -->
**Root Cause Analysis:**

The API run route returned successful `SnapshotAgent` results without running the existing materialization steps. `SnapshotAgent` writes JSON artifacts under `data/snapshots`, but `/api/snapshots/latest`, detail lookup, raw payload, and report discovery are backed by SQLite rows and markdown files under `reports`. The job-worker path already used `SnapshotIngestService` and `ReportAgent`; the API route bypassed both.

**Evidence:**

- Operator logs: POST `/api/osrs/snapshots/run` returned 200, followed by Council proxy GET `/api/osrs/snapshots/latest?limit=25` returning 502.
- Direct backend read-only probe: `/api/snapshots/latest?limit=25` returned 200, but newest DB row remained `2026-03-04T09:07:30Z`.
- Filesystem readback: May 12 JSON artifacts existed under `data/snapshots`; no May 12 markdown reports existed under `reports`.
- RED test: a successful fake API run produced no latest/history row before the fix.

**Affected Areas:**

- `api/endpoints/snapshots.py`
- `web/services/snapshot_ingest.py`
- `agents/report_agent.py`
- `core/report_builder.py`
- `tests/test_snapshot_api_materialization.py`

**Related Issues:**

- Distinct from HOTFIX-SNAPSHOT-CLIPBOARD; that fix prevents clipboard backend failures from aborting runs, while this bug fixes post-run materialization into history/report stores.
## Resolution Plan
<!-- ID: resolution_plan -->
### Immediate Actions
Fix landed with status: **working_tree_verified**

### Fix Details
- Artifact: tests/test_snapshot_api_materialization.py:68
- Execution ID: c3c04f11-ce4c-459c-828a-26945092f6d8
## Timeline & Ownership
<!-- ID: timeline -->
| Phase | Owner | Target Date | Notes |
| --- | --- | --- | --- |
| Investigation | Mantis | 2026-05-12 | Source/log/readback RCA proved API run bypassed DB/report materialization. |
| Fix Development | Mantis | 2026-05-12 | Patched `api/endpoints/snapshots.py`; added regression test; fixed adjacent report total-XP contract. |
| Testing | Mantis | 2026-05-12 | Targeted and neighbor tests passed; import smoke passed. |
| Deployment | Operator / deployment lane | Pending runtime refresh | No restart/reload performed by instruction; live process still needs source refresh before live proof. |
## Appendix
<!-- ID: appendix -->
- **Fix Reference:** tests/test_snapshot_api_materialization.py:68 (execution: c3c04f11-ce4c-459c-828a-26945092f6d8)
- **Landing Status:** working_tree_verified
- **Fix Linked By:** mantis
<!-- ID: symptoms -->
- Frontend/Council snapshot run can return success, but the newly generated run is absent from latest/history.
- Operator live evidence at 2026-05-12 02:03 EDT: backend POST `/api/snapshots/run` returned 200, then Council proxy GET `/api/osrs/snapshots/latest?limit=25` returned 502.
- Direct live backend readback after RCA showed `/api/snapshots/latest?limit=25` returns 200 but newest DB row is still `2026-03-04T09:07:30Z`.
- Filesystem readback showed May 12 JSON artifacts under `data/snapshots`, but no May 12 markdown reports under `reports`.
- User-visible result: snapshots appear to run but do not show in history and reports are not made/discoverable.

<!-- ID: root_cause -->
`api/endpoints/snapshots.py::_run_snapshots` called `SnapshotAgent.run()` and returned converted results only. `SnapshotAgent` writes JSON artifacts under `data/snapshots`, but `/api/snapshots/latest` and detail/report discovery are backed by SQLite `snapshots` rows and markdown files under `reports`. The API run path bypassed the existing `SnapshotIngestService` and `ReportAgent` materialization path already used by `web/services/job_worker.py`, so successful API runs persisted into a store the UI does not list and did not generate report files.

<!-- ID: fix -->
- Updated `api/endpoints/snapshots.py` so `_run_snapshots` constructs and reuses `SnapshotIngestService` after each successful `SnapshotAgent` result.
- The route now inserts successful run payloads into SQLite before returning, keeping `/api/snapshots/latest` and history aligned with API-triggered runs.
- The route now generates markdown reports through `ReportAgent(Path("reports"))`, matching the existing job-worker report path used by `/api/snapshots/{snapshot_id}/report`.
- Added `tests/test_snapshot_api_materialization.py` as a regression guard for run -> latest/history -> report materialization.
- Fixed adjacent report output in `core/report_builder.py` so the existing report total-XP contract passes during neighbor verification.

<!-- ID: verification -->
- RED proof: `pytest tests/test_snapshot_api_materialization.py -v` failed before the API route fix because latest/history returned `[]` after a successful fake run.
- GREEN proof: `pytest tests/test_snapshot_api_materialization.py -v` passed after the fix.
- Neighbor verification: `pytest tests/test_snapshot_api_materialization.py tests/test_snapshot_agent.py tests/test_report_agent.py tests/test_report_builder.py tests/test_scribe_reporter.py -v` -> 12 passed, 1 warning.
- API dependency neighbor: `pytest tests/test_api_dependencies.py -v` -> 8 passed, 1 warning.
- Import smoke: `/home/austin/miniconda3/envs/uap/bin/python -c 'from api.endpoints.snapshots import _run_snapshots, get_latest_snapshots, get_snapshot_report; from core.report_builder import build_report_content, _total_xp; import tests.test_snapshot_api_materialization'` -> passed.
- Live status: no restart/reload was performed. Direct backend 8001 latest is readable but still runtime-stale for the source fix; Council web port 8000 was not listening during read-only probe.
