"""Helper script to probe gamemodes and show the detector decision."""

from __future__ import annotations

import argparse
from typing import Dict, List, Tuple

import sys
from pathlib import Path

# Allow running directly from repo root.
sys.path.append(str(Path(__file__).resolve().parents[1]))

from core.constants import GAME_MODES
from core.hiscore_client import HiscoreClient, PlayerNotFoundError
from web.services.detect_mode import detect_mode


IRON_FAMILY: Tuple[str, ...] = ("hardcore", "hardcore_group_ironman", "ironman", "group_ironman", "ultimate")
DEFAULT_PROBE_ORDER: Tuple[str, ...] = IRON_FAMILY + ("main", "tournament", "seasonal", "deadman")


def extract_overall(data: Dict) -> Tuple[int | None, int | None]:
    skills = data.get("skills")
    if isinstance(skills, list) and skills:
        first = skills[0]
        if isinstance(first, dict):
            return first.get("xp"), first.get("level")
        if isinstance(first, (list, tuple)) and len(first) >= 3:
            return first[2], first[1]
    return None, None


def probe(player: str, modes: List[str]) -> Dict[str, Dict]:
    results: Dict[str, Dict] = {}
    with HiscoreClient() as client:
        for mode in modes:
            if mode not in GAME_MODES:
                continue
            try:
                resp = client.fetch(player, mode)
                xp, level = extract_overall(resp.data)
                results[mode] = {"status": "found", "xp": xp, "level": level, "url": resp.url}
            except PlayerNotFoundError:
                results[mode] = {"status": "not_found"}
            except Exception as exc:
                results[mode] = {"status": "error", "error": str(exc)}
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Probe OSRS gamemodes for a player and show detector choice.")
    parser.add_argument("player", help="RSN to probe (e.g. sleds)")
    parser.add_argument(
        "--modes",
        nargs="+",
        default=list(DEFAULT_PROBE_ORDER),
        help="Modes to test (default: iron family + main + tournament/seasonal/deadman)",
    )
    args = parser.parse_args()

    modes = []
    for mode in args.modes:
        if mode in GAME_MODES and mode not in modes:
            modes.append(mode)

    print(f"Probing modes for '{args.player}'...")
    results = probe(args.player, modes)
    for mode in modes:
        res = results.get(mode)
        if not res:
            continue
        status = res.get("status")
        if status != "found":
            print(f"- {mode}: {status}")
        else:
            print(f"- {mode}: xp={res.get('xp')} level={res.get('level')} url={res.get('url')}")

    decision = detect_mode(args.player, requested_mode="auto")
    print("\nDetector result:")
    print(decision)


if __name__ == "__main__":
    main()
