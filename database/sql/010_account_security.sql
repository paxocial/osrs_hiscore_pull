-- Migration 010: Account Security Enhancements
-- Purpose: Add columns for account lockout and email verification
-- Phase: Phase 2 (P1 Authentication Hardening)

-- Account lockout columns
ALTER TABLE users ADD COLUMN failed_login_attempts INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN locked_until DATETIME;
ALTER TABLE users ADD COLUMN last_failed_login DATETIME;

-- Email verification columns
ALTER TABLE users ADD COLUMN email_verified INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN verification_token TEXT;
ALTER TABLE users ADD COLUMN verification_expires DATETIME;

-- Add index for lockout queries
CREATE INDEX IF NOT EXISTS idx_users_locked_until ON users(locked_until);
CREATE INDEX IF NOT EXISTS idx_users_email_verified ON users(email_verified);
