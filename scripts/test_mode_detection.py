#!/usr/bin/env python3
"""Quick hiscore mode detection tester."""

from __future__ import annotations

import argparse
from typing import List
from pathlib import Path

from core.constants import GAME_MODES
from core.mode_cache import ModeCache
from core.hiscore_client import HiscoreClient, PlayerNotFoundError


def candidate_modes(player: str, requested_mode: str, cache: ModeCache) -> List[str]:
    candidates: List[str] = []
    if requested_mode not in ("auto", "auto-detect"):
        if requested_mode in GAME_MODES:
            candidates.append(requested_mode)
    cache_mode = cache.get(player)
    if cache_mode and cache_mode in GAME_MODES and cache_mode not in candidates:
        candidates.append(cache_mode)
    for mode in GAME_MODES.keys():
        if mode not in candidates:
            candidates.append(mode)
    return candidates


def detect(player: str, requested_mode: str, cache: ModeCache) -> str:
    with HiscoreClient() as client:
        for mode in candidate_modes(player, requested_mode, cache):
            try:
                resp = client.fetch(player, mode)
                cache.update(player, mode)
                cache.persist()
                return f"{player}: {mode} ({resp.url})"
            except PlayerNotFoundError:
                continue
            except Exception as exc:
                return f"{player}: error {exc}"
    return f"{player}: not found in any mode"


def main() -> None:
    parser = argparse.ArgumentParser(description="Test hiscore mode detection.")
    parser.add_argument("players", nargs="+", help="Player names to test.")
    parser.add_argument("--mode", default="auto", help="Requested mode (default auto-detect).")
    parser.add_argument("--cache", default="config/mode_cache.json", help="Path to mode cache.")
    args = parser.parse_args()

    cache = ModeCache(path=Path(args.cache))
    for player in args.players:
        print(detect(player, args.mode.lower(), cache))


if __name__ == "__main__":
    main()
