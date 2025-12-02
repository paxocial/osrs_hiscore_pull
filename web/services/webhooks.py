"""Webhook configuration service."""

from __future__ import annotations

import json
from typing import List, Dict, Optional

import httpx

from database.connection import DatabaseConnection


class WebhookService:
    def __init__(self, db: Optional[DatabaseConnection] = None) -> None:
        self.db = db or DatabaseConnection(reuse_connection=False, check_same_thread=False)

    def upsert_webhook(
        self,
        owner_user_id: int,
        target_type: str,
        target_id: Optional[int],
        url: str,
        events: str,
        provider: str = "custom",
        secret: Optional[str] = None,
        active: bool = True,
    ) -> int:
        with self.db.get_connection() as conn:
            existing = conn.execute(
                """
                SELECT id FROM webhooks
                WHERE owner_user_id = ? AND target_type = ? AND IFNULL(target_id, -1) = IFNULL(?, -1)
                """,
                (owner_user_id, target_type, target_id),
            ).fetchone()
            if existing:
                conn.execute(
                    """
                    UPDATE webhooks
                    SET url = ?, events = ?, provider = ?, secret = ?, active = ?
                    WHERE id = ?
                    """,
                    (url, events, provider, secret, 1 if active else 0, existing["id"]),
                )
                return existing["id"]
            cursor = conn.execute(
                """
                INSERT INTO webhooks (owner_user_id, target_type, target_id, provider, url, secret, events, active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (owner_user_id, target_type, target_id, provider, url, secret, events, 1 if active else 0),
            )
            return cursor.lastrowid

    def list_webhooks(self, owner_user_id: int, target_type: Optional[str] = None) -> List[Dict]:
        query = "SELECT * FROM webhooks WHERE owner_user_id = ?"
        params = [owner_user_id]
        if target_type:
            query += " AND target_type = ?"
            params.append(target_type)
        with self.db.get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    def dispatch(self, owner_user_id: int, target_type: Optional[str], target_id: Optional[int], event: str, payload: Dict) -> None:
        hooks = self.list_webhooks(owner_user_id)
        for hook in hooks:
            if target_type and hook.get("target_type") != target_type:
                continue
            if target_type == "clan" and target_id and hook.get("target_id") not in (target_id, None):
                continue
            events = (hook.get("events") or "").split(",")
            if event not in events:
                continue
            url = hook.get("url")
            if not url:
                continue
            try:
                httpx.post(url, json=payload, timeout=5.0)
            except Exception:
                continue
