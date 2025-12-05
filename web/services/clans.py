"""Clan management helpers."""

from __future__ import annotations

from typing import Optional, List
from pathlib import Path

from database.connection import DatabaseConnection
from core.mode_cache import ModeCache
from core.constants import GAME_MODES
from web.services.detect_mode import detect_mode


class ClanService:
    def __init__(self, db: Optional[DatabaseConnection] = None, mode_cache_path: Path = Path("config/mode_cache.json")) -> None:
        self.db = db or DatabaseConnection()
        self.mode_cache = ModeCache(mode_cache_path)

    def create_clan(self, owner_user_id: int, name: str, slug: str, metadata: Optional[str] = None) -> int:
        with self.db.get_connection() as conn:
            existing = conn.execute("SELECT id FROM clans WHERE slug = ?", (slug,)).fetchone()
            if existing:
                return existing["id"]
            cursor = conn.execute(
                "INSERT INTO clans (name, slug, owner_user_id, metadata) VALUES (?, ?, ?, ?)",
                (name.strip(), slug.strip(), owner_user_id, metadata or "{}"),
            )
            return cursor.lastrowid

    def list_clans_for_user(self, user_id: int) -> List[dict]:
        with self.db.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT c.*, COUNT(cm.id) as member_count
                FROM clans c
                LEFT JOIN clan_members cm ON cm.clan_id = c.id
                WHERE c.owner_user_id = ?
                GROUP BY c.id
                ORDER BY c.created_at DESC
                """,
                (user_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def add_member(self, clan_id: int, account_name: str, requested_mode: str = "auto") -> None:
        account_name = account_name.strip()
        with self.db.get_connection() as conn:
            # Ensure account exists; if exists and mode is auto, re-detect and update.
            acct = conn.execute("SELECT id, default_mode FROM accounts WHERE name = ?", (account_name,)).fetchone()
            if acct:
                account_id = acct["id"]
                final_mode = acct["default_mode"] or "main"
                if requested_mode in ("auto", "auto-detect"):
                    detection = detect_mode(account_name, requested_mode="auto")
                    if detection.get("status") == "found":
                        final_mode = detection["mode"]
                        conn.execute("UPDATE accounts SET default_mode = ? WHERE id = ?", (final_mode, account_id))
            else:
                final_mode = requested_mode
                if requested_mode in ("auto", "auto-detect"):
                    detection = detect_mode(account_name, requested_mode="auto")
                    if detection.get("status") == "found":
                        final_mode = detection["mode"]
                    else:
                        final_mode = "main"
                elif requested_mode not in GAME_MODES:
                    final_mode = "main"

                cursor = conn.execute(
                    "INSERT INTO accounts (name, default_mode) VALUES (?, ?)",
                    (account_name, final_mode),
                )
                account_id = cursor.lastrowid

            # Add member if not present
            existing = conn.execute(
                "SELECT id FROM clan_members WHERE clan_id = ? AND account_id = ?",
                (clan_id, account_id),
            ).fetchone()
            if existing:
                return

            conn.execute(
                "INSERT INTO clan_members (clan_id, account_id, rank) VALUES (?, ?, ?)",
                (clan_id, account_id, "member"),
            )

    def remove_member(self, clan_id: int, account_id: int) -> None:
        with self.db.get_connection() as conn:
            conn.execute("DELETE FROM clan_members WHERE clan_id = ? AND account_id = ?", (clan_id, account_id))

    def list_members(self, clan_id: int) -> List[dict]:
        with self.db.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT cm.*, a.name, a.default_mode
                FROM clan_members cm
                JOIN accounts a ON cm.account_id = a.id
                WHERE cm.clan_id = ?
                ORDER BY a.name ASC
                """,
                (clan_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def list_members_paginated(self, clan_id: int, *, offset: int = 0, limit: int = 20) -> dict:
        with self.db.get_connection() as conn:
            total_row = conn.execute(
                "SELECT COUNT(*) as c FROM clan_members WHERE clan_id = ?",
                (clan_id,),
            ).fetchone()
            total = total_row["c"] if total_row else 0
            rows = conn.execute(
                """
                SELECT cm.*, a.name, a.default_mode
                FROM clan_members cm
                JOIN accounts a ON cm.account_id = a.id
                WHERE cm.clan_id = ?
                ORDER BY a.name ASC
                LIMIT ? OFFSET ?
                """,
                (clan_id, limit, offset),
            ).fetchall()
            return {"total": total, "rows": [dict(r) for r in rows], "offset": offset, "limit": limit}

    def get_clan_by_slug(self, slug: str) -> Optional[dict]:
        with self.db.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM clans WHERE slug = ?",
                (slug,),
            ).fetchone()
            return dict(row) if row else None

    def get_clan_by_id(self, clan_id: int) -> Optional[dict]:
        with self.db.get_connection() as conn:
            row = conn.execute("SELECT * FROM clans WHERE id = ?", (clan_id,)).fetchone()
            return dict(row) if row else None
