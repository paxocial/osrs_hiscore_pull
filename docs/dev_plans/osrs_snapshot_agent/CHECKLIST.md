# ✅ Acceptance Checklist — codex-osrs-snapshot
**Project:** codex-osrs-snapshot  
**Version:** v0.1

---

## Environment & Tooling
- [ ] `python3.11+` environment configured
- [ ] `requirements.txt` installed (`osrs-json-hiscores`, `python-dotenv`, `rich`)
- [ ] `.env` populated with `HISCORES_USER`, `HISCORES_INTERVAL_MIN`, `DATA_PATH`
- [ ] `config/project.json` updated with correct project name and log path

---

## Phase 0: Documentation & Logging Foundations
- [ ] `AGENTS.md`, `ARCHITECTURE_GUIDE.md`, `PHASE_PLAN.md`, `PROGRESS_LOG.md`, `CHECKLIST.md` completed and reviewed
- [ ] Scribe utility writes entries with status presets and metadata
- [ ] Progress log contains sample entries covering success and info statuses

---

## Phase 1: Snapshot Agent Delivery
- [ ] `agents/osrs_snapshot_agent.py` implements fetch, validate, persist workflow
- [ ] `main.py` loads config/env and executes a snapshot run with console feedback
- [ ] Snapshot files include metadata wrapper (player, timestamp, endpoint, agent version)
- [ ] Scribe logs success and error outcomes automatically during runs
- [ ] Unit tests cover filename generation, metadata assembly, and logging hooks

---

## Phase 2: Resilience & Multi-Account Support
- [ ] Retry/backoff strategy implemented for API calls with sensible defaults
- [ ] Batch configuration supports multiple usernames with concurrency cap ≤5
- [ ] Additional metrics (duration, status code) captured in Scribe metadata
- [ ] Operational runbook documented for scheduled execution

---

## Release Readiness
- [ ] Manual smoke test completed (fetch, snapshot saved, log entry written)
- [ ] Progress log reviewed for completeness (no manual edits)
- [ ] Outstanding TODOs documented in backlog or issue tracker
- [ ] Sign-off entry appended to progress log via Scribe
