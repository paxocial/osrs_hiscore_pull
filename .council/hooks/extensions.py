"""Optional downstream runtime hook extensions.

Generated runtime hook scripts look for event-specific helpers here before they
fall back to generic behavior. Override only the functions you need.

Supported entrypoints:
- on_user_prompt_submit(payload)
- on_pre_compact(payload)
- on_hook_event(event_name, payload)

Return contract:
- None: no customization
- str: one context line
- list[str]: additional context lines
- dict:
    {
        "context_lines": [...],   # optional
        "state_updates": {...},   # optional
        "handoff_updates": {...}, # optional for pre_compact
    }
"""
