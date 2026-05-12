from __future__ import annotations

from pathlib import Path

from agents.osrs_snapshot_agent import SnapshotAgent
from core.hiscore_client import HiscoreResponse


class _FakeHiscoreClient:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return None

    def fetch(self, player: str, mode: str):
        return HiscoreResponse(
            data={"skills": [], "activities": []},
            status_code=200,
            url=f"https://example.test/{mode}/{player}",
        )


def test_snapshot_run_succeeds_when_clipboard_backend_missing(monkeypatch, tmp_path: Path):
    # Simulate pyperclip provider crash (e.g., missing clip.exe on server runtime).
    class _ClipboardProvider:
        class PyperclipException(Exception):
            pass

        @staticmethod
        def copy(text: str) -> None:
            raise FileNotFoundError("clip.exe")

    monkeypatch.setattr("core.clipboard.pyperclip", _ClipboardProvider)
    monkeypatch.setattr("agents.osrs_snapshot_agent.HiscoreClient", _FakeHiscoreClient)
    monkeypatch.setattr("agents.osrs_snapshot_agent.report_snapshot", lambda **kwargs: None)

    output_dir = tmp_path / "snapshots"
    mode_cache_path = tmp_path / "mode_cache.json"
    agent = SnapshotAgent(output_dir=output_dir, mode_cache_path=mode_cache_path)

    results = agent.run([{"name": "Lynx Titan", "mode": "main"}])

    assert len(results) == 1
    assert results[0].success is True
    assert results[0].snapshot_path is not None
    assert results[0].snapshot_path.exists()
