-- Migration 009: Rate Limiting Infrastructure
-- Purpose: Add rate limiting table for IP-based request throttling
-- Phase: Phase 2 (P1 Authentication Hardening)

CREATE TABLE IF NOT EXISTS rate_limit_store (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ip_address TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    window_start DATETIME NOT NULL,
    request_count INTEGER DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(ip_address, endpoint, window_start)
);

CREATE INDEX idx_rate_limit_lookup ON rate_limit_store(ip_address, endpoint, window_start);

-- Optional: Create cleanup trigger to remove old rate limit records (>24 hours)
CREATE TRIGGER IF NOT EXISTS cleanup_old_rate_limits
AFTER INSERT ON rate_limit_store
BEGIN
    DELETE FROM rate_limit_store
    WHERE created_at < datetime('now', '-24 hours');
END;
