"""Clipboard helper for copying snapshot summaries."""

from __future__ import annotations

import json
from typing import Any

try:
    import pyperclip
except ImportError:  # pragma: no cover - runtime fallback
    pyperclip = None  # type: ignore[assignment]


def copy_text(text: str) -> bool:
    """Copy arbitrary text to the clipboard when supported."""
    if pyperclip is None:
        return False

    try:
        pyperclip.copy(text)
    except pyperclip.PyperclipException:  # type: ignore[attr-defined]
        return False
    return True


def copy_json_snippet(data: Any) -> bool:
    """Copy a JSON snippet to the clipboard if supported."""
    snippet = json.dumps(data, indent=2)
    return copy_text(snippet)
