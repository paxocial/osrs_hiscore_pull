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
    config_path: Optional[Path] = None,
) -> None:
    status = "success" if success else "error"
    meta = {
        "player": player,
        "mode": mode,
        "result": "success" if success else "failure",
    }
    if snapshot_path:
        meta["path"] = str(snapshot_path)
    if latency_ms is not None:
        meta["latency_ms"] = f"{latency_ms:.2f}"

    log_progress(
        message=f"SnapshotAgent fetched hiscore report for {player}: {message}",
        status=status,
        agent="SnapshotAgent",
        meta=meta,
        config_path=config_path,
    )
