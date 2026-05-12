from core.processing import (
    compute_snapshot_delta,
    normalize_snapshot_data,
    summarize_delta,
)


def test_normalize_snapshot_data_replaces_negative_values():
    raw = {
        "skills": [
            {"name": "Attack", "rank": -1, "level": 50, "xp": 12345},
            {"name": "Magic", "rank": 1000, "level": -1, "xp": -1},
        ],
        "activities": [
            {"name": "Tempoross", "rank": -1, "score": -1},
            {"name": "Rifts closed", "rank": 100, "score": 10},
        ],
    }

    normalized = normalize_snapshot_data(raw)

    assert normalized["skills"][0]["rank"] is None
    assert normalized["skills"][1]["level"] is None
    assert normalized["skills"][1]["xp"] is None
    assert normalized["activities"][0]["score"] is None
    # ensure original is untouched
    assert raw["skills"][0]["rank"] == -1


def test_compute_snapshot_delta_and_summary():
    previous = {
        "skills": [
            {"name": "Magic", "level": 60, "xp": 300000},
            {"name": "Fishing", "level": 63, "xp": 374447},
        ],
        "activities": [
            {"name": "Tempoross", "score": 80},
        ],
    }

    current = {
        "skills": [
            {"name": "Magic", "level": 61, "xp": 320000},
            {"name": "Fishing", "level": 63, "xp": 380000},
        ],
        "activities": [
            {"name": "Tempoross", "score": 85},
        ],
    }

    delta = compute_snapshot_delta(previous, current)

    assert delta["total_xp_delta"] == (320000 + 380000) - (300000 + 374447)
    assert any(skill["name"] == "Magic" for skill in delta["skill_deltas"])
    assert delta["activity_deltas"][0]["score_delta"] == 5

    summary = summarize_delta(delta)
    assert "ΔXP" in summary
    assert "Magic" in summary
    assert "Tempoross" in summary


def test_compute_snapshot_delta_prefers_overall_and_summary_excludes_overall():
    previous = {
        "skills": [
            {"name": "Overall", "level": 783, "xp": 9_419_643},
            {"name": "Agility", "level": 56, "xp": 184_040},
            {"name": "Mining", "level": 9, "xp": 1_154},
            {"name": "Magic", "level": 1, "xp": 0},
        ],
        "activities": [],
    }
    current = {
        "skills": [
            {"name": "Overall", "level": 952, "xp": 14_096_057},
            {"name": "Agility", "level": 60, "xp": 276_656},
            {"name": "Mining", "level": 76, "xp": 1_439_935},
            {"name": "Magic", "level": 1, "xp": 3_145_017},
        ],
        "activities": [],
    }

    delta = compute_snapshot_delta(previous, current)

    assert delta["total_xp_delta"] == 4_676_414
    assert delta["total_xp_delta"] != 9_352_828

    summary = summarize_delta(delta)
    assert "ΔXP 4.68M" in summary
    assert "9.35M" not in summary
    assert "Overall" not in summary
    assert "Mining(+67)" in summary
    assert "Agility(+4)" in summary
