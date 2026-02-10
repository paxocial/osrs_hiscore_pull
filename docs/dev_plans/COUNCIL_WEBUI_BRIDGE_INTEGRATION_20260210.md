# Council Web UI Bridge Integration Plan

Date: 2026-02-10
Owner: Codex
Scope: Prepare `.council/council.yaml` and `.council/roster.yaml` for Council + custom-page workflow before running `council update`.

## Goals

1. Align this repo's council config with the current Council Web UI conventions used in `council_mcp` and `rom_lab`.
2. Evolve the roster from minimal Atlas-only into OSRS domain agents that match the local `AGENTS.md` and `CLAUDE.md`.
3. Pre-wire page-agent routing for custom pages so chat context can be page-scoped once pages are added.

## Findings Summary

1. `.council/council.yaml` currently has `sdk.enabled: false` and `chat.page_agents: {}`.
2. Custom pages/static support is already enabled (`custom_pages_enabled`, `custom_static_enabled`).
3. Current roster is minimal and does not encode OSRS Snapshot/Report responsibilities described in `AGENTS.md` and `CLAUDE.md`.
4. Reference councils (`rom_lab`, `council_mcp`) use:
   - SDK enabled for web-managed sessions.
   - richer roster prompts and role separation.
   - optional generation metadata for rule/key-directory shaping.

## Planned Edits

### A) `.council/council.yaml`

1. Enable SDK (`council.sdk.enabled: true`) for Council Web UI control plane.
2. Set a friendly nav label for project custom pages (`council.web.nav_group_label`).
3. Add page-agent mappings under `council.chat.page_agents` for intended OSRS pages:
   - `/pages/osrs-dashboard`
   - `/pages/osrs-jobs`
   - `/pages/osrs-snapshots`
4. Add `council.generation` section with:
   - project key directories (`agents/`, `core/`, `web/`, `tests/`, `docs/`).
   - explicit rule list including custom-pages + dual-logging + process-lifecycle.

### B) `.council/roster.yaml`

Replace minimal roster with OSRS-oriented multi-agent council:

1. `atlas` (coordinator): orchestration and bounded tasking.
2. `snapshot` (specialist): hiscore fetch/storage pipeline.
3. `report` (specialist): markdown/report rendering and summaries.
4. `bridge` (specialist): council web custom-page + API bridge integration.
5. `review` (auditor): regression/risk review and validation.

Each agent will define domains plus focused identity/expertise/behavioral guidance aligned with `AGENTS.md` and `CLAUDE.md`.

## Validation

1. YAML parse check for both files.
2. Sanity check key fields (`sdk.enabled`, `chat.page_agents`, coordinator presence, domains lists).
3. Diff review to ensure non-zero effective changes.

## Notes

1. This plan configures routing and agent defaults only; it does not create custom page templates yet.
2. After these edits, run:
   - `council update --dry-run`
   - `council update`

## Follow-Up: Template Sync (2026-02-10)

1. Update `.council/templates/claude/CLAUDE.md.j2` and `.council/templates/AGENTS.md.j2` to remove legacy hardcoded workflows/agent assumptions and make routing guidance roster-driven.
2. Regenerate with `council update --from-yaml` so `CLAUDE.md` reflects the OSRS roster.
3. Import roster into DB using `council roster import .council/roster.yaml` to align runtime/web UI state with YAML.

## Follow-Up: Slug Normalization (2026-02-10)

1. Normalize coordinator slug from underscore form to kebab-case (`osrs_atlas` → `osrs-atlas`) to match lowercase-hyphen slug convention.
2. Update `council.chat.default_agent` in `.council/council.yaml` to the same slug.
3. Regenerate artifacts with `council update --from-yaml`, then run `council roster import .council/roster.yaml`.
4. Validate with `council roster list` and confirm the coordinator appears as `osrs-atlas`.
