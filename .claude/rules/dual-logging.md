# Dual Logging Protocol

## Council Logs (Milestones and Presence)

Use for: Session lifecycle, significant decisions, cross-agent events

```python
# Announce presence
log_audit(summary="Starting: auth system refactor", metadata={"phase": "init"})

# Log milestone
log_audit(summary="Phase 1 complete: all tests passing", metadata={"phase": "complete"})

# Store learning
store_memory(text="This codebase uses factory pattern for services", tags="pattern,architecture")
```

## Scribe Logs (Detailed Work Trail)

Use for: Every action, investigation step, code change, test result

```python
# Investigation
append_entry(message="Reading auth.py to understand current flow", status="info")

# Finding
append_entry(message="Found bug: JWT expiry not checked", status="bug", meta={"file": "auth.py:142"})

# Change
append_entry(message="Fixed JWT validation with 15min grace", status="success", meta={"files": 2})
```

## When to Use Which

| Event | Council | Scribe |
|-------|---------|--------|
| Starting work | log_audit | append_entry |
| Reading a file | - | append_entry |
| Found a bug | store_memory | append_entry |
| Made a decision | store_memory | append_entry |
| Phase complete | log_audit | append_entry |
| Session end | end_session | - |

**Rule**: When in doubt, log to Scribe. Council is for milestones, Scribe is for everything.