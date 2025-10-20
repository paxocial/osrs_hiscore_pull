"""Persistent cache for resolved hiscore gamemodes."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional


@dataclass
class ModeRecord:
    mode: str
    updated_at: str


class ModeCache:
    """Keeps track of last known gamemode per player."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._data: Dict[str, ModeRecord] = {}
        self._dirty = False
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return
        for player, record in raw.items():
            mode = record.get("mode")
            updated_at = record.get("updated_at")
            if mode:
                self._data[player] = ModeRecord(mode=mode, updated_at=updated_at or "")

    def get(self, player: str) -> Optional[str]:
        record = self._data.get(player)
        if not record:
            return None
        return record.mode

    def update(self, player: str, mode: str) -> None:
        existing = self._data.get(player)
        if existing and existing.mode == mode:
            return
        timestamp = datetime.now(timezone.utc).isoformat()
        self._data[player] = ModeRecord(mode=mode, updated_at=timestamp)
        self._dirty = True

    def persist(self) -> None:
        if not self._dirty:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            player: {"mode": record.mode, "updated_at": record.updated_at}
            for player, record in self._data.items()
        }
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        self._dirty = False
