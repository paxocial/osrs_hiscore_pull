# Session Protocol

**Every work session MUST follow this pattern:**

```
1. CLOCK IN
   open_session(persona_id="<agent>", summary="<task>")
   ask_self("What do I know about this?")

2. WORK
   store_memory() - Save important findings
   append_entry() - Log detailed work trail (Scribe)
   log_audit() - Log milestones (Council)

3. CLOCK OUT
   end_session(summary="<what was accomplished>")
   -> Triggers automatic reflection
```

**Why Sessions Matter:**
- No session = no memory persistence
- No session = no audit trail
- Sessions enable cross-agent collaboration via `ask_agent`/`ask_council`

**Quick Reference:**
```python
# Start
open_session(persona_id="atlas", summary="Implementing auth flow")
ask_self("What do I know about auth patterns in this codebase?")

# During work
store_memory(text="Found JWT validation issue", tags="security,bug")
append_entry(message="Fixed JWT expiry check", status="success")

# End
end_session(session_id="...", summary="Auth flow complete, 3 tests added")
```