# ⚙️ Phase Plan — codex-osrs-snapshot
**Project:** codex-osrs-snapshot  
**Version:** Draft v0.1  
**Author:** CortaLabs  
**Last Updated:** 2025-10-20 04:05 UTC

---

## Phase 0 – Repository Initialization
**Objective:**  
Stand up the project scaffold, baseline documentation, and shared tooling needed for iterative development.

**Key Tasks:**
- [x] Establish `AGENTS.md`, architecture guide, progress log, and phase plan.
- [x] Create `config/project.json` with project metadata.
- [x] Implement the Scribe logging utility and verify log formatting.
- [ ] Confirm dependency availability (`osrs-json-hiscores`, `python-dotenv`, `rich`) and add `requirements.txt`.

**Deliverables:**
- Core documentation under `docs/dev_plans/osrs_snapshot_agent/`.
- Working `scripts/scribe.py` utility and example log entries.
- Repository structure aligned with agent expectations.

**Acceptance Criteria:**
- [ ] Scribe writes formatted log entries to the configured progress file.
- [ ] Documentation references match actual paths and tools.
- [ ] Environment configuration instructions validated on a clean setup.

**Dependencies:**  
None.

**Confidence:** 0.80

---

## Phase 1 – Snapshot Agent Implementation
**Objective:**  
Build the SnapshotAgent capable of fetching OSRS hiscore JSON for a single player, persisting snapshots deterministically, and recording runs via Scribe.

**Key Tasks:**
- [ ] Implement `agents/osrs_snapshot_agent.py` with fetch, validate, and save workflows.
- [ ] Create `main.py` runner that loads config/env, invokes the agent, and outputs status via Rich.
- [ ] Ensure snapshots include metadata wrapper and write to `data/snapshots/<player>/`.
- [ ] Integrate Scribe calls for success and error outcomes with relevant metadata (duration, result).
- [ ] Add initial unit tests for filename generation and logging hooks.

**Deliverables:**
- Functional agent module and runnable entrypoint.
- Sample snapshot files and logged entries demonstrating success/error handling.
- Test coverage for core utility functions.

**Acceptance Criteria:**
- [ ] Running `python main.py` fetches and stores a snapshot for the configured user.
- [ ] Progress log contains automated entries for each run with correct status emoji.
- [ ] Tests pass locally (or documented manual verification if live API access restricted).

**Dependencies:** Phase 0 completion.

**Confidence:** 0.70

---

## Phase 2 – Resilience & Multi-Account Support
**Objective:**  
Improve robustness, allow multiple accounts or scheduled runs, and prepare groundwork for future integrations.

**Key Tasks:**
- [ ] Add retry/backoff handling for API errors and rate limits.
- [ ] Support batch configuration (list of usernames, interval hints) with concurrency cap ≤5.
- [ ] Extend metadata to include runtime metrics (duration, response status).
- [ ] Document operational runbooks and update `CHECKLIST.md`.
- [ ] Evaluate packaging requirements (CLI flags, config options) for deployment.

**Deliverables:**
- Enhanced agent supporting multiple accounts.
- Updated documentation covering configuration and run workflows.
- Revised tests covering retries and multi-account behaviour.

**Acceptance Criteria:**
- [ ] Batch runs produce snapshots for each configured user without violating concurrency limits.
- [ ] Failure scenarios produce warning/error Scribe entries with actionable metadata.
- [ ] Updated checklist reflects deployment readiness and manual QA steps.

**Dependencies:** Phase 1 completion.

**Confidence:** 0.60

---

## Phase 3 – Optional Integrations (Backlog)
**Objective:**  
Outline future enhancements beyond initial release.

**Key Tasks:**
- [ ] Integrate snapshot summaries with analytics or vector storage.
- [ ] Implement diffing between consecutive snapshots.
- [ ] Add optional encryption/compression for long-term storage.
- [ ] Hook into scheduling/orchestration tooling (cron, Airflow, internal agents).

**Deliverables:**
- Backlog items captured in future planning docs.
- Prototype scripts as time permits.

**Acceptance Criteria:**
- [ ] Requirements refined and prioritised alongside broader roadmap.

**Dependencies:** Phase 2 completion.

**Confidence:** 0.40
