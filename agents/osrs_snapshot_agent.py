"""Snapshot agent for fetching and persisting OSRS hiscore data."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from uuid import NAMESPACE_URL, uuid5

from core.clipboard import copy_json_snippet
from core.constants import DEFAULT_MODE, GAME_MODES
from core.hiscore_client import HiscoreClient, HiscoreResponse, PlayerNotFoundError
from core.mode_cache import ModeCache
from core.processing import compute_snapshot_delta, normalize_snapshot_data, summarize_delta
from support.scribe_reporter import report_snapshot

AGENT_VERSION = "0.1.0"
SCHEMA_VERSION = "1.1"
DEFAULT_MODE_CACHE_PATH = Path("config/mode_cache.json")


@dataclass(slots=True)
class SnapshotResult:
    player: str
    mode: str
    snapshot_path: Path | None
    success: bool
    message: str
    response: HiscoreResponse | None = None
    metadata: Dict[str, Any] | None = None
    payload: Dict[str, Any] | None = None
    delta: Dict[str, Any] | None = None
    delta_summary: str | None = None


class SnapshotAgent:
    """Coordinates snapshot fetch, persistence, and clipboard export."""

    def __init__(
        self,
        output_dir: Path,
        *,
        mode_cache_path: Optional[Path] = None,
        config_path: Optional[Path] = None,
    ) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.mode_cache = ModeCache(mode_cache_path or DEFAULT_MODE_CACHE_PATH)
        self.scribe_config_path = config_path

    def _snapshot_path(self, player: str, timestamp: datetime) -> Path:
        safe_player = player.replace(" ", "_")
        directory = self.output_dir / safe_player
        directory.mkdir(parents=True, exist_ok=True)
        filename = timestamp.strftime("%Y%m%d_%H%M%S.json")
        return directory / filename

    def _candidate_modes(self, player: str, requested_mode: str) -> List[str]:
        candidates: List[str] = []
        # Auto-detect: skip the requested slot and rely on cache + all modes.
        if requested_mode not in ("auto", "auto-detect"):
            if requested_mode in GAME_MODES:
                candidates.append(requested_mode)

        cache_mode = self.mode_cache.get(player)
        if cache_mode and cache_mode in GAME_MODES and cache_mode not in candidates:
            candidates.append(cache_mode)

        for mode in GAME_MODES.keys():
            if mode not in candidates:
                candidates.append(mode)
        return candidates

    def _previous_snapshot_path(self, player: str, exclude: Path) -> Optional[Path]:
        safe_player = player.replace(" ", "_")
        directory = self.output_dir / safe_player
        if not directory.exists():
            return None
        snapshots = sorted(
            [path for path in directory.glob("*.json") if path != exclude]
        )
        if not snapshots:
            return None
        return snapshots[-1]

    def _load_snapshot(self, path: Path) -> Dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8"))

    def run(self, accounts: Iterable[Dict[str, str]]) -> List[SnapshotResult]:
        results: List[SnapshotResult] = []

        with HiscoreClient() as client:
            for account in accounts:
                player = account["name"]
                raw_mode = (account.get("mode") or DEFAULT_MODE).lower()
                if raw_mode in ("auto", "auto-detect"):
                    requested_mode = "auto"
                elif raw_mode in GAME_MODES:
                    requested_mode = raw_mode
                else:
                    requested_mode = DEFAULT_MODE

                response: Optional[HiscoreResponse] = None
                resolved_mode: Optional[str] = None
                latency_ms: Optional[float] = None
                last_error = "Player not found"

                for candidate in self._candidate_modes(player, requested_mode):
                    start = datetime.now(timezone.utc)
                    try:
                        candidate_response = client.fetch(player, candidate)
                        latency_ms = (datetime.now(timezone.utc) - start).total_seconds() * 1000
                        response = candidate_response
                        resolved_mode = candidate
                        break
                    except PlayerNotFoundError:
                        latency_ms = (datetime.now(timezone.utc) - start).total_seconds() * 1000
                        last_error = "Player not found"
                        continue
                    except Exception as exc:  # pragma: no cover - network failures
                        latency_ms = (datetime.now(timezone.utc) - start).total_seconds() * 1000
                        last_error = str(exc)
                        continue

                if response is None or resolved_mode is None:
                    report_snapshot(
                        player=player,
                        mode=requested_mode,
                        success=False,
                        message=last_error,
                        snapshot_path=None,
                        latency_ms=latency_ms,
                        expected_mode=requested_mode,
                        resolved_mode=None,
                        config_path=self.scribe_config_path,
                        agent_name="SnapshotAgent",
                    )
                    results.append(
                        SnapshotResult(
                            player=player,
                            mode=requested_mode,
                            snapshot_path=None,
                            success=False,
                            message=last_error,
                        )
                    )
                    continue

                timestamp = datetime.now(timezone.utc)
                snapshot_path = self._snapshot_path(player, timestamp)
                payload_timestamp = timestamp.isoformat()
                snapshot_id = str(uuid5(NAMESPACE_URL, f"osrs:{player}:{payload_timestamp}"))

                normalized_data = normalize_snapshot_data(response.data)

                payload: Dict[str, Any] = {
                    "metadata": {
                        "schema_version": SCHEMA_VERSION,
                        "snapshot_id": snapshot_id,
                        "player": player,
                        "requested_mode": requested_mode,
                        "resolved_mode": resolved_mode,
                        "fetched_at": payload_timestamp,
                        "fetched_at_unix": int(timestamp.timestamp()),
                        "endpoint": response.url,
                        "latency_ms": round(latency_ms, 2) if latency_ms is not None else None,
                        "agent_version": AGENT_VERSION,
                    },
                    "data": normalized_data,
                }

                previous_path = self._previous_snapshot_path(player, snapshot_path)
                if previous_path:
                    previous_payload = self._load_snapshot(previous_path)
                    delta = compute_snapshot_delta(previous_payload.get("data", {}), normalized_data)
                    payload["delta"] = delta
                    delta_summary = summarize_delta(delta)
                else:
                    delta_summary = "Initial snapshot."
                    payload["delta"] = None

                snapshot_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

                copy_json_snippet({"metadata": payload["metadata"], "delta_summary": delta_summary})

                report_snapshot(
                    player=player,
                    mode=resolved_mode,
                    success=True,
                    message=f"Snapshot stored — {delta_summary}",
                    snapshot_path=snapshot_path,
                    latency_ms=latency_ms,
                    expected_mode=requested_mode,
                    resolved_mode=resolved_mode,
                    snapshot_id=snapshot_id,
                    delta_summary=delta_summary,
                    config_path=self.scribe_config_path,
                    agent_name="SnapshotAgent",
                )

                results.append(
                    SnapshotResult(
                        player=player,
                        mode=resolved_mode,
                        snapshot_path=snapshot_path,
                        success=True,
                        message=delta_summary,
                        response=response,
                        metadata=payload["metadata"],
                        payload=payload,
                        delta=payload.get("delta"),
                        delta_summary=delta_summary,
                    )
                )

                self.mode_cache.update(player, resolved_mode)

        self.mode_cache.persist()
        return results
