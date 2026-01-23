"""Password strength validation for authentication."""

import re
from typing import Tuple

from config.settings import AppConfig


def validate_password_strength(password: str, config: AppConfig = None) -> Tuple[bool, str]:
    """
    Validate password meets security requirements.

    Args:
        password: The password to validate
        config: AppConfig instance for password policy settings (optional)

    Returns:
        Tuple of (is_valid, error_message)
        - (True, "") if password meets all requirements
        - (False, "error message") if password fails validation
    """
    if config is None:
        config = AppConfig()

    password_settings = config.password

    # Check minimum length
    if len(password) < password_settings.min_length:
        return False, f"Password must be at least {password_settings.min_length} characters"

    # Check uppercase requirement
    if password_settings.require_uppercase and not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"

    # Check lowercase requirement
    if password_settings.require_lowercase and not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"

    # Check digit requirement
    if password_settings.require_digit and not re.search(r"\d", password):
        return False, "Password must contain at least one number"

    # Check special character requirement
    if password_settings.require_special and not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "Password must contain at least one special character (!@#$%^&*(),.?\":{}|<>)"

    # Optional: Check against common passwords (if enabled)
    if password_settings.common_password_check:
        if _is_common_password(password):
            return False, "Password is too common. Please choose a more unique password"

    return True, ""


def _is_common_password(password: str) -> bool:
    """
    Check if password is in common password list.

    This is a stub implementation. In production, this would check against
    a comprehensive list of common passwords (e.g., rockyou.txt top 10000).
    """
    # Common passwords blocklist (minimal implementation)
    common_passwords = {
        "password", "password123", "123456", "12345678", "qwerty",
        "abc123", "monkey", "letmein", "trustno1", "dragon",
        "baseball", "iloveyou", "master", "sunshine", "ashley",
        "bailey", "passw0rd", "shadow", "123123", "654321",
        "superman", "qazwsx", "michael", "football"
    }
    return password.lower() in common_passwords
