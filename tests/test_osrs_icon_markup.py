from __future__ import annotations

from pathlib import Path


ICON_HELPERS = Path(".council/web/static/js/osrs-common.js")


def _helper_body(source: str, helper_name: str) -> str:
    start = source.index(f"function {helper_name}")
    end = source.index("\n    }", start)
    return source[start:end]


def test_icon_helpers_render_nonblocking_image_attributes() -> None:
    source = ICON_HELPERS.read_text(encoding="utf-8")

    for helper_name in ("renderSkillIcon", "renderGameIcon"):
        helper = _helper_body(source, helper_name)
        assert 'loading="lazy"' in helper
        assert 'decoding="async"' in helper
        assert 'fetchpriority="low"' in helper
        assert 'width="20"' in helper
        assert 'height="20"' in helper
