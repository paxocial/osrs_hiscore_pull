"""HTTP client helpers for OSRS hiscore endpoints."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List

import httpx

from .constants import ACTIVITY_LOOKUP, GAME_MODES, SKILLS, get_activity_table_index
from .index_discovery import refresh_activity_index_cache


BASE_URL = "https://secure.runescape.com"
JSON_ENDPOINT = "index_lite.json"
SKILL_PAGE = "overall.ws"
ACTIVITY_PAGE = "overall.ws"

DEFAULT_HEADERS = {
    "User-Agent": "codex-osrs-snapshot/0.1 (+https://github.com/CortaLabs)",
}


class PlayerNotFoundError(RuntimeError):
    """Raised when an RSN cannot be located on the hiscores."""


@dataclass(slots=True)
class HiscoreResponse:
    """Container for API responses."""

    data: Dict[str, Any]
    status_code: int
    url: str


@dataclass(slots=True)
class LeaderboardEntry:
    """Represents a leaderboard row."""

    rank: int
    name: str
    level: int | None
    score: int | None
    dead: bool


class HiscoreClient:
    """Thin wrapper around the OSRS hiscore JSON endpoints."""

    def __init__(self, timeout: float = 10.0) -> None:
        self._client = httpx.Client(timeout=timeout, headers=DEFAULT_HEADERS)

    def _build_url(self, player: str, mode: str) -> str:
        gamemode = GAME_MODES.get(mode) or GAME_MODES["main"]
        return f"{BASE_URL}/m={gamemode.path}/{JSON_ENDPOINT}?player={player}"

    def _build_skill_url(self, skill: str, mode: str, page: int) -> str:
        if skill not in SKILLS:
            raise ValueError(f"Unknown skill: {skill}")
        gamemode = GAME_MODES.get(mode) or GAME_MODES["main"]
        index = SKILLS.index(skill)
        return f"{BASE_URL}/m={gamemode.path}/{SKILL_PAGE}?table={index}&page={page}"

    def _build_activity_url(self, activity: str, mode: str, page: int) -> str:
        if activity not in ACTIVITY_LOOKUP:
            raise ValueError(f"Unknown activity: {activity}")
        gamemode = GAME_MODES.get(mode) or GAME_MODES["main"]
        index = get_activity_table_index(activity)
        if index is None:
            mapping = refresh_activity_index_cache()
            index = mapping.get(activity)
            if index is None:
                raise RuntimeError(f"Activity table index not defined for {activity}")
        return f"{BASE_URL}/m={gamemode.path}/{ACTIVITY_PAGE}?category_type=1&table={index}&page={page}"

    def fetch(self, player: str, mode: str = "main") -> HiscoreResponse:
        url = self._build_url(player, mode)
        response = self._client.get(url)
        if response.status_code in (301, 302, 303, 307, 308, 404):
            raise PlayerNotFoundError(player)
        response.raise_for_status()
        return HiscoreResponse(data=response.json(), status_code=response.status_code, url=str(response.request.url))

    def fetch_modes(self, player: str, modes: Iterable[str]) -> Dict[str, HiscoreResponse]:
        """Fetch multiple gamemodes for a player."""
        results: Dict[str, HiscoreResponse] = {}
        for mode in modes:
            results[mode] = self.fetch(player, mode)
        return results

    def fetch_skill_page(self, skill: str, mode: str = "main", page: int = 1) -> str:
        """Return raw HTML for a skill leaderboard page."""
        url = self._build_skill_url(skill, mode, page)
        response = self._client.get(url)
        response.raise_for_status()
        return response.text

    def fetch_activity_page(self, activity: str, mode: str = "main", page: int = 1) -> str:
        """Return raw HTML for an activity leaderboard page."""
        url = self._build_activity_url(activity, mode, page)
        response = self._client.get(url)
        response.raise_for_status()
        return response.text

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "HiscoreClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
