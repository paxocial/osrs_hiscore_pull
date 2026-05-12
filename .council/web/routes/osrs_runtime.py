"""Downstream OSRS runtime control via Council ProcessManager."""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from council_mcp.web.dependencies import get_current_user
from council_mcp.web.runtime_services import (
    build_plugin_process_config,
    collect_plugin_runtime_state,
    get_active_repo,
    get_process_manager,
)

router = APIRouter(tags=["osrs-runtime"])

DEFAULT_PORT = 8001
LOG_FILENAME = "osrs_backend.log"
START_SCRIPT = "scripts/start_osrs_backend.sh"
SERVICE_TAG = "osrs_backend"


class RuntimeStartRequest(BaseModel):
    port: int = Field(default=DEFAULT_PORT, ge=1, le=65535)
    wait_seconds: float = Field(default=25.0, ge=0.0, le=180.0)


class RuntimeStopRequest(BaseModel):
    confirm: bool = Field(default=False)
    grace_seconds: float = Field(default=4.0, ge=0.1, le=60.0)
    force_kill: bool = Field(default=True)


def _runtime_paths(repo: Path) -> tuple[Path, Path]:
    council_dir = repo / ".council"
    log_file = council_dir / LOG_FILENAME
    script = repo / START_SCRIPT
    return log_file, script


def _collect_runtime_state(repo: Path, port: int, entries: list[Any], log_file: Path) -> dict[str, Any]:
    return collect_plugin_runtime_state(
        repo=repo,
        port=int(port),
        entries=entries,
        service=SERVICE_TAG,
        log_file=log_file,
    )


@router.get("/api/osrs/runtime/status")
async def osrs_runtime_status(
    request: Request,
    port: int = DEFAULT_PORT,
    current_user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    del current_user
    repo = get_active_repo(request)
    log_file, _ = _runtime_paths(repo)
    pm = get_process_manager(request)
    entries = await pm.get_status()
    return _collect_runtime_state(repo, int(port), entries, log_file)


@router.post("/api/osrs/runtime/start")
async def osrs_runtime_start(
    request: Request,
    payload: RuntimeStartRequest,
    current_user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    del current_user
    repo = get_active_repo(request)
    log_file, script = _runtime_paths(repo)

    if not script.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Startup script not found: {script}. Expected {START_SCRIPT} in repo root.",
        )

    pm = get_process_manager(request)
    entries = await pm.get_status()
    state = _collect_runtime_state(repo, payload.port, entries, log_file)

    if state["single_instance_conflict"]:
        raise HTTPException(
            status_code=409,
            detail=(
                "Another OSRS backend instance is already online. "
                "Stop existing instances before starting a new one."
            ),
        )

    if state["running"]:
        return {
            "started": False,
            "already_running": True,
            "message": "OSRS backend already running.",
            **state,
        }

    log_file.parent.mkdir(parents=True, exist_ok=True)

    process_config = build_plugin_process_config(
        repo=repo,
        command=[str(script)],
        service=SERVICE_TAG,
        port=int(payload.port),
        env={
            "OSRS_BACKEND_PORT": str(payload.port),
            "COUNCIL_WEB_ORIGIN": str(request.base_url).rstrip("/"),
            "OSRS_BACKEND_LOG_PATH": str(log_file),
        },
        metadata={
            "script": START_SCRIPT,
        },
        auto_restart=False,
    )

    spawned = await pm.spawn(process_config.process_type, process_config)

    deadline = time.time() + payload.wait_seconds
    while time.time() < deadline:
        entries = await pm.get_status()
        state = _collect_runtime_state(repo, payload.port, entries, log_file)
        if state["running"] and state["managed_pid"] == int(spawned.pid) and not state["single_instance_conflict"]:
            break
        if not any(int(getattr(entry, "pid", -1)) == int(spawned.pid) for entry in entries):
            break
        await asyncio.sleep(0.25)

    entries = await pm.get_status()
    state = _collect_runtime_state(repo, payload.port, entries, log_file)

    if state["single_instance_conflict"]:
        try:
            await pm.stop(int(spawned.pid), grace_seconds=2.0)
        except Exception:
            pass
        raise HTTPException(
            status_code=409,
            detail="Single-instance policy violation detected during startup; start aborted.",
        )

    if not state["running"] or state["managed_pid"] is None:
        detail = "OSRS backend did not become reachable before timeout."
        try:
            tail = log_file.read_text(encoding="utf-8", errors="replace").splitlines()[-40:]
            if tail:
                detail = "\n".join(tail)
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=detail)

    return {
        "started": True,
        "already_running": False,
        "message": "OSRS backend start requested.",
        **state,
    }


@router.post("/api/osrs/runtime/stop")
async def osrs_runtime_stop(
    request: Request,
    payload: RuntimeStopRequest,
    port: int = DEFAULT_PORT,
    current_user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    del current_user

    if not payload.confirm:
        raise HTTPException(status_code=400, detail="Set confirm=true to stop OSRS backend")

    repo = get_active_repo(request)
    log_file, _ = _runtime_paths(repo)
    pm = get_process_manager(request)

    entries = await pm.get_status()
    state = _collect_runtime_state(repo, int(port), entries, log_file)

    target_pid = state.get("managed_pid")
    if not target_pid and len(state.get("repo_online_pids", [])) == 1:
        target_pid = int(state["repo_online_pids"][0])

    if not target_pid:
        return {
            "stopped": False,
            "message": "No stoppable OSRS backend process found for this council.",
            **state,
        }

    await pm.stop(int(target_pid), grace_seconds=float(payload.grace_seconds))

    entries = await pm.get_status()
    state = _collect_runtime_state(repo, int(port), entries, log_file)
    return {
        "stopped": not state["running"],
        "message": "OSRS backend stop sequence completed.",
        "force_kill_requested": bool(payload.force_kill),
        **state,
    }
