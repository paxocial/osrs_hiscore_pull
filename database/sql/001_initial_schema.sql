-- OSRS Hiscore Analytics Database Schema
-- Version: 1.0
-- Created: 2025-10-29
-- Description: Initial schema for OSRS Prometheus Dashboard

-- Enable foreign key constraints for SQLite
PRAGMA foreign_keys = ON;

-- ===================================
-- ACCOUNTS TABLE
-- ===================================
CREATE TABLE accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    display_name TEXT,
    default_mode TEXT DEFAULT 'main',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    active INTEGER DEFAULT 1,
    metadata TEXT DEFAULT '{}'
);

-- Indexes for accounts table
CREATE INDEX idx_accounts_name ON accounts(name);
CREATE INDEX idx_accounts_active ON accounts(active);
CREATE INDEX idx_accounts_created_at ON accounts(created_at);


-- ===================================
-- SNAPSHOTS TABLE
-- ===================================
CREATE TABLE snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL,
    snapshot_id TEXT UNIQUE NOT NULL,
    requested_mode TEXT NOT NULL,
    resolved_mode TEXT NOT NULL,
    fetched_at DATETIME NOT NULL,
    endpoint TEXT,
    latency_ms REAL,
    agent_version TEXT,
    total_level INTEGER,
    total_xp INTEGER,
    metadata TEXT DEFAULT '{}',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
);

-- Critical indexes for snapshots table
CREATE INDEX idx_snapshots_account_id ON snapshots(account_id);
CREATE INDEX idx_snapshots_fetched_at ON snapshots(fetched_at);
CREATE INDEX idx_snapshots_account_fetched ON snapshots(account_id, fetched_at);
CREATE INDEX idx_snapshots_resolved_mode ON snapshots(resolved_mode);
CREATE INDEX idx_snapshots_total_xp ON snapshots(total_xp);
CREATE INDEX idx_snapshots_total_level ON snapshots(total_level);
CREATE INDEX idx_snapshots_snapshot_id ON snapshots(snapshot_id);


-- ===================================
-- SKILLS TABLE
-- ===================================
CREATE TABLE skills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_id INTEGER NOT NULL,
    skill_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    level INTEGER,
    xp INTEGER,
    rank INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (snapshot_id) REFERENCES snapshots(id) ON DELETE CASCADE
);

-- Indexes for skills table
CREATE INDEX idx_skills_snapshot_id ON skills(snapshot_id);
CREATE INDEX idx_skills_skill_id ON skills(skill_id);
CREATE INDEX idx_skills_name ON skills(name);
CREATE INDEX idx_skills_level ON skills(level);
CREATE INDEX idx_skills_xp ON skills(xp);
CREATE INDEX idx_skills_snapshot_skill ON skills(snapshot_id, skill_id);


-- ===================================
-- ACTIVITIES TABLE
-- ===================================
CREATE TABLE activities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_id INTEGER NOT NULL,
    activity_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    score INTEGER,
    rank INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (snapshot_id) REFERENCES snapshots(id) ON DELETE CASCADE
);

-- Indexes for activities table
CREATE INDEX idx_activities_snapshot_id ON activities(snapshot_id);
CREATE INDEX idx_activities_activity_id ON activities(activity_id);
CREATE INDEX idx_activities_name ON activities(name);
CREATE INDEX idx_activities_score ON activities(score);
CREATE INDEX idx_activities_snapshot_activity ON activities(snapshot_id, activity_id);


-- ===================================
-- SNAPSHOTS_DELTAS TABLE
-- ===================================
CREATE TABLE snapshots_deltas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    current_snapshot_id INTEGER NOT NULL,
    previous_snapshot_id INTEGER,
    total_xp_delta INTEGER DEFAULT 0,
    skill_deltas TEXT DEFAULT '[]',
    activity_deltas TEXT DEFAULT '[]',
    time_diff_hours REAL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (current_snapshot_id) REFERENCES snapshots(id) ON DELETE CASCADE,
    FOREIGN KEY (previous_snapshot_id) REFERENCES snapshots(id) ON DELETE SET NULL
);

-- Indexes for snapshots_deltas table
CREATE INDEX idx_deltas_current_snapshot ON snapshots_deltas(current_snapshot_id);
CREATE INDEX idx_deltas_previous_snapshot ON snapshots_deltas(previous_snapshot_id);
CREATE INDEX idx_deltas_total_xp_delta ON snapshots_deltas(total_xp_delta);
CREATE INDEX idx_deltas_time_diff ON snapshots_deltas(time_diff_hours);


-- ===================================
-- MODE_CACHE TABLE
-- ===================================
CREATE TABLE mode_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL,
    mode TEXT NOT NULL,
    detected_at DATETIME NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    endpoint_used TEXT,
    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
);

-- Indexes for mode_cache table
CREATE INDEX idx_mode_cache_account_id ON mode_cache(account_id);
CREATE INDEX idx_mode_cache_updated_at ON mode_cache(updated_at);
CREATE UNIQUE INDEX idx_mode_cache_account_unique ON mode_cache(account_id);


-- ===================================
-- SCHEMA_VERSION TABLE
-- ===================================
CREATE TABLE schema_version (
    id INTEGER PRIMARY KEY,
    version TEXT NOT NULL,
    applied_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

-- Insert initial schema version
INSERT INTO schema_version (id, version, description) VALUES (1, '1.0', 'Initial OSRS analytics schema');

-- ===================================
-- VIEWS FOR COMMON QUERIES
-- ===================================

-- Latest snapshot per account
CREATE VIEW latest_snapshots AS
SELECT
    s.*,
    a.name as account_name,
    a.display_name
FROM snapshots s
INNER JOIN accounts a ON s.account_id = a.id
INNER JOIN (
    SELECT
        account_id,
        MAX(fetched_at) as latest_fetched_at
    FROM snapshots
    GROUP BY account_id
) latest ON s.account_id = latest.account_id AND s.fetched_at = latest.latest_fetched_at;

-- Account progress summary
CREATE VIEW account_progress_summary AS
SELECT
    a.id as account_id,
    a.name as account_name,
    COUNT(s.id) as total_snapshots,
    MIN(s.fetched_at) as first_snapshot,
    MAX(s.fetched_at) as latest_snapshot,
    MAX(s.total_xp) as current_total_xp,
    MAX(s.total_level) as current_total_level,
    s.resolved_mode as current_mode
FROM accounts a
LEFT JOIN snapshots s ON a.id = s.account_id
GROUP BY a.id, a.name, s.resolved_mode;

-- Skill progression view
CREATE VIEW skill_progression AS
SELECT
    a.name as account_name,
    sk.name as skill_name,
    s.fetched_at,
    sk.level,
    sk.xp,
    sk.rank,
    LAG(sk.xp) OVER (PARTITION BY a.id, sk.name ORDER BY s.fetched_at) as previous_xp,
    LAG(sk.level) OVER (PARTITION BY a.id, sk.name ORDER BY s.fetched_at) as previous_level
FROM accounts a
INNER JOIN snapshots s ON a.id = s.account_id
INNER JOIN skills sk ON s.id = sk.snapshot_id
ORDER BY a.name, sk.name, s.fetched_at;