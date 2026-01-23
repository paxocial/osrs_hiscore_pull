"""Configuration management for OSRS Hiscore Dashboard.

Centralized application configuration with environment-based validation and type safety.
All security settings configurable via environment variables with sensible defaults for development.
"""

from dataclasses import dataclass
from typing import List
import os


@dataclass
class SecuritySettings:
    """Security-related configuration."""
    secret_key: str
    session_max_age: int = 14400  # 4 hours
    https_only: bool = False
    same_site: str = "strict"
    csrf_token_bytes: int = 32


@dataclass
class RateLimitSettings:
    """Rate limiting configuration."""
    login_limit: str = "5/minute"
    register_limit: str = "3/hour"
    password_reset_limit: str = "3/hour"
    api_token_limit: str = "10/hour"


@dataclass
class PasswordSettings:
    """Password validation configuration."""
    min_length: int = 12
    require_uppercase: bool = True
    require_lowercase: bool = True
    require_digit: bool = True
    require_special: bool = True
    common_password_check: bool = False


@dataclass
class AccountSettings:
    """Account security configuration."""
    lockout_threshold: int = 5
    lockout_duration_minutes: int = 15
    email_verification_required: bool = True
    verification_token_expiry_hours: int = 24


@dataclass
class SMTPSettings:
    """Email/SMTP configuration."""
    host: str = "localhost"
    port: int = 587
    username: str = ""
    password: str = ""
    from_address: str = "noreply@localhost"
    use_tls: bool = True


@dataclass
class FeatureFlags:
    """Feature toggle configuration."""
    enable_audit_logging: bool = True
    enable_rate_limiting: bool = True
    enable_email_verification: bool = True
    enable_admin_ui: bool = True


class AppConfig:
    """Central application configuration with validation."""

    def __init__(self):
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.is_production = self.environment == "production"
        self.is_development = self.environment == "development"

        # Initialize configuration sections
        self.security = self._load_security_config()
        self.rate_limits = self._load_rate_limit_config()
        self.password = self._load_password_config()
        self.account = self._load_account_config()
        self.smtp = self._load_smtp_config()
        self.features = self._load_feature_config()
        self.cors_origins = self._get_cors_origins()

    def _load_security_config(self) -> SecuritySettings:
        secret_key = self._get_required("WEB_SECRET_KEY")
        return SecuritySettings(
            secret_key=secret_key,
            session_max_age=int(os.getenv("SESSION_MAX_AGE", "14400")),
            https_only=self.is_production,
            same_site=os.getenv("SESSION_SAME_SITE", "strict"),
        )

    def _load_rate_limit_config(self) -> RateLimitSettings:
        return RateLimitSettings(
            login_limit=os.getenv("RATE_LIMIT_LOGIN", "5/minute"),
            register_limit=os.getenv("RATE_LIMIT_REGISTER", "3/hour"),
            password_reset_limit=os.getenv("RATE_LIMIT_PASSWORD_RESET", "3/hour"),
            api_token_limit=os.getenv("RATE_LIMIT_API_TOKEN", "10/hour"),
        )

    def _load_password_config(self) -> PasswordSettings:
        return PasswordSettings(
            min_length=int(os.getenv("PASSWORD_MIN_LENGTH", "12")),
            common_password_check=os.getenv("PASSWORD_CHECK_COMMON", "false").lower() == "true",
        )

    def _load_account_config(self) -> AccountSettings:
        return AccountSettings(
            lockout_threshold=int(os.getenv("ACCOUNT_LOCKOUT_THRESHOLD", "5")),
            lockout_duration_minutes=int(os.getenv("ACCOUNT_LOCKOUT_DURATION", "15")),
            email_verification_required=os.getenv("EMAIL_VERIFICATION_REQUIRED", "true").lower() == "true",
            verification_token_expiry_hours=int(os.getenv("EMAIL_VERIFICATION_EXPIRY", "24")),
        )

    def _load_smtp_config(self) -> SMTPSettings:
        return SMTPSettings(
            host=os.getenv("SMTP_HOST", "localhost"),
            port=int(os.getenv("SMTP_PORT", "587")),
            username=os.getenv("SMTP_USERNAME", ""),
            password=os.getenv("SMTP_PASSWORD", ""),
            from_address=os.getenv("SMTP_FROM", "noreply@localhost"),
            use_tls=os.getenv("SMTP_USE_TLS", "true").lower() == "true",
        )

    def _load_feature_config(self) -> FeatureFlags:
        return FeatureFlags(
            enable_audit_logging=os.getenv("FEATURE_AUDIT_LOGGING", "true").lower() == "true",
            enable_rate_limiting=os.getenv("FEATURE_RATE_LIMITING", "true").lower() == "true",
            enable_email_verification=os.getenv("FEATURE_EMAIL_VERIFICATION", "true").lower() == "true",
            enable_admin_ui=os.getenv("FEATURE_ADMIN_UI", "true").lower() == "true",
        )

    def _get_required(self, key: str) -> str:
        value = os.getenv(key)
        if self.is_production and not value:
            raise RuntimeError(f"{key} must be set in production")
        if self.is_production and key == "WEB_SECRET_KEY" and len(value) < 32:
            raise RuntimeError("WEB_SECRET_KEY must be at least 32 characters")
        return value or self._get_dev_default(key)

    def _get_dev_default(self, key: str) -> str:
        defaults = {
            "WEB_SECRET_KEY": "dev-secret-key-minimum-32-chars-required-for-production-use",
        }
        return defaults.get(key, "")

    def _get_cors_origins(self) -> List[str]:
        origins_str = os.getenv("CORS_ALLOWED_ORIGINS", "")
        if not origins_str:
            return ["http://localhost:8000"] if self.is_development else []
        return [origin.strip() for origin in origins_str.split(",")]
