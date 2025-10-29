from pathlib import Path

from core.report_builder import build_report_content, write_report, _total_level, _total_xp


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


def test_total_level_excludes_overall():
    """Test that _total_level correctly excludes 'Overall' skill from calculation."""
    skills = [
        {"name": "Overall", "level": 952, "xp": 4691325},
        {"name": "Attack", "level": 48, "xp": 87228},
        {"name": "Defence", "level": 45, "xp": 64303},
        {"name": "Strength", "level": 45, "xp": 65500},
        {"name": "Hitpoints", "level": 52, "xp": 133368},
        {"name": "Ranged", "level": 1, "xp": 12},
        {"name": "Prayer", "level": 44, "xp": 60689},
        {"name": "Magic", "level": 63, "xp": 386581},
        {"name": "Cooking", "level": 55, "xp": 179620},
        {"name": "Woodcutting", "level": 48, "xp": 91320},
        {"name": "Fletching", "level": 5, "xp": 500},
        {"name": "Fishing", "level": 63, "xp": 374701},
        {"name": "Firemaking", "level": 50, "xp": 103200},
        {"name": "Crafting", "level": 54, "xp": 164842},
        {"name": "Smithing", "level": 49, "xp": 92800},
        {"name": "Mining", "level": 76, "xp": 1439935},
        {"name": "Herblore", "level": 19, "xp": 4275},
        {"name": "Agility", "level": 60, "xp": 276656},
        {"name": "Thieving", "level": 29, "xp": 13119},
        {"name": "Slayer", "level": 26, "xp": 9561},
        {"name": "Farming", "level": 19, "xp": 4000},
        {"name": "Runecraft", "level": 74, "xp": 1130714},
        {"name": "Hunter", "level": 1, "xp": 0},
        {"name": "Construction", "level": 26, "xp": 8915},
    ]

    # The correct total should be 952 (excluding Overall)
    # The old buggy calculation would be 952 (Overall) + 952 (individual skills) = 1904
    expected_total = 952
    actual_total = _total_level(skills)

    assert actual_total == expected_total, f"Expected {expected_total}, got {actual_total}"


def test_total_level_handles_missing_overall():
    """Test that _total_level works correctly when no 'Overall' skill is present."""
    skills = [
        {"name": "Attack", "level": 50, "xp": 100000},
        {"name": "Defence", "level": 45, "xp": 80000},
        {"name": "Strength", "level": 40, "xp": 60000},
    ]

    expected_total = 50 + 45 + 40
    actual_total = _total_level(skills)

    assert actual_total == expected_total


def test_total_level_handles_missing_levels():
    """Test that _total_level handles missing or None levels gracefully."""
    skills = [
        {"name": "Overall", "level": 100, "xp": 1000000},
        {"name": "Attack", "level": 50, "xp": 100000},
        {"name": "Defence", "level": None, "xp": 80000},  # None level
        {"name": "Strength", "xp": 60000},  # Missing level
        {"name": "Magic", "level": 40, "xp": 50000},
    ]

    expected_total = 50 + 40  # None and missing levels should be treated as 0
    actual_total = _total_level(skills)

    assert actual_total == expected_total


def test_total_level_empty_skills():
    """Test that _total_level returns 0 for empty skills list."""
    assert _total_level([]) == 0


def test_total_level_only_overall():
    """Test that _total_level returns 0 when only Overall skill is present."""
    skills = [
        {"name": "Overall", "level": 500, "xp": 1000000},
    ]

    assert _total_level(skills) == 0


def test_report_content_uses_correct_total_level():
    """Test that the generated report content uses the correct total level."""
    snapshot = {
        "metadata": {
            "player": "TestPlayer",
            "resolved_mode": "main",
            "fetched_at": "2025-10-20T00:00:00+00:00",
            "snapshot_id": "test123",
        },
        "data": {
            "skills": [
                {"name": "Overall", "level": 100, "xp": 1000000},
                {"name": "Attack", "level": 50, "xp": 100000},
                {"name": "Defence", "level": 30, "xp": 50000},
                {"name": "Strength", "level": 20, "xp": 30000},
            ],
            "activities": [],
        },
        "delta": None,
    }

    content = build_report_content(snapshot)

    # Total level should be 50 + 30 + 20 = 100 (excluding Overall)
    # Not 100 (Overall) + 100 = 200
    assert "- **Total Level:** 100" in content
    assert "- **Total XP:** 1,180,000" in content  # Should still include Overall XP
    assert "Attack | 50" in content
    assert "Overall | 100" in content  # Overall should still be displayed in skills table
