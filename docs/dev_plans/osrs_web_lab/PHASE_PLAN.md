# ⚙️ Phase Plan — OSRS Web Lab
**Project:** codex-osrs-snapshot (Web UI)  
**Version:** Draft v0.1  
**Author:** Codex  
**Last Updated:** 2025-12-02 01:55 UTC

---

## Phase 0 – Foundations / Scaffolding
**Objective:** Stand up web app shell with dark-blue theme tokens, layout grid, and HTMX-ready templates.

**Key Tasks:**
- [ ] Create `web/` package (FastAPI router for pages, Jinja templates, static pipeline).
- [ ] Define CSS variables + theme tokens; import typography + base components.
- [ ] Add session middleware + CSRF utilities foundation.

**Deliverables:**
- Base layout template with header/nav/footer stubs.
- `static/css/theme.css`, `static/js/htmx-hooks.js`.

**Acceptance Criteria:**
- [ ] Home loads with shared layout + dark theme tokens.
- [ ] HTMX requests return partials with correct headers.

**Dependencies:** API stack running locally.  
**Confidence:** 0.78

---

## Phase 1 – Auth & Account Linking
**Objective:** Enable registration/login and multiple RSNs per user with roles.

**Key Tasks:**
- [ ] Build forms + endpoints for sign-up, login, logout, password reset (token email hook placeholder).
- [ ] Add `users` + `user_accounts` tables; migration script.
- [ ] RSN management UI: add/remove RSNs, set default, attach mode.
- [ ] API token issuance (scoped, revocable, rate-limited) for bots/overlays.

**Deliverables:**
- Authenticated session cookie flow.
- “My Profiles” page with RSN list.
- API token page with create/revoke and scope display.

**Acceptance Criteria:**
- [ ] User can register, login, and see own RSNs only.
- [ ] Default RSN resolved for dashboard tiles.
- [ ] Token auth works against a protected JSON endpoint.

**Dependencies:** Phase 0.  
**Confidence:** 0.74

---

## Phase 2 – Snapshot Controls (Manual + Scheduled)
**Objective:** Let users trigger manual snapshots and configure schedules per RSN/clan.

**Key Tasks:**
- [ ] POST `/snapshots/run` HTMX action with progress polling.
- [ ] Scheduler service + `snapshot_jobs` table; UI for cron presets + pause/resume.
- [ ] Wire SnapshotAgent + Scribe logging for UI actions.
- [ ] Add webhook event emission hooks for snapshot completion (stubs for Discord/Slack).

**Deliverables:**
- “Run now” button per RSN and per clan roster.
- Scheduler admin view with next-run times.
- Webhook settings stub UI (no-op send OK for now).

**Acceptance Criteria:**
- [ ] Manual pull updates history table within the session.
- [ ] Scheduled jobs fire in dry-run/local mode and record Scribe entries.
- [ ] Webhook payload logged (dry-run) on snapshot completion.

**Dependencies:** Phase 1.  
**Confidence:** 0.72

---

## Phase 3 – History & Analytics
**Objective:** Expose snapshot history, deltas, charts, and downloads.

**Key Tasks:**
- [ ] Paginated history view with filters (mode, time window, skills/activities toggles).
- [ ] Charts: XP/level over time, boss KC deltas (Charts.js/Plotly).
- [ ] Report/JSON download links; highlight “notable gains” badges.
- [ ] Public RSN pages `/p/<rsn>` with share toggles and simple caching.

**Deliverables:**
- RSN dashboard with timeline, top deltas, and sparkline chips.
- Shareable public profile page (opt-in) with timeline/deltas/clan badge.

**Acceptance Criteria:**
- [ ] Charts render from API data without page reload.
- [ ] Snapshot rows match DB/file contents for a sample set.
- [ ] Public page respects privacy toggle and rate limits.

**Dependencies:** Phase 2.  
**Confidence:** 0.70

---

## Phase 4 – Clans, Goals, and Contests
**Objective:** Leader tooling for roster, progress, and competitions.

**Key Tasks:**
- [ ] `clans`, `clan_members`, `contests`, `contest_progress` tables + UI.
- [ ] Roster table with sortable metrics and per-member snapshot controls.
- [ ] Contest creator (metric, start/end, reward) + progress dashboards.
- [ ] Clan webhooks (Discord/Slack) for snapshot completion, contest updates, milestones.
- [ ] Clan insight board: XP heatmap, weekly deltas, HCIM death tracker, boss/KC/GOTR leaderboards, top gainers widget.
- [ ] Configurable contest metrics (XP, skills, bosses, clues, GOTR, EHB/EHP, milestones).

**Deliverables:**
- Clan home with roster, goals board, contest cards.
- Webhook configuration per clan + notification templates.
- Insight board tiles for competition dashboards.

**Acceptance Criteria:**
- [ ] Contest shows deltas between start snapshot and latest for each member.
- [ ] Clan leader can bulk trigger snapshots and view job results.
- [ ] Webhook fires (or dry-run) with top gainers + links; metrics selectable per contest.

**Dependencies:** Phase 3.  
**Confidence:** 0.68

---

## Phase 5 – Visual Labs & Production Hardening
**Objective:** Add optional Three.js scenes, polish UX, and prep for osrs.cortalabs.com.

**Key Tasks:**
- [ ] Hero/scene toggle with graceful fallback for low-power devices.
- [ ] Loading states, empty states, error toasts; accessibility pass.
- [ ] Observability hooks (Scribe + metrics), CDN/static caching, rate-limit tuning.

**Deliverables:**
- Themed hero/scene, finalized navigation, deployment checklist.

**Acceptance Criteria:**
- [ ] Page load <2.5s P75 on baseline hardware.
- [ ] Three.js disabled automatically when WebGL unsupported; charts still render.

**Dependencies:** Phase 4.  
**Confidence:** 0.69
