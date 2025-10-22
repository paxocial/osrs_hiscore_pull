"""Helpers for recording snapshot activity via Scribe."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from scripts.scribe import log_progress


def report_snapshot(
    *,
    player: str,
    mode: str,
    success: bool,
    message: str,
    snapshot_path: Optional[Path],
    latency_ms: Optional[float],
    expected_mode: Optional[str] = None,
    resolved_mode: Optional[str] = None,
    snapshot_id: Optional[str] = None,
    delta_summary: Optional[str] = None,
    config_path: Optional[Path] = None,
    agent_name: str = "SnapshotAgent",
) -> None:
    status = "success" if success else "error"
    resolved = resolved_mode or mode
    meta = {
        "player": player,
        "mode": resolved,
        "result": "success" if success else "failure",
    }
    if snapshot_path:
        meta["path"] = str(snapshot_path)
    if latency_ms is not None:
        meta["latency_ms"] = f"{latency_ms:.2f}"
    if expected_mode:
        meta["expected_mode"] = expected_mode
    if resolved_mode:
        meta["resolved_mode"] = resolved_mode
    if snapshot_id:
        meta["snapshot_id"] = snapshot_id
    if delta_summary:
        meta["summary"] = delta_summary

    log_progress(
        message=f"{agent_name} event for {player}: {message}",
        status=status,
        agent=agent_name,
        meta=meta,
        config_path=config_path,
    )
