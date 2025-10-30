-- Analytics Functions and Procedures
-- Version: 1.2
-- Created: 2025-10-29
-- Description: SQL functions for common analytics calculations

-- ===================================
-- XP RATE CALCULATION FUNCTIONS
-- ===================================

-- Calculate XP rate between two snapshots for a specific skill
CREATE VIEW IF NOT EXISTS skill_xp_rates AS
WITH time_diffs AS (
    SELECT
        s1.id as snapshot_id_1,
        s2.id as snapshot_id_2,
        s1.fetched_at as time_1,
        s2.fetched_at as time_2,
        (julianday(s2.fetched_at) - julianday(s1.fetched_at)) * 24 as hours_diff,
        sk1.xp as xp_1,
        sk2.xp as xp_2,
        sk2.xp - sk1.xp as xp_gain,
        sk2.level as level_2,
        sk1.level as level_1,
        sk2.level - sk1.level as levels_gained,
        a.name as account_name,
        sk1.name as skill_name
    FROM snapshots s1
    JOIN snapshots s2 ON s1.account_id = s2.account_id AND s1.fetched_at < s2.fetched_at
    JOIN accounts a ON s1.account_id = a.id
    JOIN skills sk1 ON s1.id = sk1.snapshot_id
    JOIN skills sk2 ON s2.id = sk2.snapshot_id AND sk1.name = sk2.name
    WHERE sk2.xp > sk1.xp  -- Only positive gains
)
SELECT
    account_name,
    skill_name,
    time_1,
    time_2,
    hours_diff,
    xp_gain,
    levels_gained,
    CASE
        WHEN hours_diff > 0 THEN xp_gain / hours_diff
        ELSE 0
    END as xp_per_hour,
    CASE
        WHEN hours_diff > 24 THEN xp_gain / (hours_diff / 24)
        ELSE xp_gain
    END as xp_per_day,
    level_1,
    level_2
FROM time_diffs
WHERE hours_diff > 0  -- Exclude invalid time differences
  AND xp_gain > 0     -- Only actual gains
ORDER BY account_name, skill_name, time_2 DESC;

-- Recent XP rates (last 7 days)
CREATE VIEW IF NOT EXISTS recent_xp_rates AS
SELECT
    sxr.*,
    CASE
        WHEN sxr.hours_diff <= 24 THEN 'Very Recent'
        WHEN sxr.hours_diff <= 72 THEN 'Recent'
        ELSE 'Older'
    END as recency_category
FROM skill_xp_rates sxr
WHERE sxr.time_2 > datetime('now', '-7 days')
  AND sxr.xp_per_hour > 0;

-- ===================================
-- PROGRESS ANALYSIS VIEWS
-- ===================================

-- Level milestones view
CREATE VIEW IF NOT EXISTS level_milestones AS
WITH level_changes AS (
    SELECT
        a.name as account_name,
        sk.name as skill_name,
        s.fetched_at,
        sk.level,
        LAG(sk.level) OVER (PARTITION BY a.id, sk.name ORDER BY s.fetched_at) as previous_level,
        sk.xp,
        LAG(sk.xp) OVER (PARTITION BY a.id, sk.name ORDER BY s.fetched_at) as previous_xp
    FROM accounts a
    JOIN snapshots s ON a.id = s.account_id
    JOIN skills sk ON s.id = sk.snapshot_id
)
SELECT
    account_name,
    skill_name,
    fetched_at,
    level,
    previous_level,
    xp,
    previous_xp,
    xp - previous_xp as xp_for_level,
    CASE
        WHEN level IN (10, 20, 30, 40, 50, 60, 70, 80, 90, 99) THEN 'Major Milestone'
        WHEN level % 5 = 0 THEN 'Minor Milestone'
        ELSE 'Regular Progress'
    END as milestone_type
FROM level_changes
WHERE previous_level IS NOT NULL
  AND level > previous_level
ORDER BY account_name, skill_name, fetched_at DESC;

-- ===================================
-- COMPARISON ANALYSIS
-- ===================================

-- Account comparison view
CREATE VIEW IF NOT EXISTS account_comparison AS
WITH latest_stats AS (
    SELECT
        a.id as account_id,
        a.name as account_name,
        s.resolved_mode,
        s.total_xp,
        s.total_level,
        s.fetched_at as last_updated,
        -- Skill rankings
        (SELECT COUNT(*) + 1 FROM accounts a2
         JOIN snapshots s2 ON a2.id = s2.account_id
         JOIN skills sk2 ON s2.id = sk2.snapshot_id
         WHERE sk2.name = 'Overall' AND sk2.xp > sk.xp
         AND s2.fetched_at = (
             SELECT MAX(fetched_at) FROM snapshots WHERE account_id = a2.id
         )) as overall_xp_rank
    FROM accounts a
    JOIN snapshots s ON a.id = s.account_id
    WHERE s.fetched_at = (
        SELECT MAX(fetched_at) FROM snapshots WHERE account_id = a.id
    )
)
SELECT
    ls.*,
    -- Calculate percentiles (approximate for SQLite)
    (SELECT COUNT(*) FROM latest_stats ls2 WHERE ls2.total_xp < ls.total_xp) * 100.0 /
        (SELECT COUNT(*) FROM latest_stats) as xp_percentile,
    (SELECT COUNT(*) FROM latest_stats ls2 WHERE ls2.total_level < ls.total_level) * 100.0 /
        (SELECT COUNT(*) FROM latest_stats) as level_percentile
FROM latest_stats ls
ORDER BY ls.total_xp DESC;

-- ===================================
-- PERFORMANCE METRICS
-- ===================================

-- Fastest growing accounts (by XP)
CREATE VIEW IF NOT EXISTS fastest_growing_accounts AS
WITH weekly_growth AS (
    SELECT
        a.name as account_name,
        SUM(sd.total_xp_delta) as weekly_xp_gain,
        COUNT(*) as snapshots_count,
        AVG(sd.time_diff_hours) as avg_time_between_snapshots
    FROM accounts a
    JOIN snapshots s ON a.id = s.account_id
    JOIN snapshots_deltas sd ON s.id = sd.current_snapshot_id
    WHERE sd.created_at > datetime('now', '-7 days')
      AND sd.total_xp_delta > 0
    GROUP BY a.id, a.name
    HAVING snapshots_count >= 2
)
SELECT
    account_name,
    weekly_xp_gain,
    weekly_xp_gain / 7.0 as daily_average,
    snapshots_count,
    avg_time_between_snapshots,
    CASE
        WHEN weekly_xp_gain > 1000000 THEN 'Exceptional'
        WHEN weekly_xp_gain > 500000 THEN 'Very High'
        WHEN weekly_xp_gain > 100000 THEN 'High'
        WHEN weekly_xp_gain > 50000 THEN 'Above Average'
        ELSE 'Average'
    END as growth_category
FROM weekly_growth
ORDER BY weekly_xp_gain DESC;

-- ===================================
-- UTILITY FUNCTIONS
-- ===================================

-- Helper function to calculate XP needed for next level
CREATE VIEW IF NOT EXISTS xp_to_next_level AS
WITH current_skills AS (
    SELECT
        a.name as account_name,
        sk.name as skill_name,
        sk.level,
        sk.xp,
        s.fetched_at
    FROM accounts a
    JOIN snapshots s ON a.id = s.account_id
    JOIN skills sk ON s.id = sk.snapshot_id
    WHERE s.fetched_at = (
        SELECT MAX(fetched_at) FROM snapshots WHERE account_id = a.id
    )
      AND sk.name != 'Overall'
)
SELECT
    account_name,
    skill_name,
    level,
    xp,
    CASE
        WHEN level >= 99 THEN 0  -- Max level
        WHEN level = 98 THEN (13034431 - xp)  -- XP to 99
        ELSE
            -- Simplified XP calculation for demonstration
            CASE
                WHEN level < 10 THEN (level + 1) * 100 - xp
                WHEN level < 20 THEN (level + 1) * 500 - xp
                WHEN level < 50 THEN (level + 1) * 1000 - xp
                WHEN level < 90 THEN (level + 1) * 5000 - xp
                ELSE (level + 1) * 10000 - xp
            END
    END as xp_to_next_level,
    CASE
        WHEN level >= 99 THEN 0
        ELSE
            CASE
                WHEN level < 10 THEN (level + 1) * 100
                WHEN level < 20 THEN (level + 1) * 500
                WHEN level < 50 THEN (level + 1) * 1000
                WHEN level < 90 THEN (level + 1) * 5000
                ELSE (level + 1) * 10000
            END
    END as next_level_xp
FROM current_skills
WHERE level < 99;

-- Update schema version
INSERT OR REPLACE INTO schema_version (id, version, description)
VALUES (3, '1.2', 'Added analytics functions and performance views');