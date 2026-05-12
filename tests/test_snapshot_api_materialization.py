from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from agents import report_agent as report_agent_module
from agents.osrs_snapshot_agent import SnapshotResult
from api.endpoints import snapshots as snapshots_module
from database.connection import DatabaseConnection


class _FakeSnapshotAgent:
    def __init__(
        self,
        output_dir: Path,
        *,
        mode_cache_path: Path | None = None,
        config_path: Path | None = None,
    ) -> None:
        self.output_dir = output_dir

    def run(self, accounts):
        account = list(accounts)[0]
        player = account["name"]
        snapshot_id = "materialized-snapshot-0001"
        snapshot_path = self.output_dir / player.replace(" ", "_") / "20260512_060000.json"
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "metadata": {
                "schema_version": "1.1",
                "snapshot_id": snapshot_id,
                "player": player,
                "requested_mode": account["mode"],
                "resolved_mode": "main",
                "fetched_at": "2026-05-12T06:00:00+00:00",
                "fetched_at_unix": 1778565600,
                "endpoint": "https://example.test/hiscore",
                "latency_ms": 12.5,
                "agent_version": "test",
            },
            "data": {
                "skills": [
                    {"id": 0, "name": "Overall", "level": 1000, "xp": 123456, "rank": 42},
                    {"id": 1, "name": "Attack", "level": 50, "xp": 101333, "rank": 100},
                ],
                "activities": [],
            },
            "delta": None,
        }
        snapshot_path.write_text(json.dumps(payload), encoding="utf-8")
        return [
            SnapshotResult(
                player=player,
                mode="main",
                snapshot_path=snapshot_path,
                success=True,
                message="Initial snapshot.",
                metadata=payload["metadata"],
                payload=payload,
                delta=None,
                delta_summary="Initial snapshot.",
            )
        ]


class _FailingIngestService:
    def ingest_result(self, result: SnapshotResult):
        raise RuntimeError("ingest failed")


class _FailingReportAgent:
    def __init__(self, *args, **kwargs) -> None:
        pass

    def build_from_payload(self, **kwargs):
        raise RuntimeError("report write failed")


def test_run_endpoint_materializes_snapshot_latest_and_report(monkeypatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    DatabaseConnection(reuse_connection=False, check_same_thread=False).initialize_database()
    monkeypatch.setattr(snapshots_module, "SnapshotAgent", _FakeSnapshotAgent)
    monkeypatch.setattr(report_agent_module, "report_snapshot", lambda **kwargs: None)

    result = asyncio.run(
        snapshots_module._run_snapshots(
            snapshots_module.SnapshotRunRequest(player="History Hero", mode="auto")
        )
    )

    assert result[0]["success"] is True

    db = DatabaseConnection(reuse_connection=False, check_same_thread=False)
    with db.get_connection() as conn:
        latest = asyncio.run(snapshots_module.get_latest_snapshots(25, None, None, conn))

    assert [snapshot.snapshot_id for snapshot in latest] == ["materialized-snapshot-0001"]
    assert latest[0].account_name == "History Hero"
    assert latest[0].requested_mode == "auto"

    report_response = asyncio.run(
        snapshots_module.get_snapshot_report(
            {
                "account_name": "History Hero",
                "snapshot_id": "materialized-snapshot-0001",
            }
        )
    )

    assert "History Hero" in report_response.body.decode("utf-8")


def test_run_endpoint_surfaces_ingest_failure_instead_of_false_success(monkeypatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    DatabaseConnection(reuse_connection=False, check_same_thread=False).initialize_database()
    monkeypatch.setattr(snapshots_module, "SnapshotAgent", _FakeSnapshotAgent)
    monkeypatch.setattr(snapshots_module, "SnapshotIngestService", _FailingIngestService)

    with pytest.raises(RuntimeError, match="ingest failed"):
        asyncio.run(
            snapshots_module._run_snapshots(
                snapshots_module.SnapshotRunRequest(player="History Hero", mode="auto")
            )
        )


def test_run_endpoint_surfaces_report_failure_instead_of_false_success(monkeypatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    DatabaseConnection(reuse_connection=False, check_same_thread=False).initialize_database()
    monkeypatch.setattr(snapshots_module, "SnapshotAgent", _FakeSnapshotAgent)
    monkeypatch.setattr(snapshots_module, "ReportAgent", _FailingReportAgent)

    with pytest.raises(RuntimeError, match="report write failed"):
        asyncio.run(
            snapshots_module._run_snapshots(
                snapshots_module.SnapshotRunRequest(player="History Hero", mode="auto")
            )
        )
