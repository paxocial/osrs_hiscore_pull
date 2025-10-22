from pathlib import Path

from core.report_builder import build_report_content, write_report


def sample_snapshot():
    return {
        "metadata": {
            "player": "Tester",
            "resolved_mode": "main",
            "fetched_at": "2025-10-20T00:00:00+00:00",
            "snapshot_id": "abc",
        },
        "data": {
            "skills": [
                {"name": "Attack", "level": 50, "xp": 100000},
                {"name": "Magic", "level": 1, "xp": 0},
            ],
            "activities": [
                {"name": "Tempoross", "score": 85},
                {"name": "Clue Scrolls (all)", "score": 0},
            ],
        },
        "delta": {
            "total_xp_delta": 1000,
            "skill_deltas": [
                {"name": "Attack", "xp_delta": 1000, "level_delta": 1}
            ],
            "activity_deltas": [],
        },
    }


def test_build_report_content():
    snapshot = sample_snapshot()
    content = build_report_content(snapshot)
    assert "OSRS Snapshot Report" in content
    assert "Attack" in content
    assert "Tempoross" in content
    assert "ΔXP" in content
    assert "Hash:" in content
    assert "## Activities" in content


def test_write_report(tmp_path: Path):
    content = "# Title\n"
    report_path = tmp_path / "tester" / "report.md"
    write_report(content, report_path)
    assert report_path.exists()
    assert report_path.read_text(encoding="utf-8") == content
