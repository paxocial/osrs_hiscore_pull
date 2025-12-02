"""Account linking helpers for the web UI."""

from __future__ import annotations

from typing import Optional
from pathlib import Path

from core.constants import GAME_MODES
from core.mode_cache import ModeCache
from database.connection import DatabaseConnection


class AccountService:
    def __init__(self, db: Optional[DatabaseConnection] = None, mode_cache_path: Path = Path("config/mode_cache.json")) -> None:
        self.db = db or DatabaseConnection()
        self.mode_cache = ModeCache(mode_cache_path)

    def ensure_account(self, name: str, display_name: Optional[str], mode: str = "main", update_default_mode: bool = True) -> int:
        """Find or create an account record and return its id. Optionally update default_mode."""
        normalized = name.strip()
        with self.db.get_connection() as conn:
            existing = conn.execute(
                "SELECT id FROM accounts WHERE name = ?",
                (normalized,),
            ).fetchone()
            if existing:
                if update_default_mode and mode in GAME_MODES:
                    conn.execute(
                        "UPDATE accounts SET default_mode = ? WHERE id = ?",
                        (mode, existing["id"]),
                    )
                return existing["id"]

            cursor = conn.execute(
                """
                INSERT INTO accounts (name, display_name, default_mode)
                VALUES (?, ?, ?)
                """,
                (normalized, display_name, mode),
            )
            return cursor.lastrowid

    def link_user_account(self, user_id: int, account_id: int, role: str = "owner", make_default: bool = False) -> bool:
        """Attach an account to a user; returns True if linked (idempotent)."""
        with self.db.get_connection() as conn:
            existing = conn.execute(
                "SELECT id FROM user_accounts WHERE user_id = ? AND account_id = ?",
                (user_id, account_id),
            ).fetchone()
            if existing:
                return True

            conn.execute(
                """
                INSERT INTO user_accounts (user_id, account_id, role, is_default)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, account_id, role, 1 if make_default else 0),
            )

            # If marking default, unset others
            if make_default:
                conn.execute(
                    """
                    UPDATE user_accounts
                    SET is_default = 0
                    WHERE user_id = ? AND account_id != ?
                    """,
                    (user_id, account_id),
                )
            return True

    def list_user_accounts(self, user_id: int) -> list[dict]:
        with self.db.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT ua.id as link_id, ua.role, ua.is_default, a.*
                FROM user_accounts ua
                JOIN accounts a ON ua.account_id = a.id
                WHERE ua.user_id = ?
                ORDER BY ua.is_default DESC, a.name ASC
                """,
                (user_id,),
            ).fetchall()
            out = []
            for r in rows:
                row_dict = dict(r)
                row_dict["cached_mode"] = self.mode_cache.get(row_dict["name"])
                out.append(row_dict)
            return out

    def set_default(self, user_id: int, account_id: int) -> None:
        with self.db.get_connection() as conn:
            conn.execute(
                "UPDATE user_accounts SET is_default = 0 WHERE user_id = ?",
                (user_id,),
            )
            conn.execute(
                "UPDATE user_accounts SET is_default = 1 WHERE user_id = ? AND account_id = ?",
                (user_id, account_id),
            )

    def unlink_user_account(self, user_id: int, account_id: int) -> None:
        with self.db.get_connection() as conn:
            conn.execute(
                "DELETE FROM user_accounts WHERE user_id = ? AND account_id = ?",
                (user_id, account_id),
            )
