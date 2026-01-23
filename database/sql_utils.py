"""SQL utility functions for safe query construction."""


def escape_like_pattern(pattern: str) -> str:
    """
    Escape special characters in LIKE pattern to prevent SQL injection.

    SQL LIKE patterns use % (match any characters) and _ (match single character)
    as wildcards. User input containing these characters can cause unintended
    matching behavior or be used for SQL injection attacks.

    This function escapes those special characters so they're treated literally.

    Args:
        pattern: User input to be used in LIKE clause

    Returns:
        Escaped pattern safe for LIKE clause

    Example:
        >>> escape_like_pattern("test%_input")
        "test\\%\\_input"
        >>> f"%{escape_like_pattern(user_input)}%"  # Safe wrapping with wildcards
    """
    if not pattern:
        return pattern

    # Escape backslash first (escape character itself)
    pattern = pattern.replace("\\", "\\\\")
    # Escape percent (matches zero or more characters)
    pattern = pattern.replace("%", "\\%")
    # Escape underscore (matches exactly one character)
    pattern = pattern.replace("_", "\\_")

    return pattern
