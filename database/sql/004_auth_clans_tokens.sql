-- Auth, tokens, clans, contests, jobs, and webhooks
-- Version: 1.3
-- Created: 2025-12-02
-- Description: Adds multi-user auth, API tokens, clans/contests, public profiles, jobs, and webhooks.

PRAGMA foreign_keys = ON;

-- ===================================
-- USERS TABLE
-- ===================================
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    is_active INTEGER DEFAULT 1,
    is_admin INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login_at DATETIME
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active);

-- ===================================
-- USER ↔ ACCOUNT LINKS
-- ===================================
CREATE TABLE IF NOT EXISTS user_accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    account_id INTEGER NOT NULL,
    role TEXT DEFAULT 'owner', -- owner | editor | viewer
    is_default INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE,
    UNIQUE(user_id, account_id)
);

CREATE INDEX IF NOT EXISTS idx_user_accounts_user ON user_accounts(user_id);
CREATE INDEX IF NOT EXISTS idx_user_accounts_account ON user_accounts(account_id);
CREATE INDEX IF NOT EXISTS idx_user_accounts_default ON user_accounts(user_id, is_default);

-- ===================================
-- API TOKENS
-- ===================================
CREATE TABLE IF NOT EXISTS api_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    token_hash TEXT UNIQUE NOT NULL,
    scopes TEXT DEFAULT 'read',
    label TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_used_at DATETIME,
    revoked_at DATETIME,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_api_tokens_user ON api_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_api_tokens_active ON api_tokens(token_hash) WHERE revoked_at IS NULL;

-- ===================================
-- CLANS AND MEMBERS
-- ===================================
CREATE TABLE IF NOT EXISTS clans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    owner_user_id INTEGER NOT NULL,
    metadata TEXT DEFAULT '{}',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (owner_user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(name)
);

CREATE TABLE IF NOT EXISTS clan_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    clan_id INTEGER NOT NULL,
    account_id INTEGER NOT NULL,
    rank TEXT DEFAULT 'member',
    join_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    FOREIGN KEY (clan_id) REFERENCES clans(id) ON DELETE CASCADE,
    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE,
    UNIQUE(clan_id, account_id)
);

CREATE INDEX IF NOT EXISTS idx_clan_members_clan ON clan_members(clan_id);
CREATE INDEX IF NOT EXISTS idx_clan_members_account ON clan_members(account_id);

-- ===================================
-- CONTESTS AND PROGRESS
-- ===================================
CREATE TABLE IF NOT EXISTS contests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    clan_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    metric TEXT NOT NULL, -- xp | level | boss_kc | clues | gotr | ehp | ehb | custom
    start_at DATETIME NOT NULL,
    end_at DATETIME,
    reward TEXT,
    metadata TEXT DEFAULT '{}',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (clan_id) REFERENCES clans(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_contests_clan ON contests(clan_id);
CREATE INDEX IF NOT EXISTS idx_contests_metric ON contests(metric);
CREATE INDEX IF NOT EXISTS idx_contests_time ON contests(start_at, end_at);

CREATE TABLE IF NOT EXISTS contest_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contest_id INTEGER NOT NULL,
    account_id INTEGER NOT NULL,
    start_snapshot_id INTEGER,
    latest_snapshot_id INTEGER,
    delta_xp INTEGER DEFAULT 0,
    delta_level INTEGER DEFAULT 0,
    delta_score INTEGER DEFAULT 0, -- generic metric slot (boss kc, clues, gotr, etc.)
    metric_breakdown TEXT DEFAULT '{}',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (contest_id) REFERENCES contests(id) ON DELETE CASCADE,
    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE,
    FOREIGN KEY (start_snapshot_id) REFERENCES snapshots(id) ON DELETE SET NULL,
    FOREIGN KEY (latest_snapshot_id) REFERENCES snapshots(id) ON DELETE SET NULL,
    UNIQUE(contest_id, account_id)
);

CREATE INDEX IF NOT EXISTS idx_contest_progress_contest ON contest_progress(contest_id);
CREATE INDEX IF NOT EXISTS idx_contest_progress_account ON contest_progress(account_id);

-- ===================================
-- SNAPSHOT JOBS (MANUAL/SCHEDULED)
-- ===================================
CREATE TABLE IF NOT EXISTS snapshot_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    target_type TEXT NOT NULL, -- account | clan
    target_id INTEGER NOT NULL,
    cadence_cron TEXT NOT NULL,
    last_run DATETIME,
    next_run DATETIME,
    status TEXT DEFAULT 'idle',
    metadata TEXT DEFAULT '{}',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_snapshot_jobs_user ON snapshot_jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_snapshot_jobs_target ON snapshot_jobs(target_type, target_id);
CREATE INDEX IF NOT EXISTS idx_snapshot_jobs_next ON snapshot_jobs(next_run);

-- ===================================
-- WEBHOOKS
-- ===================================
CREATE TABLE IF NOT EXISTS webhooks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_user_id INTEGER NOT NULL,
    target_type TEXT NOT NULL, -- user | clan
    target_id INTEGER,
    provider TEXT NOT NULL, -- discord | slack
    url TEXT NOT NULL,
    secret TEXT,
    events TEXT NOT NULL, -- comma-separated event keys
    active INTEGER DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (owner_user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_webhooks_owner ON webhooks(owner_user_id);
CREATE INDEX IF NOT EXISTS idx_webhooks_target ON webhooks(target_type, target_id);

-- ===================================
-- PUBLIC PROFILES
-- ===================================
CREATE TABLE IF NOT EXISTS public_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    is_public INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_viewed_at DATETIME,
    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE,
    UNIQUE(account_id)
);

CREATE INDEX IF NOT EXISTS idx_public_profiles_slug ON public_profiles(slug);

-- ===================================
-- SCHEMA VERSION
-- ===================================
INSERT OR REPLACE INTO schema_version (id, version, description)
VALUES (4, '1.3', 'Added auth, API tokens, clans/contests, jobs, webhooks, public profiles');
