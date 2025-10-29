"""Markdown report generation for OSRS snapshots."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple
import hashlib
import json

from .constants import CLUE_ACTIVITIES, MINIGAME_ACTIVITIES, BOSS_ACTIVITIES, POINT_ACTIVITIES


def build_report_content(snapshot: Dict[str, Any]) -> str:
    metadata = snapshot.get("metadata", {})
    data = snapshot.get("data", {})
    delta = snapshot.get("delta")

    player = metadata.get("player", "Unknown")
    resolved_mode = metadata.get("resolved_mode") or metadata.get("mode", "main")
    fetched_at = metadata.get("fetched_at")
    fetched_at_fmt = _format_timestamp(fetched_at)
    total_xp = _total_xp(data.get("skills", []))
    total_level = _total_level(data.get("skills", []))
    snapshot_hash = _snapshot_hash(snapshot)

    lines = [
        f"# OSRS Snapshot Report — {player}",
        "",
        f"- **Player:** {player}",
        f"- **Mode:** {resolved_mode}",
        f"- **Fetched:** {fetched_at_fmt}",
        f"- **Total XP:** {total_xp:,}",
        f"- **Total Level:** {total_level}",
    ]

    if delta and isinstance(delta, dict):
        lines.append(f"- **Changes:** {_summarize_delta(delta)}")
    else:
        lines.append("- **Changes:** No changes recorded.")

    snapshot_id = metadata.get("snapshot_id")
    if snapshot_id:
        lines.append(f"- **Snapshot ID:** {snapshot_id}")
    lines.append(f"- **Hash:** `{snapshot_hash}`")

    lines.append("")
    lines.append("## Skills")
    lines.append("")
    lines.append("| Skill | Level | XP |")
    lines.append("| ----- | ----- | -- |")
    for skill in data.get("skills", []):
        name = skill.get("name")
        level = _safe_int(skill.get("level"))
        xp = _safe_int(skill.get("xp"))
        if name:
            lines.append(f"| {name} | {level} | {xp:,} |")

    activity_sections = _group_notable_activities(data.get("activities", []))
    if activity_sections:
        lines.append("")
        lines.append("## Activities")
        lines.append("")
        for header, entries in activity_sections:
            lines.append(f"### {header}")
            lines.append("")
            lines.append("| Activity | Score |")
            lines.append("| -------- | ----- |")
            for activity in entries:
                name = activity.get("name")
                score = _safe_int(activity.get("score"))
                lines.append(f"| {name} | {score:,} |")
            lines.append("")

    if delta and isinstance(delta, dict):
        lines.append("## Changes")
        lines.append("")
        skill_rows = _skill_delta_rows(delta)
        if skill_rows:
            lines.append("### Skills")
            lines.append("")
            lines.append("| Skill | ΔXP | ΔLevel |")
            lines.append("| ----- | ---- | ------- |")
            for name, xp_delta, level_delta in skill_rows:
                lines.append(f"| {name} | {xp_delta} | {level_delta} |")
            lines.append("")

        activity_rows = _activity_delta_rows(delta)
        if activity_rows:
            lines.append("### Activities")
            lines.append("")
            lines.append("| Activity | ΔScore |")
            lines.append("| -------- | ------- |")
            for name, score_delta in activity_rows:
                lines.append(f"| {name} | {score_delta} |")
            lines.append("")

    lines.append("")
    lines.append("## Source")
    lines.append("")
    lines.append("```json")
    lines.append(_truncate_json(snapshot))
    lines.append("```")

    return "\n".join(lines)


def _format_timestamp(timestamp: Any) -> str:
    if isinstance(timestamp, str):
        try:
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
        except ValueError:
            return str(timestamp)
    return str(timestamp)


def _total_xp(skills: Iterable[Dict[str, Any]]) -> int:
    return sum(_safe_int(skill.get("xp")) for skill in skills)


def _total_level(skills: Iterable[Dict[str, Any]]) -> int:
    # Exclude "Overall" skill from total level calculation since it already represents the sum
    return sum(_safe_int(skill.get("level")) for skill in skills if skill.get("name") != "Overall")


def _safe_int(value: Any) -> int:
    if isinstance(value, (int, float)):
        return int(value)
    return 0


def _group_notable_activities(activities: Iterable[Dict[str, Any]]) -> List[Tuple[str, List[Dict[str, Any]]]]:
    groups: Dict[str, List[Dict[str, Any]]] = {
        "Clue Scrolls": [],
        "Minigames": [],
        "Bosses": [],
        "Points": [],
        "Other": [],
    }

    for activity in activities:
        score = activity.get("score")
        if not (isinstance(score, (int, float)) and score > 0):
            continue
        name = activity.get("name")
        if not name:
            continue

        key = None
        if name in CLUE_ACTIVITIES.values():
            key = "Clue Scrolls"
        elif name in MINIGAME_ACTIVITIES.values():
            key = "Minigames"
        elif name in BOSS_ACTIVITIES.values():
            key = "Bosses"
        elif name in POINT_ACTIVITIES.values():
            key = "Points"
        else:
            key = "Other"
        groups[key].append(activity)

    return [(category, entries) for category, entries in groups.items() if entries]


def _summarize_delta(delta: Dict[str, Any]) -> str:
    total_xp_delta = int(delta.get("total_xp_delta", 0))
    skill_deltas: List[Dict[str, Any]] = delta.get("skill_deltas", [])
    leveled = [skill for skill in skill_deltas if skill.get("level_delta")]
    xp_highlights = [
        skill for skill in skill_deltas if skill.get("xp_delta") and skill.get("xp_delta") > 0
    ]

    fragments = []
    if total_xp_delta:
        fragments.append(f"ΔXP {total_xp_delta:,}")
    if leveled:
        fragments.append(
            "Levels " + ", ".join(f"{skill['name']} (+{int(skill['level_delta'])})" for skill in leveled[:3])
        )
    elif xp_highlights:
        fragments.append(
            "XP " + ", ".join(f"{skill['name']} (+{int(skill['xp_delta'])})" for skill in xp_highlights[:3])
        )
    if not fragments:
        return "No recorded gains."
    return " | ".join(fragments)


def _truncate_json(snapshot: Dict[str, Any], limit: int = 2048) -> str:
    raw = json.dumps(snapshot, indent=2)
    if len(raw) <= limit:
        return raw
    return raw[: limit - 3] + "..."


def _snapshot_hash(snapshot: Dict[str, Any]) -> str:
    encoded = json.dumps(snapshot, sort_keys=True).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _skill_delta_rows(delta: Dict[str, Any]) -> List[Tuple[str, str, str]]:
    rows = []
    for entry in delta.get("skill_deltas", []):
        name = entry.get("name")
        if not name:
            continue
        xp_delta = int(entry.get("xp_delta", 0))
        level_delta = int(entry.get("level_delta", 0))
        if xp_delta == 0 and level_delta == 0:
            continue
        rows.append((name, f"{xp_delta:+,}", f"{level_delta:+d}"))
    return rows


def _activity_delta_rows(delta: Dict[str, Any]) -> List[Tuple[str, str]]:
    rows = []
    for entry in delta.get("activity_deltas", []):
        name = entry.get("name")
        if not name:
            continue
        score_delta = int(entry.get("score_delta", 0))
        if score_delta == 0:
            continue
        rows.append((name, f"{score_delta:+,}"))
    return rows


def write_report(content: str, report_path: Path) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(content, encoding="utf-8")
