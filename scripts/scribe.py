#!/usr/bin/env python3
"""Utility for appending structured progress log entries."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple


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

    segments = [f"[{timestamp}]", f"[{emoji}]"]

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


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
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


def main(argv: Iterable[str] | None = None) -> None:
    args = parse_args(argv or sys.argv[1:])

    config_path = args.config or DEFAULT_CONFIG_PATH
    config = load_config(config_path)

    progress_log = config.get("progress_log")
    if not progress_log:
        raise SystemExit("Config file is missing 'progress_log'.")

    project_name = config.get("project_name")
    default_emoji = config.get("default_emoji", "📝")
    default_agent = config.get("default_agent")

    emoji = args.emoji
    if not emoji and args.status:
        emoji = STATUS_EMOJI.get(args.status)
    if not emoji:
        emoji = default_emoji

    if not emoji:
        raise SystemExit("Emoji is required; provide --emoji, --status, or set default_emoji.")

    agent = args.agent or default_agent

    try:
        meta = parse_meta(args.meta)
    except SystemExit as exc:  # allow parse errors to propagate with message
        raise

    entry = format_entry(
        message=args.message,
        emoji=emoji,
        agent=agent,
        project_name=project_name,
        meta=meta,
        timestamp=args.timestamp,
    )

    log_path = Path(progress_log)
    if not log_path.is_absolute():
        log_path = ROOT_DIR / log_path

    if args.dry_run:
        print(entry)
        return

    append_log(log_path, entry)
    print(f"Wrote entry to {log_path}:")
    print(entry)


if __name__ == "__main__":
    main()
