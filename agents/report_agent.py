"""Agent responsible for building Markdown reports from snapshots."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

from core.report_builder import build_report_content, write_report
from support.scribe_reporter import report_snapshot


@dataclass(slots=True)
class ReportResult:
    player: str
    mode: str
    report_path: Path | None
    success: bool
    message: str


class ReportAgent:
    def __init__(self, reports_dir: Path, *, scribe_config: Optional[Path] = None) -> None:
        self.reports_dir = reports_dir
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.scribe_config = scribe_config

    def _report_path(self, player: str, snapshot_id: str) -> Path:
        safe_player = player.replace(" ", "_")
        directory = self.reports_dir / safe_player
        directory.mkdir(parents=True, exist_ok=True)
        return directory / f"{snapshot_id}.md"

    def build(self, snapshot_path: Path) -> ReportResult:
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        metadata: Dict[str, str] = snapshot.get("metadata", {})
        player = metadata.get("player") or "unknown"
        resolved_mode = metadata.get("resolved_mode") or metadata.get("mode") or "main"
        snapshot_id = metadata.get("snapshot_id") or snapshot_path.stem

        if player == "unknown" or not snapshot_id:
            message = "Missing metadata for report"
            report_snapshot(
                player=player,
                mode=resolved_mode,
                success=False,
                message=message,
                snapshot_path=None,
                latency_ms=None,
                config_path=self.scribe_config,
            )
            return ReportResult(player=player, mode=resolved_mode, report_path=None, success=False, message=message)

        content = build_report_content(snapshot)
        report_path = self._report_path(player, snapshot_id)
        write_report(content, report_path)

        report_snapshot(
            player=player,
            mode=resolved_mode,
            success=True,
            message="Report generated",
            snapshot_path=report_path,
            latency_ms=None,
            config_path=self.scribe_config,
            snapshot_id=snapshot_id,
            delta_summary=None,
            expected_mode=None,
            resolved_mode=resolved_mode,
            )

        return ReportResult(player=player, mode=resolved_mode, report_path=report_path, success=True, message="Report generated")
