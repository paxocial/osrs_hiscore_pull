# Council Isolation

**Every web API endpoint that touches council-scoped data MUST filter by the active council_id.**

## The Pattern

```python
from starlette.requests import Request

@app.get("/api/resource")
async def list_resources(
    request: Request,  # REQUIRED
    current_user: dict = Depends(get_current_user),
) -> JSONResponse:
    council_id = _get_active_council_id(request)  # REQUIRED

    # Filter queries by council_id
    if council_id:
        query += " AND council_id = %(council_id)s"
    # When council_id is None: skip filtering for backward compat
```

## Helper Function

`_get_active_council_id(request)` in `app.py`:
- Reads `active_council_id` cookie (set by council dropdown switch)
- Falls back to first council via `list_councils_sync()`
- Returns `None` if no councils exist

## Scoping Strategies

### Direct Column Filter
For tables with a `council_id` column (persona_profiles, skills, mcp_servers):
```python
if council_id:
    query += " WHERE council_id = %(council_id)s"
```

### JOIN Through persona_profiles
For tables linked via persona (memories, sessions, audit):
```python
if council_id:
    query = """
        SELECT r.* FROM resource_table r
        JOIN persona_profiles pp ON r.persona_id = pp.id
        WHERE pp.council_id = %(council_id)s
    """
```

### Persona Validation
For single-resource endpoints that accept a persona_id:
```python
if council_id:
    cur.execute(
        "SELECT 1 FROM persona_profiles WHERE slug = %(pid)s AND council_id = %(cid)s",
        {"pid": persona_id, "cid": council_id}
    )
    if not cur.fetchone():
        raise HTTPException(status_code=403, detail="Persona not in active council")
```

## Frontend Requirements

Every page's JS MUST listen for council switches:
```javascript
window.addEventListener('councilSwitched', async (event) => {
    console.log('Council switched:', event.detail);
    // Clear current state
    // Reload data from API
});
```

The council selector (`static/js/council.js`) dispatches this event on `window` after `POST /api/councils/switch` sets the cookie and reloads.

## What Gets Scoped

| Resource | Scoping Method | Table Path |
|----------|---------------|------------|
| Agents | Direct column | `persona_profiles.council_id` |
| Memories | JOIN | `persona_memories → persona_profiles.council_id` |
| Sessions | JOIN | `persona_sessions → persona_profiles.council_id` |
| Skills | Direct column | `skills.council_id` |
| MCP Servers | Direct column | `mcp_servers.council_id` |
| Audit Entries | JOIN | `persona_audit_entries → persona_profiles.council_id` |
| Chat/DMs | Persona validation | Verify sender/target persona in council |
| Templates | Cookie-based | `active_council_id` passed to TemplateService |

## What Does NOT Get Scoped

- `/api/councils/*` — council management endpoints (global by nature)
- `/api/archetypes/*` — global reference data
- `/api/hooks/*` — internal webhook endpoints
- `/api/v1/federation/*` — federation endpoints
- `/api/settings/*` — user settings (not council-specific)
- `/api/scribe/*` — Scribe projects are repo-scoped, not council-scoped

## Checklist for New Endpoints

When adding ANY new `/api/*` endpoint:

1. Does it touch council-scoped data? → Add `request: Request` param
2. Call `_get_active_council_id(request)`
3. Apply appropriate scoping (direct filter, JOIN, or persona validation)
4. Handle `council_id = None` gracefully (backward compat)
5. Add `councilSwitched` listener to the page's JS if it has a frontend
6. Test by switching councils in the dropdown

## Anti-Patterns

**Wrong** — Hardcoding first council:
```python
councils = list_councils_sync()
council_id = councils[0]["id"]  # BREAKS multi-council
```

**Wrong** — Optional query param the frontend never sends:
```python
council_id: str = Query(default=None)  # Frontend won't pass this
```

**Right** — Cookie-based via helper:
```python
council_id = _get_active_council_id(request)  # Reads cookie automatically
```