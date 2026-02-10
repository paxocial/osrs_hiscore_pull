# Process Lifecycle

**Council runs as a process tree. Understanding ownership prevents cross-process bugs.**

## Process Tree

```
council start
  └─ Daemon (server.py)                    port 8016, PID in .council/daemon.pid
       ├─ Scribe MCP (stdio subprocess)    registered in process_registry.db
       └─ Web UI (separate OS process)     port 8015, registered in process_registry.db
            ├─ SDK ProcessManager           lightweight, for worker spawn/stop only
            └─ SDK SessionManager           manages Claude/mock SDK sessions
```

## Ownership Rules

| Component | Owner | Shared Via |
|-----------|-------|------------|
| ProcessManager (primary) | Daemon | SQLite `process_registry.db` |
| SystemHealthMonitor | Daemon | Daemon MCP tools (`get_system_health`) |
| Scribe MCP processes | Daemon | Daemon proxy (`scribe_call`/`scribe_status`) |
| `_RUNTIME_CONTEXT` | Daemon | **NOT shared** — process-local dict |
| MCP client pool (WS) | Web | Direct WebSocket to daemon/scribe |
| SDK SessionManager | Web | Direct init (fallback path) |
| SDK ProcessManager | Web | Lightweight instance, shares SQLite |
| LogManager | Web | Reads log files directly |

### Critical: `_RUNTIME_CONTEXT` is process-local

`_RUNTIME_CONTEXT` in `server.py` is a Python dict populated by the daemon process. The web UI runs as a **separate OS process** — when it imports `server.py`, it gets an empty dict. **Never rely on `_RUNTIME_CONTEXT` for cross-process state sharing.** Use SQLite (process registry) or MCP tool calls instead.

## Startup Sequence

### Daemon (`council start`)
1. `_start_background()` — spawn daemon process, write PID file
2. Daemon initializes: ProcessManager → SystemHealthMonitor → Scribe clients
3. `_spawn_web_ui()` — wait for daemon health, spawn web as separate process
4. Register web PID in SQLite process registry

### Web UI (lifespan in `app.py`)
1. Connect MCP client pool to daemon (WS on port 8016)
2. Connect to Scribe — prefer daemon proxy, fallback to direct spawn
3. Sync persona profiles from `.claude/agents/` to database
4. Set sentinels: `app.state.process_manager = None`, `app.state.system_health = None`
5. Initialize LogManager
6. Initialize SDK: ProviderRegistry → WorkerPool(pm) → StreamBridge → SessionManager

### SDK Initialization (web-owned)
```python
# app.state.process_manager is None (daemon-owned sentinel)
# SDK needs its own PM for worker lifecycle
pm = ProcessManager()        # lightweight instance
await pm.start()             # init SQLite, adopt orphans, health loop
pool = WorkerPool(process_manager=pm)
bridge = StreamBridge(ws_manager=ws_manager)
session_mgr = SessionManager(worker_pool=pool, stream_bridge=bridge, ...)
await session_mgr.startup()  # readopt workers, restore approvals
```

## Shutdown Sequences

### Full Stop (`council stop`)
```
_stop_registry_children() order:
  1. sdk_session     (least critical)
  2. plugin
  3. web_ui
  4. mcp_server
  5. scribe_mcp      (most critical — stop last)
Then: SIGTERM daemon → wait grace period → SIGKILL if --force
```

### Web Full Shutdown (no sentinel)
```
1. SDK SessionManager.shutdown()     — end sessions, stop workers
2. SDK ProcessManager.shutdown()     — stop health loop, close SQLite
3. MCP client pool.stop_all()        — close WS connections
```

### Web Soft Reload (sentinel exists)
```
1. MCP client pool.disconnect_all()  — close WS only, no subprocess kill
   (daemon and Scribe stay alive)
```

### Reboot (`council reboot`)
```
Stage 1: Notify WS clients (close code 4010)
Stage 2: Stop children → stop daemon
Stage 3: Start daemon fresh → spawn web UI
Stage 4: Verify health
```

## Reload Commands

| Command | Scope | Mechanism |
|---------|-------|-----------|
| `council reload` | Daemon only | POST `/api/daemon/restart` |
| `council reload --web` | Web only | Sentinel file + SIGTERM |
| `council reload --all` | Both | Web reload, then daemon reload |

### Web Reload Sentinel Pattern
`council reload --web` writes `.council/.web_reloading` before SIGTERM. The web lifespan checks for this file on shutdown:
- **Sentinel exists** → soft disconnect (WS only), uvicorn restarts worker
- **No sentinel** → full teardown (SDK, PM, all MCP clients)

## WebSocket Close Codes

| Code | Constant | Meaning | Client Behavior |
|------|----------|---------|-----------------|
| 4010 | `WS_CLOSE_RESTART` | Daemon restarting | Reconnect with backoff |
| 4011 | `WS_CLOSE_SHUTDOWN` | Full shutdown | Stop reconnecting |
| 4012 | `WS_CLOSE_WEB_RELOAD` | Web UI reloading | Fast reconnect (0.5s) |

## Key Files

| File | Purpose |
|------|---------|
| `cli/start_cmd.py` | `council start`, `council stop`, `_stop_registry_children` |
| `cli/reload_cmd.py` | `council reload`, `_reload_web`, `_reload_daemon` |
| `cli/reboot_cmd.py` | `council reboot` (full-stack restart) |
| `server.py` | Daemon main, `_RUNTIME_CONTEXT`, scribe/SDK init |
| `web/app.py` | Web lifespan (startup/shutdown), SDK fallback init |
| `process_manager.py` | ProcessManager, ProcessType enum, SQLite registry |
| `web/mcp_client.py` | MCP client pool, ScribeProxyClient, `start_scribe()` |

## Common Pitfalls

**Wrong** — Reading `_RUNTIME_CONTEXT` from web:
```python
# ALWAYS empty in web process
from council_mcp.server import _RUNTIME_CONTEXT
sdk_mgr = _RUNTIME_CONTEXT.get("sdk_session_manager")  # None!
```

**Right** — Direct initialization with fallback:
```python
sdk_mgr = _server_ctx.get("sdk_session_manager")
if sdk_mgr is None:
    # Initialize directly — web is a separate process
    session_mgr = SessionManager(...)
```

**Wrong** — Assuming web has ProcessManager:
```python
pm = app.state.process_manager  # None (sentinel)
pm.get_status()  # AttributeError!
```

**Right** — Create lightweight PM for SDK:
```python
pm = getattr(app.state, "process_manager", None)
if pm is None:
    pm = ProcessManager()
    await pm.start()
```

**Wrong** — Stopping Scribe from web shutdown:
```python
# Web doesn't own Scribe — daemon does
await scribe_client.stop()  # Kills daemon's subprocess!
```

**Right** — Disconnect only:
```python
await mcp_pool.disconnect_all()  # Close WS, leave subprocess alive
```