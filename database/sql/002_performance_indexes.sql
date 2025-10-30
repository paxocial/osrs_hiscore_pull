-- Performance Optimization Indexes
-- Version: 1.1
-- Created: 2025-10-29
-- Description: Additional indexes for analytics performance

-- ===================================
-- COMPOSITE INDEXES FOR ANALYTICS
-- ===================================

-- Account + Time indexes for trend analysis
CREATE INDEX IF NOT EXISTS idx_snapshots_account_time ON snapshots(account_id, fetched_at DESC);

-- Mode + Time for analytics by game mode
CREATE INDEX IF NOT EXISTS idx_snapshots_mode_time ON snapshots(resolved_mode, fetched_at DESC);

-- Skill progression tracking
CREATE INDEX IF NOT EXISTS idx_skills_account_skill_time ON skills(snapshot_id, skill_id)
WHERE skill_id IN (1, 2, 3, 4, 5, 6, 7);  -- Combat skills

-- High-level skills tracking
CREATE INDEX IF NOT EXISTS idx_skills_high_level ON skills(snapshot_id, level)
WHERE level >= 70;

-- Activity tracking for combat skills
CREATE INDEX IF NOT EXISTS idx_activities_combat ON activities(snapshot_id, score)
WHERE name IN ('Alchemical Hydra', 'Zulrah', 'Vorkath', 'Thermonuclear Smoke Devil');

-- Time-based delta analysis
CREATE INDEX IF NOT EXISTS idx_deltas_time_xp ON snapshots_deltas(time_diff_hours, total_xp_delta);

-- Recent snapshots for performance (simple index)
CREATE INDEX IF NOT EXISTS idx_snapshots_recent ON snapshots(fetched_at DESC);

-- ===================================
-- PARTIAL INDEXES FOR COMMON FILTERS
-- ===================================

-- Active accounts only
CREATE INDEX IF NOT EXISTS idx_accounts_active_recent ON accounts(id, updated_at)
WHERE active = 1;

-- Significant XP gains only
CREATE INDEX IF NOT EXISTS idx_deltas_significant ON snapshots_deltas(current_snapshot_id, total_xp_delta)
WHERE total_xp_delta > 10000;

-- Recent level gains (simple index)
CREATE INDEX IF NOT EXISTS idx_deltas_levels_recent ON snapshots_deltas(current_snapshot_id, created_at);

-- High XP accounts (potential power users)
CREATE INDEX IF NOT EXISTS idx_snapshots_high_xp ON snapshots(account_id, total_xp)
WHERE total_xp > 50000000;

-- ===================================
-- FULL-TEXT SEARCH INDEXES (Simplified)
-- ===================================

-- Account name search (basic implementation)
CREATE VIRTUAL TABLE IF NOT EXISTS accounts_fts USING fts5(
    name,
    display_name
);

-- Skill name search (basic implementation)
CREATE VIRTUAL TABLE IF NOT EXISTS skills_fts USING fts5(
    name
);

-- Activity name search (basic implementation)
CREATE VIRTUAL TABLE IF NOT EXISTS activities_fts USING fts5(
    name
);

-- Note: FTS tables will be populated via application logic to avoid trigger complexity

-- Update schema version
INSERT OR REPLACE INTO schema_version (id, version, description)
VALUES (2, '1.1', 'Added performance optimization indexes (simplified)');