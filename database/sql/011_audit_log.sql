-- Migration 011: Audit Log Table
-- Purpose: Track all authentication and security events for audit trail
-- Phase 3, Task 3.1: Audit Logging Infrastructure

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,  -- login_success, login_failure, logout, register, token_create, token_revoke, password_change, account_locked, admin_*
    user_id INTEGER,
    email TEXT,
    ip_address TEXT,
    user_agent TEXT,
    metadata TEXT DEFAULT '{}',  -- JSON string for additional event data
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- Indexes for efficient audit log queries
CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_event ON audit_log(event_type);
CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_log(created_at);
CREATE INDEX IF NOT EXISTS idx_audit_ip ON audit_log(ip_address);
