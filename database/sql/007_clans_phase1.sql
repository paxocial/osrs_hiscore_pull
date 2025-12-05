-- Clans Phase 1 schema updates: richer contests, clan batch snapshots, schedules, stats, leaderboards.
-- Version: 1.6
-- Created: 2025-12-05
-- Description: Adds clan schedules, clan snapshots/aggregates, contest rules/entries/draws, and contest fairness fields.

PRAGMA foreign_keys = ON;

-- ===================================
-- CLAN SCHEDULES (up to 2/day)
-- ===================================
CREATE TABLE IF NOT EXISTS clan_schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    clan_id INTEGER NOT NULL,
    cron TEXT NOT NULL,
    max_daily_runs INTEGER DEFAULT 1, -- enforce <=2 via app logic
    enabled INTEGER DEFAULT 1,
    next_run_at DATETIME,
    last_run_status TEXT DEFAULT 'idle',
    last_error TEXT,
    created_by_user_id INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (clan_id) REFERENCES clans(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by_user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_clan_schedules_clan ON clan_schedules(clan_id);
CREATE INDEX IF NOT EXISTS idx_clan_schedules_next ON clan_schedules(next_run_at);

-- ===================================
-- CLAN SNAPSHOTS (batch runs)
-- ===================================
CREATE TABLE IF NOT EXISTS clan_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    clan_id INTEGER NOT NULL,
    job_id TEXT,
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    finished_at DATETIME,
    status TEXT DEFAULT 'pending', -- pending | running | success | error
    latency_ms REAL,
    error TEXT,
    member_count INTEGER,
    mode TEXT,
    requested_by_user_id INTEGER,
    metadata TEXT DEFAULT '{}',
    FOREIGN KEY (clan_id) REFERENCES clans(id) ON DELETE CASCADE,
    FOREIGN KEY (requested_by_user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_clan_snapshots_clan ON clan_snapshots(clan_id);
CREATE INDEX IF NOT EXISTS idx_clan_snapshots_status ON clan_snapshots(status);

CREATE TABLE IF NOT EXISTS clan_snapshot_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    clan_snapshot_id INTEGER NOT NULL,
    account_id INTEGER NOT NULL,
    snapshot_id INTEGER, -- references snapshots.id
    status TEXT DEFAULT 'pending', -- pending | success | error
    error TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (clan_snapshot_id) REFERENCES clan_snapshots(id) ON DELETE CASCADE,
    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE,
    FOREIGN KEY (snapshot_id) REFERENCES snapshots(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_clan_snapshot_members_snapshot ON clan_snapshot_members(clan_snapshot_id);
CREATE INDEX IF NOT EXISTS idx_clan_snapshot_members_account ON clan_snapshot_members(account_id);

-- ===================================
-- CLAN STATS / LEADERBOARDS (cached aggregates)
-- ===================================
CREATE TABLE IF NOT EXISTS clan_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    clan_id INTEGER NOT NULL,
    timeframe TEXT NOT NULL, -- 7d | 30d | mtd | custom
    start_at DATETIME,
    end_at DATETIME,
    generated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    payload TEXT NOT NULL, -- JSON blob with totals, per-skill/per-activity deltas, top performers
    FOREIGN KEY (clan_id) REFERENCES clans(id) ON DELETE CASCADE,
    UNIQUE(clan_id, timeframe, start_at, end_at)
);

CREATE INDEX IF NOT EXISTS idx_clan_stats_clan ON clan_stats(clan_id);

CREATE TABLE IF NOT EXISTS clan_leaderboards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    clan_id INTEGER NOT NULL,
    metric TEXT NOT NULL, -- xp_gained | levels_gained | skill_xp | boss_kc | clues
    timeframe TEXT NOT NULL,
    start_at DATETIME,
    end_at DATETIME,
    generated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    rows TEXT NOT NULL, -- JSON array of leaderboard rows
    FOREIGN KEY (clan_id) REFERENCES clans(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_clan_leaderboards_clan ON clan_leaderboards(clan_id);
CREATE INDEX IF NOT EXISTS idx_clan_leaderboards_metric ON clan_leaderboards(metric, timeframe);

-- ===================================
-- CONTESTS REBUILD + SUPPORTING TABLES
-- ===================================
PRAGMA foreign_keys = OFF;

DROP TABLE IF EXISTS contest_draws;
DROP TABLE IF EXISTS contest_entries;
DROP TABLE IF EXISTS contest_rules;
DROP TABLE IF EXISTS contests;
DROP TABLE IF EXISTS contests_new;
DROP TABLE IF EXISTS contests_stage;

CREATE TABLE contests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    clan_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    metric TEXT NOT NULL, -- xp | level | boss_kc | clues | custom
    start_at DATETIME NOT NULL,
    end_at DATETIME,
    reward TEXT,
    metadata TEXT DEFAULT '{}',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'draft', -- draft | active | ended | drawn
    prize TEXT,
    seed_commitment TEXT,
    seed_reveal TEXT,
    nonce TEXT,
    hash_fn TEXT DEFAULT 'sha256',
    created_by_user_id INTEGER,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (clan_id) REFERENCES clans(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_contests_clan ON contests(clan_id);
CREATE INDEX IF NOT EXISTS idx_contests_metric ON contests(metric);
CREATE INDEX IF NOT EXISTS idx_contests_time ON contests(start_at, end_at);
CREATE INDEX IF NOT EXISTS idx_contests_status ON contests(status);

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS contest_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contest_id INTEGER NOT NULL,
    type TEXT NOT NULL, -- skill_xp | skill_levels | total_xp | boss_kc | clue_count
    targets TEXT,
    threshold INTEGER NOT NULL,
    comparator TEXT DEFAULT '>=',
    timeframe TEXT DEFAULT 'contest', -- contest | custom
    weight INTEGER DEFAULT 1,
    title TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (contest_id) REFERENCES contests(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_contest_rules_contest ON contest_rules(contest_id);

CREATE TABLE IF NOT EXISTS contest_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contest_id INTEGER NOT NULL,
    rule_id INTEGER,
    account_id INTEGER NOT NULL,
    entry_count INTEGER DEFAULT 1,
    proof TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (contest_id) REFERENCES contests(id) ON DELETE CASCADE,
    FOREIGN KEY (rule_id) REFERENCES contest_rules(id) ON DELETE SET NULL,
    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_contest_entries_contest ON contest_entries(contest_id);
CREATE INDEX IF NOT EXISTS idx_contest_entries_account ON contest_entries(account_id);

CREATE TABLE IF NOT EXISTS contest_draws (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contest_id INTEGER NOT NULL,
    drawn_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    winner_account_id INTEGER,
    winner_entry_id INTEGER,
    seed_reveal TEXT,
    nonce TEXT,
    rng_proof TEXT,
    notes TEXT,
    FOREIGN KEY (contest_id) REFERENCES contests(id) ON DELETE CASCADE,
    FOREIGN KEY (winner_account_id) REFERENCES accounts(id) ON DELETE SET NULL,
    FOREIGN KEY (winner_entry_id) REFERENCES contest_entries(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_contest_draws_contest ON contest_draws(contest_id);

-- ===================================
-- SCHEMA VERSION
-- ===================================
INSERT OR REPLACE INTO schema_version (id, version, description)
VALUES (7, '1.6', 'Clans Phase 1: schedules, batch snapshots, cached stats, extended contests');
