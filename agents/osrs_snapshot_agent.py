"""Snapshot agent for fetching and persisting OSRS hiscore data."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

from core.clipboard import copy_json_snippet
from core.constants import DEFAULT_MODE, GAME_MODES
from core.hiscore_client import HiscoreClient, HiscoreResponse, PlayerNotFoundError
from support.scribe_reporter import report_snapshot

AGENT_VERSION = "0.1.0"


@dataclass(slots=True)
class SnapshotResult:
    player: str
    mode: str
    snapshot_path: Path | None
    success: bool
    message: str
    response: HiscoreResponse | None = None


class SnapshotAgent:
    """Coordinates snapshot fetch, persistence, and clipboard export."""

    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _snapshot_path(self, player: str, timestamp: datetime) -> Path:
        safe_player = player.replace(" ", "_")
        directory = self.output_dir / safe_player
        directory.mkdir(parents=True, exist_ok=True)
        filename = timestamp.strftime("%Y%m%d_%H%M%S.json")
        return directory / filename

    def run(self, accounts: Iterable[Dict[str, str]]) -> List[SnapshotResult]:
        results: List[SnapshotResult] = []

        with HiscoreClient() as client:
            for account in accounts:
                player = account["name"]
                mode = (account.get("mode") or DEFAULT_MODE).lower()
                if mode not in GAME_MODES:
                    mode = DEFAULT_MODE
                timestamp = datetime.now(timezone.utc)
                start = datetime.now(timezone.utc)
                try:
                    response = client.fetch(player, mode)
                    latency = (datetime.now(timezone.utc) - start).total_seconds() * 1000
                except PlayerNotFoundError:
                    latency = (datetime.now(timezone.utc) - start).total_seconds() * 1000
                    report_snapshot(
                        player=player,
                        mode=mode,
                        success=False,
                        message="Player not found",
                        snapshot_path=None,
                        latency_ms=latency,
                    )
                    results.append(
                        SnapshotResult(
                            player=player,
                            mode=mode,
                            snapshot_path=None,
                            success=False,
                            message="Player not found",
                        )
                    )
                    continue
                except Exception as exc:  # pragma: no cover - network failures
                    latency = (datetime.now(timezone.utc) - start).total_seconds() * 1000
                    report_snapshot(
                        player=player,
                        mode=mode,
                        success=False,
                        message=str(exc),
                        snapshot_path=None,
                        latency_ms=None,
                    )
                    results.append(
                        SnapshotResult(
                            player=player,
                            mode=mode,
                            snapshot_path=None,
                            success=False,
                            message=str(exc),
                        )
                    )
                    continue

                target = self._snapshot_path(player, timestamp)
                payload_timestamp = timestamp.isoformat()
                payload = {
                    "metadata": {
                        "player": player,
                        "mode": mode,
                        "fetched_at": payload_timestamp,
                        "endpoint": response.url,
                        "latency_ms": round(latency, 2),
                        "agent_version": AGENT_VERSION,
                    },
                    "data": response.data,
                }
                target.write_text(json.dumps(payload, indent=2), encoding="utf-8")

                copy_json_snippet(payload)

                report_snapshot(
                    player=player,
                    mode=mode,
                    success=True,
                    message="Snapshot stored",
                    snapshot_path=target,
                    latency_ms=round(latency, 2),
                )

                results.append(
                    SnapshotResult(
                        player=player,
                        mode=mode,
                        snapshot_path=target,
                        success=True,
                        message="Snapshot stored",
                        response=response,
                    )
                )

        return results
