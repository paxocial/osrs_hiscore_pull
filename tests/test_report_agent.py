from pathlib import Path

from agents.report_agent import ReportAgent


def test_report_agent_build_from_payload(tmp_path: Path):
    reports_dir = tmp_path / "reports"
    agent = ReportAgent(reports_dir)

    payload = {
        "metadata": {
            "player": "Tester",
            "resolved_mode": "main",
            "fetched_at": "2025-10-20T00:00:00+00:00",
            "snapshot_id": "demo",
        },
        "data": {
            "skills": [
                {"name": "Attack", "level": 50, "xp": 100000},
            ],
            "activities": [],
        },
        "delta": None,
    }

    snapshot_file = tmp_path / "snap.json"
    snapshot_file.write_text("{}", encoding="utf-8")

    result = agent.build_from_payload(payload=payload, report_source=snapshot_file, delta_summary="No changes")

    assert result.success
    assert result.report_path is not None
    content = result.report_path.read_text(encoding="utf-8")
    assert "Tester" in content
    assert "Total XP" in content
