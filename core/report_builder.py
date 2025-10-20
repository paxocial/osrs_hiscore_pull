"""Markdown report generation for OSRS snapshots."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


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

    notable_activities = _filter_notable_activities(data.get("activities", []))
    if notable_activities:
        lines.append("")
        lines.append("## Activities (Notable)")
        lines.append("")
        lines.append("| Activity | Score |")
        lines.append("| -------- | ----- |")
        for activity in notable_activities:
            name = activity.get("name")
            score = _safe_int(activity.get("score"))
            lines.append(f"| {name} | {score:,} |")

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
    return sum(_safe_int(skill.get("level")) for skill in skills)


def _safe_int(value: Any) -> int:
    if isinstance(value, (int, float)):
        return int(value)
    return 0


def _filter_notable_activities(activities: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    notable = []
    for activity in activities:
        score = activity.get("score")
        if isinstance(score, (int, float)) and score > 0:
            notable.append(activity)
    return notable


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
        return "No changes recorded."
    return " | ".join(fragments)


def _truncate_json(snapshot: Dict[str, Any], limit: int = 2048) -> str:
    import json

    raw = json.dumps(snapshot, indent=2)
    if len(raw) <= limit:
        return raw
    return raw[: limit - 3] + "..."


def write_report(content: str, report_path: Path) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(content, encoding="utf-8")
