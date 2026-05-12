
# 🐞 Report delta math double-counts Overall skill delta — osrs_prod_audit_integrate_20260512
**Author:** Scribe
**Version:** v0.1
**Status:** RESOLVED
**Last Updated:** 2026-05-12 06:42:40 UTC

This bug report documents the report delta aggregate defect where the synthetic OSRS `Overall` row was counted alongside per-skill rows, doubling total XP gain summaries and causing `Overall` to appear as a player-facing skill highlight.

---
## Bug Overview
<!-- ID: bug_overview -->
**Bug ID:** BUG-2026-05-12-0003

**Reported By:** mantis

**Date Reported:** 2026-05-12 06:35:38 UTC

**Severity:** HIGH

**Status:** RESOLVED

**Component:** report delta calculation

**Environment:** generated report

**Customer Impact:** Player report summaries overstate XP gains by counting Overall plus per-skill XP and surface Overall as a misleading skill-level highlight.


---
## Description
<!-- ID: description -->
### Summary
Generated Flamelborn ironman report renders Changes summary `ΔXP 9,352,828` while the detailed skill deltas contain `Overall +4,676,414` and non-Overall skill deltas that also sum to 4,676,414. The summary also highlights `Levels Overall (+169)`, which is not a player-facing skill gain highlight.

### Expected Behaviour
`total_xp_delta` should prefer the Overall XP delta when present, fall back to summing non-Overall skill deltas when Overall is absent, and report-facing skill gain highlights should exclude Overall.

### Actual Behaviour
Generated Flamelborn ironman report renders Changes summary `ΔXP 9,352,828` while the detailed skill deltas contain `Overall +4,676,414` and non-Overall skill deltas that also sum to 4,676,414. The summary also highlights `Levels Overall (+169)`, which is not a player-facing skill gain highlight.

### Steps to Reproduce
- [x] Build a delta where `skill_deltas` includes `Overall` with `xp_delta=4,676,414` and non-Overall skill deltas summing to `4,676,414`.
- [x] Render report Changes summary from that delta.
- [x] Observe summary `ΔXP` is doubled if total_xp_delta was computed from all skill XP rows, and observe `Overall` appears in level highlights when it has a positive level_delta.



---
## Investigation
<!-- ID: investigation -->
**Root Cause Analysis:**
`core.processing.compute_snapshot_delta` computed `total_xp_delta` by summing every skill XP row in previous and current snapshots. OSRS hiscore payloads include `Overall` as an aggregate row plus individual skill rows, so summing all rows counts the same XP twice. Separately, `core.processing.summarize_delta` and `core.report_builder._summarize_delta` selected highlight skills from raw `skill_deltas` without excluding `Overall`, allowing the aggregate row to lead `Levels` or `XP` highlights.

**Affected Areas:**
- core/processing.py
- core/report_builder.py
- tests/test_processing.py
- tests/test_report_builder.py


**Related Issues:**
- Adjacent package HOTFIX-REPORT-TOTAL-XP fixed header Total XP semantics in `core/report_builder.py`; this case covers delta math and summary highlights only.


---
## Resolution Plan
<!-- ID: resolution_plan -->
### Immediate Actions
- [x] Add Flamelborn-shaped RED regressions for doubled `total_xp_delta` and `Levels Overall` summary output.
- [x] Change `compute_snapshot_delta` to derive total XP delta from Overall when present and fall back to non-Overall sums when absent.
- [x] Exclude `Overall` from processing/report summary highlight selection.
- [x] Preserve the detailed Changes table Overall row to retain existing report detail behavior.


### Long-Term Fixes
- [x] No broader refactor required for this hotfix; recurrence coverage now guards the aggregate and summary contracts.

### Testing Strategy
- [x] Focused RED/GREEN package tests: `pytest tests/test_processing.py tests/test_report_builder.py -v`.
- [x] Direct-neighbor tests: `pytest tests/test_report_agent.py tests/test_scribe_reporter.py tests/test_snapshot_agent.py tests/test_snapshot_api_materialization.py -q`.
- [x] Import smoke: `python -c "from core.processing import compute_snapshot_delta, summarize_delta; from core.report_builder import build_report_content, _summarize_delta"`.


---
## Timeline & Ownership
<!-- ID: timeline -->
| Phase | Owner | Target Date | Notes |
| --- | --- | --- | --- |
| Investigation | mantis | 2026-05-12 | Reproduced doubled delta and Overall highlight with focused RED tests. |
| Fix Development | mantis | 2026-05-12 | Patched `core/processing.py` and `core/report_builder.py`. |
| Testing | mantis | 2026-05-12 | Focused package tests, direct-neighbor tests, and import smoke passed. |
| Deployment | operator | TBD | No deployment or runtime reload performed in this package. |


---
## Appendix
<!-- ID: appendix -->
- **Logs & Evidence:** Scribe progress entries for HOTFIX-REPORT-DELTA-OVERALL include RED failure (`2 failed, 13 passed`) and GREEN verification (`15 passed`, neighbor `4 passed, 1 warning`, import smoke passed).
- **Fix References:** `core/processing.py`, `core/report_builder.py`, `tests/test_processing.py`, `tests/test_report_builder.py`.
- **Open Questions:** Live/generated report artifacts created before this hotfix may remain stale until regenerated or runtime services reload the current source.


---
