"""Snapshot normalization and delta utilities."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Iterable, List, Optional, Tuple


def normalize_snapshot_data(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """Return a sanitized copy of the snapshot data."""
    data = deepcopy(raw_data)

    for skill in data.get("skills", []):
        _sanitize_number_fields(skill, ("rank", "level", "xp"))

    for activity in data.get("activities", []):
        _sanitize_number_fields(activity, ("rank", "score"))

    return data


def _sanitize_number_fields(item: Dict[str, Any], keys: Iterable[str]) -> None:
    for key in keys:
        value = item.get(key)
        if isinstance(value, (int, float)) and value < 0:
            item[key] = None


def compute_snapshot_delta(
    previous: Dict[str, Any], current: Dict[str, Any]
) -> Dict[str, Any]:
    """Compute deltas between two normalized snapshot payloads."""
    prev_skills = _index_by_name(previous.get("skills", []))
    curr_skills = _index_by_name(current.get("skills", []))
    prev_activities = _index_by_name(previous.get("activities", []))
    curr_activities = _index_by_name(current.get("activities", []))

    skill_deltas: List[Dict[str, Any]] = []
    for name, current_skill in curr_skills.items():
        prev_skill = prev_skills.get(name, {})
        xp_delta = _number_delta(prev_skill.get("xp"), current_skill.get("xp"))
        level_delta = _number_delta(prev_skill.get("level"), current_skill.get("level"))
        if xp_delta > 0 or level_delta > 0:
            skill_deltas.append(
                {
                    "name": name,
                    "xp_delta": xp_delta,
                    "level_delta": level_delta,
                }
            )

    activity_deltas: List[Dict[str, Any]] = []
    for name, current_activity in curr_activities.items():
        prev_activity = prev_activities.get(name, {})
        score_delta = _number_delta(prev_activity.get("score"), current_activity.get("score"))
        if score_delta > 0:
            activity_deltas.append(
                {
                    "name": name,
                    "score_delta": score_delta,
                }
            )

    total_xp_prev = sum(_safe_number(skill.get("xp")) for skill in previous.get("skills", []))
    total_xp_curr = sum(_safe_number(skill.get("xp")) for skill in current.get("skills", []))
    total_xp_delta = total_xp_curr - total_xp_prev

    return {
        "total_xp_delta": total_xp_delta,
        "skill_deltas": sorted(skill_deltas, key=lambda item: item["xp_delta"], reverse=True),
        "activity_deltas": sorted(activity_deltas, key=lambda item: item["score_delta"], reverse=True),
    }


def _index_by_name(entries: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {entry.get("name"): entry for entry in entries if entry.get("name")}


def _safe_number(value: Optional[Any]) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    return 0.0


def _number_delta(old: Optional[Any], new: Optional[Any]) -> float:
    return _safe_number(new) - _safe_number(old)


def summarize_delta(delta: Dict[str, Any]) -> str:
    total_xp_delta = int(delta.get("total_xp_delta", 0))
    skill_deltas: List[Dict[str, Any]] = delta.get("skill_deltas", [])
    activity_deltas: List[Dict[str, Any]] = delta.get("activity_deltas", [])

    fragments: List[str] = []

    if total_xp_delta:
        fragments.append(f"ΔXP {format_number(total_xp_delta)}")

    leveled = [
        skill
        for skill in skill_deltas
        if skill.get("level_delta", 0) > 0
    ]

    if leveled:
        fragments.append(
            "Levels: "
            + ", ".join(
                f"{skill['name']}(+{int(skill['level_delta'])})"
                for skill in leveled[:3]
            )
        )
    elif skill_deltas:
        fragments.append(
            "XP gains: "
            + ", ".join(
                f"{skill['name']}({format_number(int(skill['xp_delta']))})"
                for skill in skill_deltas[:3]
            )
        )

    if activity_deltas:
        fragments.append(
            "Activities: "
            + ", ".join(
                f"{activity['name']}(+{int(activity['score_delta'])})"
                for activity in activity_deltas[:3]
            )
        )

    if not fragments:
        return "No changes since last snapshot."

    return " | ".join(fragments)


def format_number(value: int) -> str:
    abs_value = abs(value)
    if abs_value >= 1_000_000_000:
        formatted = f"{value / 1_000_000_000:.2f}B"
    elif abs_value >= 1_000_000:
        formatted = f"{value / 1_000_000:.2f}M"
    elif abs_value >= 1_000:
        formatted = f"{value / 1_000:.2f}K"
    else:
        formatted = str(value)
    if formatted.startswith("-0.00"):
        formatted = "0"
    return formatted
