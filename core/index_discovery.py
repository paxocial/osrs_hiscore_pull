"""Discovery utilities for OSRS hiscore activity indexes."""

from __future__ import annotations

import re
from typing import Dict, Iterable, Tuple

import httpx
from bs4 import BeautifulSoup

from .constants import (
    ACTIVITY_LOOKUP,
    DISPLAY_TO_ACTIVITY,
    DEFAULT_MODE,
    GAME_MODES,
    SKILLS,
    update_activity_table_index,
)


DISCOVERY_ENDPOINT = "https://secure.runescape.com/m={path}/overall.ws?category_type=1"


def fetch_activity_options(mode: str = DEFAULT_MODE, timeout: float = 10.0) -> Iterable[Tuple[str, str]]:
    """Fetch option value/text pairs from the activity leaderboard page."""
    gamemode = GAME_MODES.get(mode) or GAME_MODES[DEFAULT_MODE]
    url = DISCOVERY_ENDPOINT.format(path=gamemode.path)
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(url, headers={"User-Agent": "codex-osrs-snapshot/0.1 discovery"})
            response.raise_for_status()
    except httpx.HTTPError:
        return []
    soup = BeautifulSoup(response.text, "html.parser")
    select = soup.find("select", attrs={"name": "table"})
    if not select:
        return []
    options = []
    for option in select.find_all("option"):
        value = option.get("value")
        label = option.text.strip()
        if value is None or not label:
            continue
        options.append((value, label))
    return options


def normalise_label(label: str) -> str:
    """Ensure labels match our lookup keys."""
    cleaned = re.sub(r"\s+", " ", label).strip()
    return cleaned


def discover_activity_indexes(mode: str = DEFAULT_MODE) -> Dict[str, int]:
    """Discover activity table indexes by scraping the hiscore activity dropdown."""
    options = fetch_activity_options(mode)
    mapping: Dict[str, int] = {}
    for value, label in options:
        label = normalise_label(label)
        activity_key = DISPLAY_TO_ACTIVITY.get(label)
        if activity_key:
            try:
                mapping[activity_key] = int(value)
            except ValueError:
                continue
    return mapping


def sequential_fallback_mapping() -> Dict[str, int]:
    """Derive a best-effort mapping based on known activity order."""
    offset = len(SKILLS)
    mapping: Dict[str, int] = {}
    for index, key in enumerate(ACTIVITY_LOOKUP.keys(), start=offset):
        mapping[key] = index
    return mapping


def refresh_activity_index_cache(mode: str = DEFAULT_MODE, *, allow_fallback: bool = True) -> Dict[str, int]:
    """Refresh the cached activity index mapping."""
    mapping = discover_activity_indexes(mode)
    if not mapping:
        if not allow_fallback:
            raise RuntimeError("Unable to discover activity indexes.")
        mapping = sequential_fallback_mapping()
    update_activity_table_index(mapping)
    return mapping
