"""Shared mode detection helper for web UI."""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple
from pathlib import Path

from core.constants import GAME_MODES
from core.mode_cache import ModeCache
from core.hiscore_client import HiscoreClient, PlayerNotFoundError


IRON_FAMILY: Tuple[str, ...] = ("hardcore", "hardcore_group_ironman", "ironman", "group_ironman", "ultimate")
FALLBACK_MODES: Tuple[str, ...] = ("main", "tournament", "seasonal", "deadman")
STABLE_CACHED_MODES: Tuple[str, ...] = ("ironman", "group_ironman", "ultimate", "main")


def _extract_overall(data: Dict) -> Tuple[Optional[int], Optional[int]]:
    """Extract total XP/level from a hiscore payload; tolerate multiple shapes."""
    try:
        skills = data.get("skills")
        if isinstance(skills, list) and skills:
            first = skills[0]
            if isinstance(first, dict):
                return first.get("xp"), first.get("level")
            if isinstance(first, (list, tuple)) and len(first) >= 3:
                return first[2], first[1]
    except Exception:
        pass
    return None, None


def _xp_value(entry: Dict) -> int:
    xp = entry.get("xp")
    try:
        return int(xp)
    except Exception:
        return -1


def _pick_best_mode(successes: Dict[str, Dict]) -> str:
    """Choose the best mode from successful fetches."""
    iron_candidates = {m: successes[m] for m in IRON_FAMILY if m in successes}

    # Handle fallen hardcores (compare hardcore vs ironman)
    if "hardcore" in iron_candidates and "ironman" in iron_candidates:
        hc = iron_candidates["hardcore"]
        im = iron_candidates["ironman"]
        if _xp_value(im) > _xp_value(hc):
            return "ironman"
        # Tie or hardcore higher: keep hardcore
        return "hardcore"

    # Handle fallen hardcore group ironman
    if "hardcore_group_ironman" in iron_candidates and "group_ironman" in iron_candidates:
        hcg = iron_candidates["hardcore_group_ironman"]
        gi = iron_candidates["group_ironman"]
        if _xp_value(gi) > _xp_value(hcg):
            return "group_ironman"
        return "hardcore_group_ironman"

    if iron_candidates:
        priority = {m: i for i, m in enumerate(IRON_FAMILY)}
        best = max(
            iron_candidates.items(),
            key=lambda kv: (_xp_value(kv[1]), -priority.get(kv[0], 0)),
        )
        return best[0]

    if "main" in successes:
        return "main"

    # If no iron/main, pick any success with highest XP
    best = max(successes.items(), key=lambda kv: _xp_value(kv[1]))
    return best[0]


def detect_mode(
    player: str,
    requested_mode: str = "auto",
    cache_path: Path = Path("config/mode_cache.json"),
    force: bool = False,
) -> dict:
    cache = ModeCache(cache_path)
    requested_mode = (requested_mode or "auto").lower().strip()
    cache_mode = cache.get(player)

    # If we have a stable cached mode, trust it and skip probing.
    if not force and requested_mode in ("auto", "auto-detect") and cache_mode in STABLE_CACHED_MODES:
        return {
            "status": "found",
            "mode": cache_mode,
            "cached": True,
            "tested_modes": [],
        }

    # If explicit mode requested (not auto), honor it directly.
    if requested_mode not in ("auto", "auto-detect"):
        if requested_mode not in GAME_MODES:
            return {"status": "error", "error": f"Unknown mode: {requested_mode}"}
        try:
            with HiscoreClient() as client:
                resp = client.fetch(player, requested_mode)
            cache.update(player, requested_mode)
            cache.persist()
            xp, level = _extract_overall(resp.data)
            return {"status": "found", "mode": requested_mode, "url": resp.url, "xp": xp, "level": level}
        except PlayerNotFoundError:
            return {"status": "not_found"}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    # Auto-detect: probe iron family + fallbacks and choose best by XP.
    def _add_unique(seq: List[str], mode: str) -> None:
        if mode in GAME_MODES and mode not in seq:
            seq.append(mode)

    candidates: List[str] = []
    if cache_mode:
        _add_unique(candidates, cache_mode)
    for mode in IRON_FAMILY:
        _add_unique(candidates, mode)
    for mode in FALLBACK_MODES:
        _add_unique(candidates, mode)
    for mode in GAME_MODES.keys():
        _add_unique(candidates, mode)

    successes: Dict[str, Dict] = {}
    with HiscoreClient() as client:
        for mode in candidates:
            try:
                resp = client.fetch(player, mode)
                xp, level = _extract_overall(resp.data)
                successes[mode] = {"xp": xp, "level": level, "url": resp.url}
            except PlayerNotFoundError:
                continue
            except Exception as exc:
                return {"status": "error", "error": str(exc)}

    if not successes:
        return {"status": "not_found"}

    best_mode = _pick_best_mode(successes)
    cache.update(player, best_mode)
    cache.persist()

    result = {"status": "found", "mode": best_mode, "url": successes[best_mode]["url"]}
    result.update({k: v for k, v in successes[best_mode].items() if k in ("xp", "level")})
    result["tested_modes"] = list(successes.keys())
    return result
