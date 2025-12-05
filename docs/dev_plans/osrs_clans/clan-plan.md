# Clans Vision & Plan

## Purpose
Define the clans experience: clan-wide snapshots and aggregates, leaderboards, contests with provable fairness, and Discord notifications.

## Core UX Blocks
- **Clan Overview**: name, member count, snapshot cadence, last clan snapshot status, CTA “Run clan snapshot now”.
- **Snapshot Cadence**: daily default, configurable up to 2/day; next run time and last run result/errors.
- **Clan Stats Panels**: aggregate totals/deltas (XP, levels, bosses, clues) with links to member profiles; timeframe filters (7d/30d/MTD).
- **Leaderboards**: XP gained, levels gained, per-skill XP, bosses killed, clues completed; sortable; timeframe-scoped.
- **Contests**: list/detail (active/upcoming/past); rules, entries, prize, end date, fairness seed, “Run draw” with spinner; lifecycle events in Discord.
- **Notifications**: clan-level Discord webhooks; per-event toggles; last delivery status.
- **Audit/History**: log of snapshot runs and contest draws with timestamps and links.

## Data & Entities (high level)
- **Clan**, **ClanMember** (role/leader flag).
- **ClanSnapshot** (batch run + aggregate roll-up).
- **ClanStats** (cached aggregates by timeframe).
- **Contest** (metadata, status, prize, timeframe, seed commitment).
- **ContestRule** (type/target/value/timeframe).
- **ContestEntry** (member, rule hit, proof snapshot IDs).
- **ContestDraw** (winner, seed reveal, nonce, hash, RNG proof).

## Scheduling & Snapshots
- Daily default; cap at 2/day; store per-clan schedule; show next run.
- “Run now” batches member snapshots (≤5 concurrent; backoff) then aggregates into clan stats.
- Track job status/errors and surface in UI; require recent snapshot for contest draw (e.g., within 24h).

## Contests
- **Rule types** (snapshot-derived):
  - Skill XP gained ≥ N (per skill or set).
  - Levels gained ≥ N (per skill or total).
  - Boss KC increase ≥ N (selected bosses).
  - Clue count increase ≥ N (selected tiers).
  - Total XP gained ≥ N.
- **Entries**: each satisfied rule grants one entry; multiple rules can stack for a member; store with proof to snapshots.
- **Lifecycle**: draft → active → ended → drawn. End locks entries; draw is a separate action (leader clicks).
- **Fairness**: commit–reveal seed (hash(server_secret + contest_id + end_time)); reveal publishes secret; RNG via HMAC/SHA256(seed||nonce); store commitment, reveal, nonce, winner index; expose in UI and Discord.
- **UI**: contest detail shows rules, participants/entries, prize, end date, hash commitment, and “Run draw” spinner; after draw, show winner and verification info.

## Leaderboards & Metrics
- Timeframe-scoped (7d/30d/month); deltas from snapshots.
- Views: total XP gained, per-skill XP gained, levels gained, boss KC gained, clues done.
- Each row links to member profile.

## Discord Integration
- Clan-level webhooks; events: clan snapshot complete, contest created, contest ending soon, contest drawn (winner + proof hash), leaderboard highlights.
- Store last delivery status/response; per-event enable/disable.

## Fairness & Transparency
- Show commitment hash + reveal seed + nonce + RNG formula; “verify” link.
- Audit tables/logs for snapshot runs, contest calculations, and draws.

## Performance & Limits
- Respect rate limit (≤5 concurrent snapshots); backoff on errors.
- Enforce schedule cap (2/day) and contest draw prerequisites (recent data).

## Rollout Phases
1) **Design & schema**: finalize tables for clans, snapshots, aggregates, contests, rules, entries, draws; mock UI.
2) **Clan snapshots/aggregates**: implement scheduled/batch runs, aggregation, and clan stats panels; “Run now” + cadence UI.
3) **Leaderboards**: timeframe filters and per-metric boards using aggregates.
4) **Contests (MVP)**: create contests/rules, compute/store entries, display counts.
5) **Fair draw**: commit–reveal RNG, spinner UI, winner display, audit trail.
6) **Discord hooks**: emit contest lifecycle and snapshot events with verification data.
7) **Hardening**: permissions (leader-only), rate limits, errors, tests.
