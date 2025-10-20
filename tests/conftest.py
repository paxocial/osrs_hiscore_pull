from __future__ import annotations

import json
from pathlib import Path
from typing import Tuple

import pytest


@pytest.fixture()
def temp_config(tmp_path: Path) -> Tuple[Path, Path]:
    log_path = tmp_path / "progress.log"
    config_path = tmp_path / "project.json"
    config = {
        "project_name": "codex-test",
        "progress_log": str(log_path),
        "default_emoji": "ℹ️",
        "default_agent": "TestAgent",
    }
    config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    return config_path, log_path
