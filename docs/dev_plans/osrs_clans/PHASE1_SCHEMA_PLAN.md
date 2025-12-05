# Phase 1 — Clans Schema & API Plan

Goal: lock the data model, API surface, and UI contracts for clans: batch snapshots, aggregates, leaderboards, contests (provably fair), and Discord hooks. Grounded in snapshot payloads (skills, activities/bosses/clues, deltas, totals, latency, mode, timestamps).

## Data Model (proposed tables)

### Core clan
- `clans` (id, name, slug, created_by, created_at, updated_at, default_snapshot_mode, timezone, description)
- `clan_members` (id, clan_id, account_id, role enum: leader/officer/member, joined_at, is_active)
- `clan_schedules` (id, clan_id, cron, max_daily_runs (cap 2), enabled, next_run_at, last_run_status, last_error)
- `clan_webhooks` (id, clan_id, url, provider enum (discord/slack/custom), events json, last_status_code, last_error, created_at)

### Snapshots & aggregates
- `clan_snapshots` (id, clan_id, job_id, started_at, finished_at, status, latency_ms, error, member_count, mode, requested_by)
- `clan_snapshot_members` (id, clan_snapshot_id, account_id, snapshot_id, status, error)  // traces member snapshot results
- `clan_stats` (id, clan_id, timeframe enum (7d/30d/mtd/custom), start_at, end_at, generated_at, payload jsonb)  // cached aggregates (totals + deltas)
  - payload shape: totals (xp, levels), per-skill xp/levels gained, per-activity deltas (boss kc, clues), top performers, slackers.

### Contests
- `contests` (id, clan_id, name, status enum draft/active/ended/drawn, start_at, end_at, prize text, description, seed_commitment, seed_reveal, nonce, hash_fn, created_by, created_at, updated_at)
- `contest_rules` (id, contest_id, type enum (skill_xp, skill_levels, total_xp, boss_kc, clue_count), targets json (skills/activities list), threshold int, comparator (>=), timeframe enum (during_contest), weight int default 1, title)
- `contest_entries` (id, contest_id, rule_id, account_id, entry_count int default 1, proof json (snapshot_ids, deltas), created_at)
- `contest_draws` (id, contest_id, drawn_at, winner_account_id, winner_entry_id, seed_reveal, nonce, rng_proof json, notes)

### Leaderboards cache (optional for perf)
- `clan_leaderboards` (id, clan_id, metric enum (xp_gained, levels_gained, skill_xp, boss_kc, clues), timeframe enum, generated_at, rows jsonb)

## Metrics available from snapshots (for rules/leaderboards)
- Totals: `total_xp`, `total_level`, `resolved_mode`, `latency_ms`, `fetched_at`.
- Skills: level + xp per skill; deltas per skill (xp_delta, level_delta).
- Activities: bosses, clues, minigames, other; per-activity score and delta.
- Time delta: hours between snapshots to allow rate (xp/hour) later if needed.

## API Surface (draft)

### Clans
- GET `/api/clans` (list user’s clans)
- POST `/api/clans` (create clan)
- GET `/api/clans/{clan_id}` (detail + latest stats)
- POST `/api/clans/{clan_id}/members` (add member)
- PATCH `/api/clans/{clan_id}/members/{account_id}` (role/update)
- DELETE `/api/clans/{clan_id}/members/{account_id}`

### Clan snapshots & schedules
- POST `/api/clans/{clan_id}/snapshots/run` (trigger batch) -> job_id
- GET `/api/clans/{clan_id}/snapshots/jobs/{job_id}` (status + member results)
- GET `/api/clans/{clan_id}/stats` (cached aggregates, timeframe param)
- GET `/api/clans/{clan_id}/leaderboards` (metric + timeframe)
- PUT `/api/clans/{clan_id}/schedule` (cron/max_daily_runs enable/disable)

### Contests
- POST `/api/clans/{clan_id}/contests` (create draft)
- GET `/api/clans/{clan_id}/contests` (list)
- GET `/api/clans/{clan_id}/contests/{contest_id}` (detail + rules + entries summary)
- POST `/api/clans/{clan_id}/contests/{contest_id}/rules` (add rule)
- POST `/api/clans/{clan_id}/contests/{contest_id}/activate` (locks rules)
- POST `/api/clans/{clan_id}/contests/{contest_id}/end` (locks entries, computes)
- POST `/api/clans/{clan_id}/contests/{contest_id}/draw` (runs RNG with commit–reveal; returns proof + winner)

### Webhooks
- POST `/api/clans/{clan_id}/webhooks` (add)
- GET `/api/clans/{clan_id}/webhooks`
- DELETE `/api/clans/{clan_id}/webhooks/{id}`

## Rule evaluation (contest entries)
- Inputs: two snapshots (previous vs end-of-contest) or aggregated deltas during contest window.
- Entry awarded when:
  - Skill XP gained >= threshold for any of the selected skills.
  - Skill levels gained >= threshold.
  - Total XP gained >= threshold.
  - Boss killcount delta >= threshold for selected bosses.
  - Clue count delta >= threshold for selected tiers.
- Each satisfied rule yields an entry (weight adjustable via `entry_count`/`weight`).
- Store `proof` with snapshot ids + computed deltas.

## Fairness (commit–reveal)
- Commitment: `hash = SHA256(server_secret + contest_id + end_at)`, stored on contest creation/activation.
- On draw: reveal `server_secret` + `nonce`, compute `seed = SHA256(server_secret + contest_id + nonce)`, pick winner via deterministic RNG over ordered entry list.
- Persist `seed_reveal`, `nonce`, `rng_proof` (selected index, entry list length, hash function).
- Surface hash + reveal in UI and Discord message; provide “verify” instructions.

## UI Contracts (for later phases)
- **Clans page**: overview, run-now button, cadence settings, next run time, last run status; stats panels; leaderboards; contests list; webhook config.
- **Contest detail**: rules list, entries summary, commitment hash, end time, draw button (leader only), spinner UX; after draw: winner + proof.
- **Jobs panel**: show batch run status per member snapshot with errors.

## Permissions
- Clan leader/officer: manage members, schedules, webhooks, contests, run snapshots.
- Member: view stats/leaderboards/contests; no write actions.

## Open questions (to finalize in implementation)
- Do we allow multiple webhooks per clan? (assumed yes)
- How to handle partial failures in batch snapshots? (proceed with available data; flag missing members)
- Do we cap contest length/timeframe presets? (likely 7/30 days or explicit dates)
