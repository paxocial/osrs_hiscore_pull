"""Auth helpers for the web UI."""

from __future__ import annotations

import bcrypt
import secrets
import hashlib
from typing import Optional
from datetime import datetime, timedelta
from fastapi import HTTPException

from config.settings import AppConfig

from database.connection import DatabaseConnection
from web.services.password_validator import validate_password_strength
from web.services.email_sender import send_verification_email
from web.services.audit import log_auth_event


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

    def register(self, email: str, password: str, base_url: str = "http://localhost:8001") -> Optional[int]:
        """Create a user; returns user_id or None if exists."""
        # Validate password strength before registration
        is_valid, error_msg = validate_password_strength(password)
        if not is_valid:
            raise ValueError(error_msg)

        config = AppConfig()

        with self.db.get_connection() as conn:
            existing = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
            if existing:
                return None
            password_hash = _hash_password(password)

            # Generate email verification token if feature enabled
            verification_token = None
            verification_expires = None
            if config.features.enable_email_verification:
                verification_token = secrets.token_urlsafe(32)
                expiry_hours = config.account.verification_token_expiry_hours
                verification_expires = (datetime.utcnow() + timedelta(hours=expiry_hours)).isoformat()

            cursor = conn.execute(
                "INSERT INTO users (email, password_hash, email_verified, verification_token, verification_expires) VALUES (?, ?, ?, ?, ?)",
                (email, password_hash, 0, verification_token, verification_expires),
            )
            user_id = cursor.lastrowid

            # Send verification email if feature enabled
            if config.features.enable_email_verification and verification_token:
                send_verification_email(email, verification_token, base_url)

            return user_id

    def authenticate(self, email: str, password: str, request = None) -> Optional[dict]:
        """Verify credentials; returns user dict or None."""
        config = AppConfig()
        lockout_threshold = config.account.lockout_threshold
        lockout_duration_minutes = config.account.lockout_duration_minutes

        with self.db.get_connection() as conn:
            # Select specific columns, including password_hash for verification
            # Note: password_hash should never be returned to client, only used for verification
            row = conn.execute(
                """
                SELECT id, email, password_hash, is_active, is_admin, failed_login_attempts,
                       locked_until, last_failed_login, email_verified, created_at
                FROM users
                WHERE email = ? AND is_active = 1
                """,
                (email,),
            ).fetchone()
            if not row:
                # Log failed login attempt (user not found)
                if config.features.enable_audit_logging:
                    log_auth_event("login_failure", request=request, email=email,
                                 metadata={"reason": "user_not_found"})
                return None

            user = dict(row)

            # Check if account is locked
            if user.get("locked_until"):
                locked_until = datetime.fromisoformat(user["locked_until"])
                if datetime.utcnow() < locked_until:
                    # Log locked account login attempt
                    if config.features.enable_audit_logging:
                        log_auth_event("login_failure", request=request, user_id=user["id"],
                                     email=email, metadata={"reason": "account_locked",
                                     "locked_until": user["locked_until"]})
                    raise HTTPException(
                        status_code=429,
                        detail=f"Account locked until {locked_until.strftime('%Y-%m-%d %H:%M UTC')}. Too many failed login attempts."
                    )
                # Lockout expired, clear it
                conn.execute(
                    "UPDATE users SET locked_until = NULL, failed_login_attempts = 0 WHERE id = ?",
                    (user["id"],)
                )
                conn.commit()

            # Verify password
            if not _verify_password(password, user["password_hash"]):
                # Increment failed attempts
                attempts = (user.get("failed_login_attempts") or 0) + 1
                locked_until = None

                # Lock account if threshold reached
                if attempts >= lockout_threshold:
                    locked_until = (datetime.utcnow() + timedelta(minutes=lockout_duration_minutes)).isoformat()

                    # Log account lockout
                    if config.features.enable_audit_logging:
                        log_auth_event("account_locked", request=request, user_id=user["id"],
                                     email=email, metadata={"attempts": attempts,
                                     "locked_until": locked_until})

                conn.execute(
                    "UPDATE users SET failed_login_attempts = ?, locked_until = ?, last_failed_login = CURRENT_TIMESTAMP WHERE id = ?",
                    (attempts, locked_until, user["id"])
                )
                conn.commit()

                # Log failed login attempt (invalid password)
                if config.features.enable_audit_logging:
                    log_auth_event("login_failure", request=request, user_id=user["id"],
                                 email=email, metadata={"reason": "invalid_password",
                                 "attempts": attempts})
                return None

            # Successful login - reset failed attempts
            conn.execute(
                "UPDATE users SET failed_login_attempts = 0, locked_until = NULL WHERE id = ?",
                (user["id"],)
            )
            conn.commit()

            # Log successful login
            if config.features.enable_audit_logging:
                log_auth_event("login_success", request=request, user_id=user["id"],
                             email=email)

            # Remove password_hash before returning user dict (sensitive data protection)
            user.pop("password_hash", None)
            return user

    def get_user(self, user_id: int) -> Optional[dict]:
        with self.db.get_connection() as conn:
            # Explicitly exclude password_hash and other sensitive fields
            row = conn.execute(
                """
                SELECT id, email, is_active, is_admin, email_verified, created_at
                FROM users
                WHERE id = ? AND is_active = 1
                """,
                (user_id,)
            ).fetchone()
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
