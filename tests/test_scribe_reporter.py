from support.scribe_reporter import report_snapshot


def test_report_snapshot_writes_log(temp_config):
    config_path, log_path = temp_config

    report_snapshot(
        player="Tester",
        mode="main",
        success=True,
        message="Snapshot stored",
        snapshot_path=None,
        latency_ms=123.45,
        expected_mode="main",
        resolved_mode="main",
        snapshot_id="abc-123",
        delta_summary="ΔXP +10",
        config_path=config_path,
    )

    content = log_path.read_text(encoding="utf-8")
    assert "SnapshotAgent" in content
    assert "Tester" in content
    assert "ΔXP +10" in content
    assert "latency_ms=123.45" in content
