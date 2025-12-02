"""Shared mode detection helper for web UI."""

from __future__ import annotations

from typing import List, Optional
from pathlib import Path

from core.constants import GAME_MODES
from core.mode_cache import ModeCache
from core.hiscore_client import HiscoreClient, PlayerNotFoundError


def detect_mode(player: str, requested_mode: str = "auto", cache_path: Path = Path("config/mode_cache.json")) -> dict:
    cache = ModeCache(cache_path)

    def candidates() -> List[str]:
        out: List[str] = []
        if requested_mode not in ("auto", "auto-detect") and requested_mode in GAME_MODES:
            out.append(requested_mode)
        cache_mode = cache.get(player)
        if cache_mode and cache_mode in GAME_MODES and cache_mode not in out:
            out.append(cache_mode)
        for mode in GAME_MODES.keys():
            if mode not in out:
                out.append(mode)
        return out

    with HiscoreClient() as client:
        for mode in candidates():
            try:
                resp = client.fetch(player, mode)
                cache.update(player, mode)
                cache.persist()
                return {"status": "found", "mode": mode, "url": resp.url}
            except PlayerNotFoundError:
                continue
            except Exception as exc:
                return {"status": "error", "error": str(exc)}

    return {"status": "not_found"}
