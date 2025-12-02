# 🧠 OSRS Web Lab Architecture Guide
**Project:** codex-osrs-snapshot  
**System Focus:** Web UI (auth, scheduling, analytics)  
**Author:** Codex  
**Version:** Draft v0.1  
**Last Updated:** 2025-12-02 01:55 UTC

---

## 1. Overview
A dark-blue, RuneScape-inspired web experience for osrs.cortalabs.com that wraps the existing snapshot pipeline (SnapshotAgent, ReportAgent, FastAPI) with authenticated user accounts, multi-RSN tracking, clan management, scheduled/manual snapshots, and visual analytics (charts + optional Three.js scenes). Delivery favors FastAPI + server-rendered HTML fragments with HTMX for interactivity, minimal JS helpers, and progressive enhancement for Three.js visualizations.

---

## 2. Goals & Non-Goals

| Goals | Non-Goals |
|-------|-----------|
| Authenticated accounts (email/pass + session cookies) and registration | Replacing SnapshotAgent ingestion logic |
| Link multiple RSNs per user; set a default profile | Building a SPA with React/Vue |
| Clan leader surfaces: roster, progress tables, goals/contests | Mobile apps or desktop launchers |
| Manual + scheduled snapshots (per account and per clan) | Custom hiscore scraping beyond current client |
| Snapshot history browser with deltas, XP/level charts | Heavy visual FX that slow low-end devices |
| Analytics layer ready for 2D charts + opt-in Three.js scenes | Real-time WebSockets in v1 (poll/HTMX is fine) |

---

## 3. Component Map

```mermaid
flowchart LR
  subgraph Client
    UI[HTMX pages + CSS system]
    Charts[Charts.js/Plotly segments]
    Three[Three.js scene (optional)]
  end
  subgraph API[FastAPI]
    Auth[Auth routes]
    Accounts[Account + RSN routes]
    Clans[Clan + contests routes]
    Snapshots[Snapshot browse/run]
    Jobs[Scheduler hooks]
  end
  subgraph Services
    Scheduler[Cron/APS + task runner]
    SnapshotAgent
    ReportAgent
    Analytics[analytics.engine]
    Scribe[scripts/scribe.py]
  end
  subgraph Storage
    DB[(SQLite analytics.db)]
    Files[data/snapshots + reports]
  end

  UI -->|HTMX| API
  Charts --> UI
  Three --> UI
  API --> Services
  Services --> DB
  Services --> Files
  Services --> Scribe
```

---

## 4. Integration Points

| Integration | File Path | Description |
|-------------|-----------|-------------|
| REST API | `api/main.py`, `api/endpoints/*` | Backing endpoints for accounts, snapshots, analytics, clans, contests, auth. |
| SnapshotAgent | `agents/osrs_snapshot_agent.py` | Runs manual and scheduled pulls; persists JSON and metadata. |
| ReportAgent | `agents/report_agent.py` | Generates Markdown reports referenced in UI downloads. |
| Scheduler | New (APS/cron wrapper) + `main.py` entry | Triggers periodic pulls; stores job configs in DB. |
| Scribe | `scripts/scribe.py` + `support/scribe_reporter.py` | Structured logging for UI actions (auth, jobs, renders). |
| Data | `data/snapshots`, `reports/`, `data/analytics.db` | Snapshot payloads, Markdown, relational views. |
| Visualizations | New `web/static/js/three-scenes.js` | Optional Three.js scene loader for hero/3D charts. |
| Webhooks | New `web/services/webhooks.py` | Discord/Slack notifications for snapshots, contests, milestones. |
| API Tokens | New `web/services/api_tokens.py` | Per-user tokens (scoped, revocable) for bots/overlays. |
| Public Profiles | New `web/routes/public.py` | Shareable `/p/<rsn>` timeline/delta pages. |

---

## 5. Schema Overview (proposed extensions)

- `users` (id, email, password_hash, created_at, last_login)
- `user_accounts` (user_id, account_id, role [owner/editor/viewer], default_flag)
- `clans` (id, name, slug, owner_user_id, metadata)
- `clan_members` (clan_id, account_id, join_date, rank, notes)
- `contests` (id, clan_id, name, start_at, end_at, metric, reward, created_by)
- `contest_progress` (contest_id, account_id, start_snapshot_id, latest_snapshot_id, delta)
- `snapshot_jobs` (id, user_id, target_type [account/clan], target_id, cadence_cron, last_run, next_run, status, metadata)
- `api_tokens` (id, user_id, token_hash, scopes, last_used_at, revoked_at, label)
- `webhooks` (id, owner_user_id, target_type [clan/user], url, provider, secret, events, active)
- `public_profiles` (id, account_id, slug, is_public, created_at, last_viewed_at)
- Reuse existing `accounts`, `snapshots`, `skills`, `activities` from analytics DB.

---

## 6. Primary User Journeys (HTMX-first)

- **Registration & Login**: Form posts → set signed session cookie → redirect to Dashboard.
- **Connect RSNs**: Add RSN with mode; list in “My Profiles”; mark default; attach to clans.
- **Manual Snapshot**: From profile card, hit “Fetch Now” → POST /snapshots/run → optimistic status pill + delta summary.
- **Scheduled Snapshot**: Configure cron string or presets per RSN/clan → write `snapshot_jobs` → scheduler triggers SnapshotAgent and logs to Scribe.
- **History Browser**: Timeline with filters; HTMX swaps table + sparkline; download JSON/MD links.
- **Clan Leader View**: Roster table (sortable), goals/contests, “bulk snapshot” trigger, leaderboard slices.
- **Visual Labs**: Toggle “3D view” that pipes data to Three.js (e.g., constellation of skills, time-based particle trail).
- **Clan Webhooks**: Clan owner registers Discord/Slack URL; on snapshot/contest updates, webhook fires with top gains + links.
- **Public RSN Page**: Opt-in shareable `/p/<rsn>` with timeline, deltas, clan badge; toggle visibility and revoke link.
- **API Access**: User generates token scoped to read-only analytics; used by clan bots/overlays with rate limiting.

---

## 7. Message Flow / Execution

- Manual pull: UI → POST `/snapshots/run` → SnapshotAgent → DB/files → Scribe entry → HTMX poll `/snapshots/status/{id}` for completion → render delta and links.
- Scheduled pull: Scheduler tick → SnapshotAgent batch → DB/files → Scribe → optional email/Toast in UI next visit.
- Contest progress: Nightly job (or on-demand) computes deltas between contest start snapshot and latest → caches in `contest_progress`.
- Analytics tiles: Fast API queries via `analytics/engine.py` for XP rates, milestones, boss kc graphs → returned as JSON for HTMX fragments or chart JS payloads.
- Webhooks: Snapshot/contest event → enqueue notification → `web/services/webhooks.py` sends to Discord/Slack with signed payload.
- Public profile: Request `/p/<rsn>` → cached render of timeline/deltas → respects visibility flag and rate limits → optional token for bot-friendly JSON.
- API tokens: Request with `Authorization: Bearer <token>` → token scope validated → rate limiter checks → serve JSON (accounts/snapshots/analytics).

---

## 8. Testing & Verification

- API contract tests for new auth/clan/job endpoints.
- HTMX view tests via Playwright/Locust-lite smoke (login, manual snapshot, history pagination).
- Scheduler dry-run mode to avoid accidental spam.
- Visual regression: static screenshot checks for dark-blue theme tokens.
- Data integrity: nightly job to compare DB rows vs file-based snapshots for drift.

---

## 9. Long-Term Roadmap

- Multi-tenant hosting mode for `osrs.cortalabs.com` (orgs + billing).
- WebSocket live updates for in-progress snapshots and contest dashboards.
- Feature-flagged advanced 3D scenes (seasonal events, boss arenas).
- Plugin API for community visualizations fed from the analytics engine.

---

## 10. Revision Log

| Date | Change | Author | Confidence |
|------|--------|--------|------------|
| 2025-12-02 | Initial draft | Codex | 0.74 |
