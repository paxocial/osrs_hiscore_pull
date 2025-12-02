"""Auth helpers for the web UI."""

from __future__ import annotations

import bcrypt
import secrets
import hashlib
from typing import Optional

from database.connection import DatabaseConnection


def _hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def _verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class AuthService:
    """User auth, token issuance, and retrieval."""

    def __init__(self, db: Optional[DatabaseConnection] = None) -> None:
        self.db = db or DatabaseConnection()

    def register(self, email: str, password: str) -> Optional[int]:
        """Create a user; returns user_id or None if exists."""
        with self.db.get_connection() as conn:
            existing = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
            if existing:
                return None
            password_hash = _hash_password(password)
            cursor = conn.execute(
                "INSERT INTO users (email, password_hash) VALUES (?, ?)",
                (email, password_hash),
            )
            return cursor.lastrowid

    def authenticate(self, email: str, password: str) -> Optional[dict]:
        """Verify credentials; returns user dict or None."""
        with self.db.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE email = ? AND is_active = 1",
                (email,),
            ).fetchone()
            if not row:
                return None
            if not _verify_password(password, row["password_hash"]):
                return None
            return dict(row)

    def get_user(self, user_id: int) -> Optional[dict]:
        with self.db.get_connection() as conn:
            row = conn.execute("SELECT * FROM users WHERE id = ? AND is_active = 1", (user_id,)).fetchone()
            return dict(row) if row else None

    # ---- API tokens ----
    def issue_token(self, user_id: int, scopes: str = "read", label: str | None = None) -> tuple[str, int]:
        """Generate a token string and store hashed; returns (plain_token, token_id)."""
        plain = secrets.token_urlsafe(32)
        token_hash = _hash_token(plain)
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO api_tokens (user_id, token_hash, scopes, label)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, token_hash, scopes, label),
            )
            return plain, cursor.lastrowid

    def revoke_token(self, user_id: int, token_id: int) -> bool:
        with self.db.get_connection() as conn:
            result = conn.execute(
                "UPDATE api_tokens SET revoked_at = CURRENT_TIMESTAMP WHERE id = ? AND user_id = ? AND revoked_at IS NULL",
                (token_id, user_id),
            )
            return result.rowcount > 0

    def list_tokens(self, user_id: int) -> list[dict]:
        with self.db.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, scopes, label, created_at, last_used_at, revoked_at
                FROM api_tokens
                WHERE user_id = ?
                ORDER BY created_at DESC
                """,
                (user_id,),
            ).fetchall()
            return [dict(r) for r in rows]
