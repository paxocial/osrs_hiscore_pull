"""Snapshot trigger helpers for web UI (calls API runner)."""

from __future__ import annotations

import json
from typing import Dict, List

import httpx


class SnapshotService:
    def __init__(self, api_base: str = "/api") -> None:
        self.api_base = api_base.rstrip("/")

    def trigger_snapshot(self, player: str, mode: str = "auto") -> Dict:
        url = f"{self.api_base}/snapshots/run"
        payload = {"player": player, "mode": mode}
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(url, json=payload)
            body = resp.json() if resp.content else {}
            return {"status": resp.status_code, "body": body}

    def trigger_bulk(self, accounts: List[Dict[str, str]]) -> Dict:
        url = f"{self.api_base}/snapshots/run"
        payload = {"accounts": accounts}
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(url, json=payload)
            body = resp.json() if resp.content else {}
            return {"status": resp.status_code, "body": body}
