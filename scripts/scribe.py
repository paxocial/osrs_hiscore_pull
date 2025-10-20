#!/usr/bin/env python3
"""Utility for appending structured progress log entries."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence, Tuple


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = ROOT_DIR / "config" / "project.json"

STATUS_EMOJI = {
    "info": "ℹ️",
    "success": "✅",
    "warn": "⚠️",
    "error": "❌",
    "bug": "🐞",
    "plan": "🧭",
}


def load_config(path: Path) -> Dict[str, str]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError as exc:
        raise SystemExit(f"Config file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Config file is not valid JSON: {path}") from exc


def parse_meta(pairs: Iterable[str]) -> Tuple[Tuple[str, str], ...]:
    extracted = []
    for pair in pairs:
        if "=" not in pair:
            raise SystemExit(f"Meta value must be key=value, received: {pair}")
        key, value = pair.split("=", 1)
        key, value = key.strip(), value.strip()
        if not key:
            raise SystemExit("Meta key cannot be empty.")
        extracted.append((key, value))
    return tuple(extracted)


def format_entry(
    message: str,
    emoji: str,
    agent: Optional[str],
    project_name: Optional[str],
    meta: Tuple[Tuple[str, str], ...],
    timestamp: Optional[str],
) -> str:
    if timestamp is None:
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    if not emoji:
        emoji = "📝"

    segments = [f"[{emoji}]", f"[{timestamp}]"]

    if agent:
        segments.append(f"[Agent: {agent}]")

    if project_name:
        segments.append(f"[Project: {project_name}]")

    entry = " ".join(segments) + f" {message}"

    if meta:
        meta_str = "; ".join(f"{key}={value}" for key, value in meta)
        entry += f" | {meta_str}"

    return entry


def append_log(path: Path, entry: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(entry)
        if not entry.endswith("\n"):
            handle.write("\n")


def log_progress(
    message: str,
    *,
    emoji: Optional[str] = None,
    status: Optional[str] = None,
    agent: Optional[str] = None,
    meta: Optional[Mapping[str, Any]] = None,
    config_path: Optional[Path] = None,
    timestamp: Optional[str] = None,
    dry_run: bool = False,
) -> str:
    config_path = config_path or DEFAULT_CONFIG_PATH
    config = load_config(config_path)

    progress_log = config.get("progress_log")
    if not progress_log:
        raise ValueError("Config file is missing 'progress_log'.")

    project_name = config.get("project_name")
    default_emoji = config.get("default_emoji", "📝")
    default_agent = config.get("default_agent")

    resolved_emoji = emoji
    if not resolved_emoji and status:
        resolved_emoji = STATUS_EMOJI.get(status)
    if not resolved_emoji:
        resolved_emoji = default_emoji
    if not resolved_emoji:
        raise ValueError("Emoji is required; provide emoji/status or set default_emoji.")

    resolved_agent = agent or default_agent

    meta_pairs: Tuple[Tuple[str, str], ...] = ()
    if meta:
        meta_pairs = tuple((str(key), str(value)) for key, value in meta.items())

    entry = format_entry(
        message=message,
        emoji=resolved_emoji,
        agent=resolved_agent,
        project_name=project_name,
        meta=meta_pairs,
        timestamp=timestamp,
    )

    log_path = Path(progress_log)
    if not log_path.is_absolute():
        log_path = ROOT_DIR / log_path

    if dry_run:
        return entry

    append_log(log_path, entry)
    return entry


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Append a formatted entry to the project progress log."
    )
    parser.add_argument("message", help="Primary log message.")
    status_help = ", ".join(f"{name!r}" for name in STATUS_EMOJI)
    parser.add_argument(
        "-e",
        "--emoji",
        help="Emoji or short indicator to include in the entry.",
    )
    parser.add_argument(
        "-s",
        "--status",
        choices=sorted(STATUS_EMOJI),
        help=f"Named status mapped to an emoji ({status_help}).",
    )
    parser.add_argument(
        "-a",
        "--agent",
        help="Name of the agent or component producing the entry.",
    )
    parser.add_argument(
        "-m",
        "--meta",
        action="append",
        default=[],
        help="Additional metadata as key=value pairs. Option may be repeated.",
    )
    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        default=None,
        help=f"Path to project config (default: {DEFAULT_CONFIG_PATH}).",
    )
    parser.add_argument(
        "-t",
        "--timestamp",
        help="Override timestamp text (default: current UTC time).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the formatted entry without writing to disk.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv or sys.argv[1:])

    config_path = args.config or DEFAULT_CONFIG_PATH

    meta = parse_meta(args.meta)

    try:
        entry = log_progress(
            message=args.message,
            emoji=args.emoji,
            status=args.status,
            agent=args.agent,
            meta=dict(meta),
            config_path=config_path,
            timestamp=args.timestamp,
            dry_run=args.dry_run,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    if args.dry_run:
        print(entry)
    else:
        config = load_config(config_path)
        progress_log = config.get("progress_log")
        log_path = Path(progress_log)
        if not log_path.is_absolute():
            log_path = ROOT_DIR / log_path
        print(f"Wrote entry to {log_path}:")
        print(entry)


if __name__ == "__main__":
    main()
