# Council Hooks

This directory is the Council-owned source of truth for hook intent and
provider mappings.

Rules:
- Edit files here, not generated `.claude/*` or `.codex/*` outputs.
- Keep shared intent canonical and provider differences explicit.
- Do not pretend Claude Code and Codex expose identical hook surfaces.

Current model:
- `registry.yaml` defines canonical Council event ids.
- Provider adapters decide what is fully supported, partially supported, or
  unsupported for each vendor runtime.
- `council update` materializes provider-specific runtime artifacts from this
  source.
- `extensions.py` is the downstream customization seam for runtime hook
  behavior. Generated hook scripts may call event-specific helpers there
  instead of requiring full file overrides.

`extensions.py` hook API:
- `on_user_prompt_submit(payload)` may return `None`, a string, a list of
  context lines, or a dict containing `context_lines` and/or `state_updates`.
- `on_pre_compact(payload)` may return `None`, a string, a list of context
  lines, or a dict containing `context_lines`, `handoff_updates`, and/or
  `state_updates`.
- `on_hook_event(event_name, payload)` is an optional generic fallback.
