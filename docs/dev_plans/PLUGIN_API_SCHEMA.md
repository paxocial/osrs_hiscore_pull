# Plugin API Database Schema

**Version:** 1.0
**Created:** 2026-01-30
**Purpose:** Complete database schema documentation for Catherby RuneLite Plugin API

This document defines the database schema for storing RuneLite plugin telemetry data. The schema includes 11 tables designed to capture gameplay events, player progress, and audit logs.

---

## Table of Contents

1. [Schema Overview](#schema-overview)
2. [Table Definitions](#table-definitions)
   - [plugin_sessions](#1-plugin_sessions)
   - [plugin_xp_snapshots](#2-plugin_xp_snapshots)
   - [plugin_collection_log](#3-plugin_collection_log)
   - [plugin_quests](#4-plugin_quests)
   - [plugin_diaries](#5-plugin_diaries)
   - [plugin_combat_achievements](#6-plugin_combat_achievements)
   - [plugin_equipment](#7-plugin_equipment)
   - [plugin_loot](#8-plugin_loot)
   - [plugin_activity](#9-plugin_activity)
   - [plugin_bank](#10-plugin_bank)
   - [plugin_sync_log](#11-plugin_sync_log)
3. [JSON Structure Documentation](#json-structure-documentation)
4. [Index Strategy](#index-strategy)
5. [PostgreSQL Migration Notes](#postgresql-migration-notes)
6. [Sample Queries](#sample-queries)

---

## Schema Overview

### Design Principles

- **Time-Series Data**: All plugin tables are append-only time-series tables optimized for write-heavy workloads
- **Foreign Key Cascade**: All tables reference `accounts(id)` with `ON DELETE CASCADE` to maintain referential integrity
- **JSON Storage**: Complex nested data (skills, equipment, inventory) stored as JSON TEXT for SQLite compatibility
- **Audit Trail**: Comprehensive audit logging via `plugin_sync_log` table
- **Timestamp Tracking**: Dual timestamps (`timestamp` = event time, `created_at` = insertion time)
- **Idempotency**: Tables that receive discrete events (loot, collection_log, sessions) include an `event_id` UUID column with a UNIQUE constraint to prevent duplicate rows on plugin retry
- **Composite Indexes**: All tables use `(account_id, timestamp)` composite indexes from day one — this is the primary access pattern

### Relationships

```
accounts (1) ──┬── (*) plugin_sessions
               ├── (*) plugin_xp_snapshots
               ├── (*) plugin_collection_log
               ├── (*) plugin_quests
               ├── (*) plugin_diaries
               ├── (*) plugin_combat_achievements
               ├── (*) plugin_equipment
               ├── (*) plugin_loot
               ├── (*) plugin_activity
               ├── (*) plugin_bank
               └── (*) plugin_sync_log

api_tokens (1) ─── (*) plugin_sync_log
```

---

## Table Definitions

### 1. plugin_sessions

Tracks player session lifecycle events (login, logout, world hop).

```sql
CREATE TABLE IF NOT EXISTS plugin_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL,
    event_id TEXT NOT NULL,                 -- UUID from plugin for idempotent submissions
    session_id TEXT NOT NULL,
    event TEXT NOT NULL,                    -- 'login' | 'logout' | 'world_hop'
    world INTEGER NOT NULL,                 -- OSRS world number (300-600)
    duration_seconds INTEGER,               -- Session duration (NULL for login/hop, populated for logout)
    timestamp DATETIME NOT NULL,            -- Event timestamp (UTC)
    plugin_version TEXT NOT NULL,           -- Plugin version (semver)
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
);

CREATE INDEX idx_plugin_sessions_account_ts ON plugin_sessions(account_id, timestamp);
CREATE INDEX idx_plugin_sessions_session ON plugin_sessions(session_id);
CREATE INDEX idx_plugin_sessions_event ON plugin_sessions(event);
CREATE UNIQUE INDEX idx_plugin_sessions_event_id ON plugin_sessions(event_id);
```

**Column Details:**

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | INTEGER | NO | Primary key (autoincrement) |
| `account_id` | INTEGER | NO | Foreign key to `accounts(id)` |
| `event_id` | TEXT | NO | UUID from plugin for idempotent submissions |
| `session_id` | TEXT | NO | Unique session identifier (UUID from plugin) |
| `event` | TEXT | NO | Event type: `login`, `logout`, `world_hop` |
| `world` | INTEGER | NO | OSRS world number (300-600 range) |
| `duration_seconds` | INTEGER | YES | Session duration (only for `logout` events) |
| `timestamp` | DATETIME | NO | Event timestamp (UTC) |
| `plugin_version` | TEXT | NO | Plugin version (e.g., `1.0.0`) |
| `created_at` | DATETIME | NO | Record insertion timestamp |

**Notes:**
- Session tracking allows play time analysis and world hop detection
- `duration_seconds` computed by plugin (logout timestamp - login timestamp)
- Same `session_id` used for login and logout events
- **`plugin_version` per-row note:** Every row stores `plugin_version` for traceability. At scale, consider normalizing this to the session level — all events within a session use the same plugin version. The session table becomes the source of truth for version, and other tables can omit it.

---

### 2. plugin_xp_snapshots

Stores XP snapshots for all 23 OSRS skills.

```sql
CREATE TABLE IF NOT EXISTS plugin_xp_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL,
    skills TEXT NOT NULL,                   -- JSON: {"attack": 13034431, "defence": 1234, ...}
    world INTEGER,                          -- OSRS world number (nullable)
    timestamp DATETIME NOT NULL,            -- Snapshot timestamp (UTC)
    plugin_version TEXT NOT NULL,           -- Plugin version (semver)
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
);

CREATE INDEX idx_plugin_xp_snapshots_account_ts ON plugin_xp_snapshots(account_id, timestamp);
```

**Column Details:**

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | INTEGER | NO | Primary key (autoincrement) |
| `account_id` | INTEGER | NO | Foreign key to `accounts(id)` |
| `skills` | TEXT | NO | JSON object with all 23 skill XP values |
| `world` | INTEGER | YES | OSRS world number (optional) |
| `timestamp` | DATETIME | NO | Snapshot timestamp (UTC) |
| `plugin_version` | TEXT | NO | Plugin version (e.g., `1.0.0`) |
| `created_at` | DATETIME | NO | Record insertion timestamp |

**JSON Structure (`skills`):**
```json
{
    "attack": 13034431,
    "defence": 1154,
    "strength": 4470000,
    "hitpoints": 3000000,
    "ranged": 2500000,
    "prayer": 500000,
    "magic": 1800000,
    "cooking": 1100000,
    "woodcutting": 950000,
    "fletching": 800000,
    "fishing": 700000,
    "firemaking": 600000,
    "crafting": 1300000,
    "smithing": 400000,
    "mining": 850000,
    "herblore": 1200000,
    "agility": 750000,
    "thieving": 900000,
    "slayer": 3500000,
    "farming": 2200000,
    "runecraft": 650000,
    "hunter": 1050000,
    "construction": 1400000
}
```

**Notes:**
- All 23 skills required (validation in Pydantic model)
- XP values are integers (minimum 0)
- Enables XP gain tracking and skill progress analytics

---

### 3. plugin_collection_log

Records collection log item obtained events.

```sql
CREATE TABLE IF NOT EXISTS plugin_collection_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL,
    event_id TEXT NOT NULL,                 -- UUID from plugin for idempotent submissions
    item_id INTEGER NOT NULL,               -- OSRS item ID
    item_name TEXT NOT NULL,                -- Item display name
    quantity INTEGER NOT NULL,              -- Quantity obtained
    source TEXT NOT NULL,                   -- Source/boss/activity name
    obtained_at DATETIME NOT NULL,          -- Item obtained timestamp
    world INTEGER,                          -- OSRS world number (nullable)
    timestamp DATETIME NOT NULL,            -- Event submission timestamp (UTC)
    plugin_version TEXT NOT NULL,           -- Plugin version (semver)
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
);

CREATE INDEX idx_plugin_collection_log_account_ts ON plugin_collection_log(account_id, timestamp);
CREATE INDEX idx_plugin_collection_log_item ON plugin_collection_log(item_id);
CREATE INDEX idx_plugin_collection_log_source ON plugin_collection_log(source);
CREATE INDEX idx_plugin_collection_log_obtained ON plugin_collection_log(obtained_at);
CREATE UNIQUE INDEX idx_plugin_collection_log_event_id ON plugin_collection_log(event_id);
```

**Column Details:**

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | INTEGER | NO | Primary key (autoincrement) |
| `account_id` | INTEGER | NO | Foreign key to `accounts(id)` |
| `item_id` | INTEGER | NO | OSRS item ID (e.g., `11832` for Bandos chestplate) |
| `item_name` | TEXT | NO | Item display name (e.g., `"Bandos chestplate"`) |
| `quantity` | INTEGER | NO | Quantity obtained (minimum 1) |
| `source` | TEXT | NO | Source name (e.g., `"General Graardor"`, `"Chambers of Xeric"`) |
| `obtained_at` | DATETIME | NO | Timestamp when item was obtained |
| `world` | INTEGER | YES | OSRS world number (optional) |
| `timestamp` | DATETIME | NO | Event submission timestamp (UTC) |
| `plugin_version` | TEXT | NO | Plugin version (e.g., `1.0.0`) |
| `created_at` | DATETIME | NO | Record insertion timestamp |

**Notes:**
- Tracks collection log completions and rare drops
- `obtained_at` vs `timestamp`: obtained_at = when plugin detected drop, timestamp = when submitted to API
- Supports duplicate tracking (same item obtained multiple times)

---

### 4. plugin_quests

Tracks quest progress updates.

```sql
CREATE TABLE IF NOT EXISTS plugin_quests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL,
    quest_name TEXT NOT NULL,               -- Quest name
    state TEXT NOT NULL,                    -- 'not_started' | 'in_progress' | 'complete'
    world INTEGER,                          -- OSRS world number (nullable)
    timestamp DATETIME NOT NULL,            -- State change timestamp (UTC)
    plugin_version TEXT NOT NULL,           -- Plugin version (semver)
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
);

CREATE INDEX idx_plugin_quests_account_ts ON plugin_quests(account_id, timestamp);
CREATE INDEX idx_plugin_quests_name ON plugin_quests(quest_name);
CREATE INDEX idx_plugin_quests_state ON plugin_quests(state);
```

**Column Details:**

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | INTEGER | NO | Primary key (autoincrement) |
| `account_id` | INTEGER | NO | Foreign key to `accounts(id)` |
| `quest_name` | TEXT | NO | Quest name (e.g., `"Dragon Slayer II"`) |
| `state` | TEXT | NO | Quest state: `not_started`, `in_progress`, `complete` |
| `world` | INTEGER | YES | OSRS world number (optional) |
| `timestamp` | DATETIME | NO | State change timestamp (UTC) |
| `plugin_version` | TEXT | NO | Plugin version (e.g., `1.0.0`) |
| `created_at` | DATETIME | NO | Record insertion timestamp |

**Notes:**
- Time-series design allows tracking quest progress over time
- State transitions: `not_started` → `in_progress` → `complete`
- Supports quest completion analytics and progress tracking

---

### 5. plugin_diaries

Tracks achievement diary progress by region and tier.

```sql
CREATE TABLE IF NOT EXISTS plugin_diaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL,
    region TEXT NOT NULL,                   -- Diary region (e.g., 'Varrock', 'Lumbridge')
    easy INTEGER NOT NULL DEFAULT 0,        -- Easy tier completed (0 = false, 1 = true)
    medium INTEGER NOT NULL DEFAULT 0,      -- Medium tier completed
    hard INTEGER NOT NULL DEFAULT 0,        -- Hard tier completed
    elite INTEGER NOT NULL DEFAULT 0,       -- Elite tier completed
    world INTEGER,                          -- OSRS world number (nullable)
    timestamp DATETIME NOT NULL,            -- Progress update timestamp (UTC)
    plugin_version TEXT NOT NULL,           -- Plugin version (semver)
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
);

CREATE INDEX idx_plugin_diaries_account_ts ON plugin_diaries(account_id, timestamp);
CREATE INDEX idx_plugin_diaries_region ON plugin_diaries(region);
```

**Column Details:**

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | INTEGER | NO | Primary key (autoincrement) |
| `account_id` | INTEGER | NO | Foreign key to `accounts(id)` |
| `region` | TEXT | NO | Diary region (e.g., `"Varrock"`, `"Lumbridge"`, `"Desert"`) |
| `easy` | INTEGER | NO | Easy tier completed (0 = false, 1 = true) |
| `medium` | INTEGER | NO | Medium tier completed (0 = false, 1 = true) |
| `hard` | INTEGER | NO | Hard tier completed (0 = false, 1 = true) |
| `elite` | INTEGER | NO | Elite tier completed (0 = false, 1 = true) |
| `world` | INTEGER | YES | OSRS world number (optional) |
| `timestamp` | DATETIME | NO | Progress update timestamp (UTC) |
| `plugin_version` | TEXT | NO | Plugin version (e.g., `1.0.0`) |
| `created_at` | DATETIME | NO | Record insertion timestamp |

**Notes:**
- SQLite uses INTEGER for booleans (0 = false, 1 = true)
- Each row represents a snapshot of diary progress for one region
- Time-series design allows tracking tier completions over time

---

### 6. plugin_combat_achievements

Tracks combat achievement progress by tier and individual tasks.

```sql
CREATE TABLE IF NOT EXISTS plugin_combat_achievements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL,
    tier_progress TEXT NOT NULL,            -- JSON: {"easy": 5, "medium": 3, "hard": 1, ...}
    completed_tasks TEXT NOT NULL,          -- JSON: ["Kill Zulrah", "Complete CoX", ...]
    world INTEGER,                          -- OSRS world number (nullable)
    timestamp DATETIME NOT NULL,            -- Progress update timestamp (UTC)
    plugin_version TEXT NOT NULL,           -- Plugin version (semver)
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
);

CREATE INDEX idx_plugin_combat_achievements_account_ts ON plugin_combat_achievements(account_id, timestamp);
```

**Column Details:**

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | INTEGER | NO | Primary key (autoincrement) |
| `account_id` | INTEGER | NO | Foreign key to `accounts(id)` |
| `tier_progress` | TEXT | NO | JSON object with tier completion counts |
| `completed_tasks` | TEXT | NO | JSON array of completed task names |
| `world` | INTEGER | YES | OSRS world number (optional) |
| `timestamp` | DATETIME | NO | Progress update timestamp (UTC) |
| `plugin_version` | TEXT | NO | Plugin version (e.g., `1.0.0`) |
| `created_at` | DATETIME | NO | Record insertion timestamp |

**JSON Structure (`tier_progress`):**
```json
{
    "easy": 15,
    "medium": 8,
    "hard": 3,
    "elite": 1,
    "master": 0,
    "grandmaster": 0
}
```

**JSON Structure (`completed_tasks`):**
```json
[
    "Kill Zulrah",
    "Complete Chambers of Xeric",
    "Kill Vorkath with no damage",
    "Complete Theatre of Blood"
]
```

**Notes:**
- Tier progress counts how many tasks completed per tier
- `completed_tasks` array contains human-readable task names
- Supports granular combat achievement tracking

---

### 7. plugin_equipment

Stores player equipment and inventory snapshots.

```sql
CREATE TABLE IF NOT EXISTS plugin_equipment (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL,
    equipment TEXT NOT NULL,                -- JSON: {"head": 11832, "cape": 21295, ...}
    inventory TEXT NOT NULL,                -- JSON: [{"item_id": 560, "quantity": 1000}, ...]
    world INTEGER,                          -- OSRS world number (nullable)
    timestamp DATETIME NOT NULL,            -- Snapshot timestamp (UTC)
    plugin_version TEXT NOT NULL,           -- Plugin version (semver)
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
);

CREATE INDEX idx_plugin_equipment_account_ts ON plugin_equipment(account_id, timestamp);
```

**Column Details:**

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | INTEGER | NO | Primary key (autoincrement) |
| `account_id` | INTEGER | NO | Foreign key to `accounts(id)` |
| `equipment` | TEXT | NO | JSON object mapping equipment slots to item IDs |
| `inventory` | TEXT | NO | JSON array of inventory items |
| `world` | INTEGER | YES | OSRS world number (optional) |
| `timestamp` | DATETIME | NO | Snapshot timestamp (UTC) |
| `plugin_version` | TEXT | NO | Plugin version (e.g., `1.0.0`) |
| `created_at` | DATETIME | NO | Record insertion timestamp |

**JSON Structure (`equipment`):**
```json
{
    "head": 11832,
    "cape": 21295,
    "neck": 19547,
    "weapon": 11806,
    "body": 11834,
    "shield": 12954,
    "legs": 11836,
    "hands": 7462,
    "feet": 11840,
    "ring": 19550,
    "ammo": 21326
}
```

**JSON Structure (`inventory`):**
```json
[
    {"item_id": 560, "quantity": 1000},
    {"item_id": 555, "quantity": 5000},
    {"item_id": 385, "quantity": 10},
    {"item_id": 3144, "quantity": 1}
]
```

**Notes:**
- Equipment slots use standard OSRS names (head, cape, neck, weapon, etc.)
- Empty slots omitted from equipment JSON
- Inventory array can be empty (no specific ordering)

---

### 8. plugin_loot

Records loot drop received events.

```sql
CREATE TABLE IF NOT EXISTS plugin_loot (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL,
    event_id TEXT NOT NULL,                 -- UUID from plugin for idempotent submissions
    item_id INTEGER NOT NULL,               -- OSRS item ID
    item_name TEXT NOT NULL,                -- Item display name
    quantity INTEGER NOT NULL,              -- Quantity dropped
    ge_value INTEGER,                       -- Grand Exchange value at drop time (coins)
    source TEXT NOT NULL,                   -- Source name (NPC/boss/chest)
    source_type TEXT NOT NULL,              -- 'npc' | 'boss' | 'chest' | 'clue' | 'minigame' | 'other'
    world INTEGER,                          -- OSRS world number (nullable)
    timestamp DATETIME NOT NULL,            -- Loot drop timestamp (UTC)
    plugin_version TEXT NOT NULL,           -- Plugin version (semver)
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
);

CREATE INDEX idx_plugin_loot_account_ts ON plugin_loot(account_id, timestamp);
CREATE INDEX idx_plugin_loot_item ON plugin_loot(item_id);
CREATE INDEX idx_plugin_loot_source ON plugin_loot(source);
CREATE INDEX idx_plugin_loot_source_type ON plugin_loot(source_type);
CREATE INDEX idx_plugin_loot_value ON plugin_loot(ge_value);
CREATE UNIQUE INDEX idx_plugin_loot_event_id ON plugin_loot(event_id);
```

**Column Details:**

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | INTEGER | NO | Primary key (autoincrement) |
| `account_id` | INTEGER | NO | Foreign key to `accounts(id)` |
| `item_id` | INTEGER | NO | OSRS item ID (e.g., `11832`) |
| `item_name` | TEXT | NO | Item display name (e.g., `"Bandos chestplate"`) |
| `quantity` | INTEGER | NO | Quantity dropped (minimum 1) |
| `ge_value` | INTEGER | YES | Grand Exchange value per item (coins) |
| `source` | TEXT | NO | Source name (e.g., `"General Graardor"`, `"Barrows chest"`) |
| `source_type` | TEXT | NO | Source type: `npc`, `boss`, `chest`, `clue`, `minigame`, `other` |
| `world` | INTEGER | YES | OSRS world number (optional) |
| `timestamp` | DATETIME | NO | Loot drop timestamp (UTC) |
| `plugin_version` | TEXT | NO | Plugin version (e.g., `1.0.0`) |
| `created_at` | DATETIME | NO | Record insertion timestamp |

**Notes:**
- `ge_value` nullable (not all items have GE prices)
- `ge_value` is the **GE price at drop time** as reported by the plugin (sourced from RuneLite's item price cache). This is a point-in-time snapshot — prices change constantly. For current-value analytics, join against a separate price table or re-fetch from GE API.
- Supports loot analytics, boss profitability tracking, rare drop detection
- `source_type` enables filtering by content category

---

### 9. plugin_activity

Tracks general player activity updates and miscellaneous events.

```sql
CREATE TABLE IF NOT EXISTS plugin_activity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL,
    activity TEXT NOT NULL,                 -- Activity name/type
    detail TEXT,                            -- Additional activity details (nullable)
    world INTEGER,                          -- OSRS world number (nullable)
    timestamp DATETIME NOT NULL,            -- Activity timestamp (UTC)
    plugin_version TEXT NOT NULL,           -- Plugin version (semver)
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
);

CREATE INDEX idx_plugin_activity_account_ts ON plugin_activity(account_id, timestamp);
CREATE INDEX idx_plugin_activity_activity ON plugin_activity(activity);
```

**Column Details:**

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | INTEGER | NO | Primary key (autoincrement) |
| `account_id` | INTEGER | NO | Foreign key to `accounts(id)` |
| `activity` | TEXT | NO | Activity name/type (e.g., `"minigame_start"`, `"teleport"`) |
| `detail` | TEXT | YES | Additional details (JSON or freeform text) |
| `world` | INTEGER | YES | OSRS world number (optional) |
| `timestamp` | DATETIME | NO | Activity timestamp (UTC) |
| `plugin_version` | TEXT | NO | Plugin version (e.g., `1.0.0`) |
| `created_at` | DATETIME | NO | Record insertion timestamp |

**Notes:**
- Catch-all table for events not covered by other tables
- `detail` can contain JSON for structured data or plain text
- Examples: minigame participation, achievements, level-ups, teleports
- **Design consideration:** This table is intentionally loose. For high-value event types that emerge from usage (deaths, minigames, PvP), promote them to dedicated tables with typed columns. Use `activity` as an enum-like value (`death`, `minigame_start`, `level_up`, `teleport`) to keep queries reliable. Avoid storing freeform text in `detail` — prefer structured JSON with a known schema per activity type.

---

### 10. plugin_bank

Stores bank contents snapshots with total value.

```sql
CREATE TABLE IF NOT EXISTS plugin_bank (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL,
    items TEXT NOT NULL,                    -- JSON: [{"item_id": 560, "quantity": 10000, "value": 50000}, ...]
    total_value INTEGER NOT NULL,           -- Total bank value in coins
    world INTEGER,                          -- OSRS world number (nullable)
    timestamp DATETIME NOT NULL,            -- Snapshot timestamp (UTC)
    plugin_version TEXT NOT NULL,           -- Plugin version (semver)
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
);

CREATE INDEX idx_plugin_bank_account_ts ON plugin_bank(account_id, timestamp);
CREATE INDEX idx_plugin_bank_value ON plugin_bank(total_value);
```

**Column Details:**

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | INTEGER | NO | Primary key (autoincrement) |
| `account_id` | INTEGER | NO | Foreign key to `accounts(id)` |
| `items` | TEXT | NO | JSON array of bank items with values |
| `total_value` | INTEGER | NO | Total bank value in coins (minimum 0) |
| `world` | INTEGER | YES | OSRS world number (optional) |
| `timestamp` | DATETIME | NO | Snapshot timestamp (UTC) |
| `plugin_version` | TEXT | NO | Plugin version (e.g., `1.0.0`) |
| `created_at` | DATETIME | NO | Record insertion timestamp |

**JSON Structure (`items`):**
```json
[
    {"item_id": 560, "quantity": 10000, "value": 50000},
    {"item_id": 11832, "quantity": 1, "value": 15000000},
    {"item_id": 385, "quantity": 500, "value": 50000},
    {"item_id": 2, "quantity": 1000000, "value": 1000000}
]
```

**Notes:**
- `total_value` redundant with sum of item values but denormalized for query performance
- Enables bank value tracking over time, wealth analytics
- Items array can be very large (up to 816 bank slots + placeholders)
- **Storage warning:** Full bank snapshots at frequent intervals grow fast. Consider client-side delta detection — only sync when bank contents actually change. The plugin should hash the bank state and skip sync if unchanged.

---

### 11. plugin_sync_log

Audit log for all plugin API submissions.

```sql
CREATE TABLE IF NOT EXISTS plugin_sync_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL,
    token_id INTEGER NOT NULL,              -- API token ID used for submission
    category TEXT NOT NULL,                 -- Payload category (e.g., 'xp', 'session', 'batch')
    payload_summary TEXT NOT NULL,          -- JSON: Summary of submitted payload
    synced_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE,
    FOREIGN KEY (token_id) REFERENCES api_tokens(id) ON DELETE CASCADE
);

CREATE INDEX idx_plugin_sync_log_account ON plugin_sync_log(account_id);
CREATE INDEX idx_plugin_sync_log_token ON plugin_sync_log(token_id);
CREATE INDEX idx_plugin_sync_log_category ON plugin_sync_log(category);
CREATE INDEX idx_plugin_sync_log_synced ON plugin_sync_log(synced_at);
```

**Column Details:**

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | INTEGER | NO | Primary key (autoincrement) |
| `account_id` | INTEGER | NO | Foreign key to `accounts(id)` |
| `token_id` | INTEGER | NO | Foreign key to `api_tokens(id)` |
| `category` | TEXT | NO | Payload category (e.g., `xp`, `session`, `loot`, `batch`) |
| `payload_summary` | TEXT | NO | JSON summary of submitted payload |
| `synced_at` | DATETIME | NO | Sync timestamp (UTC) |

**JSON Structure (`payload_summary`):**

For XP snapshot:
```json
{
    "total_xp": 145678900,
    "skill_count": 23
}
```

For session event:
```json
{
    "event": "logout",
    "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

For batch submission:
```json
{
    "categories": ["sessions", "xp", "loot"],
    "total_events": 15
}
```

**Notes:**
- Audit trail for security, debugging, and rate limiting
- `payload_summary` contains minimal data (not full payload) to reduce storage
- Links submissions to specific API tokens for token usage analytics

---

## JSON Structure Documentation

### Skills Object (plugin_xp_snapshots)

All 23 OSRS skills required:

```json
{
    "attack": 13034431,
    "defence": 1154,
    "strength": 4470000,
    "hitpoints": 3000000,
    "ranged": 2500000,
    "prayer": 500000,
    "magic": 1800000,
    "cooking": 1100000,
    "woodcutting": 950000,
    "fletching": 800000,
    "fishing": 700000,
    "firemaking": 600000,
    "crafting": 1300000,
    "smithing": 400000,
    "mining": 850000,
    "herblore": 1200000,
    "agility": 750000,
    "thieving": 900000,
    "slayer": 3500000,
    "farming": 2200000,
    "runecraft": 650000,
    "hunter": 1050000,
    "construction": 1400000
}
```

**Validation:**
- All 23 skills must be present
- XP values must be integers ≥ 0
- Max XP: 200,000,000 per skill

---

### Equipment Object (plugin_equipment)

Standard OSRS equipment slots:

```json
{
    "head": 11832,
    "cape": 21295,
    "neck": 19547,
    "weapon": 11806,
    "body": 11834,
    "shield": 12954,
    "legs": 11836,
    "hands": 7462,
    "feet": 11840,
    "ring": 19550,
    "ammo": 21326
}
```

**Validation:**
- All slots optional (empty slots omitted)
- Item IDs must be valid OSRS item IDs (integers ≥ 0)

---

### Inventory Array (plugin_equipment, plugin_bank)

Array of items with quantities:

```json
[
    {"item_id": 560, "quantity": 1000},
    {"item_id": 555, "quantity": 5000},
    {"item_id": 385, "quantity": 10}
]
```

**Validation:**
- Each item must have `item_id` (integer ≥ 0) and `quantity` (integer ≥ 1)
- No ordering requirements
- For equipment inventory: max 28 items
- For bank: max 816 items

---

### Tier Progress Object (plugin_combat_achievements)

Combat achievement tier counts:

```json
{
    "easy": 15,
    "medium": 8,
    "hard": 3,
    "elite": 1,
    "master": 0,
    "grandmaster": 0
}
```

**Validation:**
- Valid tiers: `easy`, `medium`, `hard`, `elite`, `master`, `grandmaster`
- Counts must be integers ≥ 0

---

### Completed Tasks Array (plugin_combat_achievements)

Array of completed task names:

```json
[
    "Kill Zulrah",
    "Complete Chambers of Xeric",
    "Kill Vorkath with no damage"
]
```

**Validation:**
- Strings (1-100 characters each)
- No duplicates enforced (plugin responsibility)

---

## Index Strategy

### Time-Series Indexes

All plugin tables use time-series indexes for efficient range queries:

```sql
CREATE INDEX idx_plugin_*_timestamp ON plugin_*(timestamp);
```

**Purpose:** Optimize queries like "get all XP snapshots in last 7 days"

### Account Lookup Indexes

All plugin tables indexed by `account_id`:

```sql
CREATE INDEX idx_plugin_*_account ON plugin_*(account_id);
```

**Purpose:** Fast retrieval of player-specific data

### Category-Specific Indexes

#### Session Events
```sql
CREATE INDEX idx_plugin_sessions_session ON plugin_sessions(session_id);
CREATE INDEX idx_plugin_sessions_event ON plugin_sessions(event);
```
**Purpose:** Session tracking, logout duration calculations

#### Collection Log & Loot
```sql
CREATE INDEX idx_plugin_collection_log_item ON plugin_collection_log(item_id);
CREATE INDEX idx_plugin_collection_log_source ON plugin_collection_log(source);
CREATE INDEX idx_plugin_loot_item ON plugin_loot(item_id);
CREATE INDEX idx_plugin_loot_source ON plugin_loot(source);
CREATE INDEX idx_plugin_loot_source_type ON plugin_loot(source_type);
CREATE INDEX idx_plugin_loot_value ON plugin_loot(ge_value);
```
**Purpose:** Item drop analytics, boss profitability, rarity tracking

#### Quests & Diaries
```sql
CREATE INDEX idx_plugin_quests_name ON plugin_quests(quest_name);
CREATE INDEX idx_plugin_quests_state ON plugin_quests(state);
CREATE INDEX idx_plugin_diaries_region ON plugin_diaries(region);
```
**Purpose:** Quest completion tracking, diary progress queries

#### Activity
```sql
CREATE INDEX idx_plugin_activity_activity ON plugin_activity(activity);
```
**Purpose:** Activity type filtering

#### Bank Value
```sql
CREATE INDEX idx_plugin_bank_value ON plugin_bank(total_value);
```
**Purpose:** Wealth leaderboards, bank value analytics

### Audit Indexes
```sql
CREATE INDEX idx_plugin_sync_log_token ON plugin_sync_log(token_id);
CREATE INDEX idx_plugin_sync_log_category ON plugin_sync_log(category);
CREATE INDEX idx_plugin_sync_log_synced ON plugin_sync_log(synced_at);
```
**Purpose:** Token usage analytics, audit queries, rate limiting

### Composite Index Notes

All tables now use `(account_id, timestamp)` composite indexes as the primary index. Additional composite indexes for production:

```sql
-- Loot source + timestamp for boss drop history
CREATE INDEX idx_plugin_loot_source_timestamp ON plugin_loot(source, timestamp);
```

---

## PostgreSQL Migration Notes

### Type Mappings

| SQLite Type | PostgreSQL Type | Notes |
|-------------|-----------------|-------|
| `INTEGER` | `INTEGER` or `BIGINT` | Use BIGINT for XP values (can exceed 2.1B) |
| `TEXT` | `TEXT` or `VARCHAR(n)` | Use VARCHAR for bounded strings (e.g., `VARCHAR(100)`) |
| `TEXT` (JSON) | `JSONB` | **Critical**: Convert all JSON TEXT columns to JSONB |
| `INTEGER` (boolean) | `BOOLEAN` | Convert diary tier columns to proper booleans |
| `DATETIME` | `TIMESTAMPTZ` | Use `TIMESTAMPTZ` for proper timezone support |

### JSON Column Migration

All `*_json` columns should become `JSONB` in PostgreSQL:

```sql
-- SQLite
skills TEXT NOT NULL  -- JSON string

-- PostgreSQL
skills JSONB NOT NULL  -- Native JSON with indexing
```

**Benefits:**
- Native JSON operators (`->`, `->>`, `@>`)
- GIN indexes for fast JSON queries
- Validation at database level

**Example GIN indexes:**
```sql
CREATE INDEX idx_plugin_xp_skills_gin ON plugin_xp_snapshots USING GIN (skills);
CREATE INDEX idx_plugin_equipment_equipment_gin ON plugin_equipment USING GIN (equipment);
CREATE INDEX idx_plugin_combat_achievements_tiers_gin ON plugin_combat_achievements USING GIN (tier_progress);
```

### Boolean Column Migration

Diary tier columns (currently INTEGER 0/1):

```sql
-- SQLite
easy INTEGER NOT NULL DEFAULT 0

-- PostgreSQL
easy BOOLEAN NOT NULL DEFAULT FALSE
```

### Partitioning Strategy

For high-volume production, partition time-series tables by timestamp:

```sql
-- Partition plugin_xp_snapshots by month
CREATE TABLE plugin_xp_snapshots (
    id BIGSERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL,
    skills JSONB NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    ...
) PARTITION BY RANGE (timestamp);

-- Create monthly partitions
CREATE TABLE plugin_xp_snapshots_2026_01 PARTITION OF plugin_xp_snapshots
    FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');

CREATE TABLE plugin_xp_snapshots_2026_02 PARTITION OF plugin_xp_snapshots
    FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');
```

**Benefits:**
- Faster queries (scans only relevant partitions)
- Easier archival (drop old partitions)
- Better maintenance (vacuum per partition)

**Recommended partitioning for:**
- `plugin_xp_snapshots` (high write volume)
- `plugin_loot` (high write volume)
- `plugin_sessions` (high write volume)
- `plugin_sync_log` (audit table, grows large)

### Materialized Views

Optimize common queries with materialized views:

```sql
-- Latest XP per account
CREATE MATERIALIZED VIEW mv_latest_xp AS
SELECT DISTINCT ON (account_id)
    account_id,
    skills,
    timestamp
FROM plugin_xp_snapshots
ORDER BY account_id, timestamp DESC;

CREATE UNIQUE INDEX idx_mv_latest_xp_account ON mv_latest_xp(account_id);

-- Refresh strategy: CONCURRENTLY on schedule or trigger
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_latest_xp;
```

### Constraints

Add constraints not available in SQLite:

```sql
-- World number range
ALTER TABLE plugin_sessions
ADD CONSTRAINT chk_sessions_world CHECK (world >= 300 AND world <= 600);

-- XP validation (prevent negative)
ALTER TABLE plugin_xp_snapshots
ADD CONSTRAINT chk_xp_skills_valid CHECK (
    (skills->>'attack')::BIGINT >= 0 AND
    (skills->>'attack')::BIGINT <= 200000000
);

-- Loot quantity minimum
ALTER TABLE plugin_loot
ADD CONSTRAINT chk_loot_quantity CHECK (quantity >= 1);
```

### Concurrency Considerations

- Use `INSERT ... ON CONFLICT` for idempotent submissions
- Consider `SERIALIZABLE` isolation for batch submissions
- Add advisory locks for session tracking

---

## Sample Queries

### 1. Get Latest XP Snapshot for Account

```sql
SELECT
    id,
    skills,
    timestamp,
    plugin_version
FROM plugin_xp_snapshots
WHERE account_id = ?
ORDER BY timestamp DESC
LIMIT 1;
```

---

### 2. Calculate XP Gains Between Two Timestamps

```sql
-- Get first and last snapshot in range
WITH snapshots AS (
    SELECT
        skills,
        timestamp,
        ROW_NUMBER() OVER (ORDER BY timestamp ASC) as rn_asc,
        ROW_NUMBER() OVER (ORDER BY timestamp DESC) as rn_desc
    FROM plugin_xp_snapshots
    WHERE account_id = ?
      AND timestamp BETWEEN ? AND ?
)
SELECT
    json_extract(latest.skills, '$.attack') - json_extract(earliest.skills, '$.attack') as attack_gain,
    json_extract(latest.skills, '$.strength') - json_extract(earliest.skills, '$.strength') as strength_gain
    -- ... repeat for all skills
FROM
    (SELECT skills FROM snapshots WHERE rn_desc = 1) latest,
    (SELECT skills FROM snapshots WHERE rn_asc = 1) earliest;
```

**PostgreSQL version (using JSONB):**
```sql
SELECT
    (latest.skills->>'attack')::BIGINT - (earliest.skills->>'attack')::BIGINT as attack_gain,
    (latest.skills->>'strength')::BIGINT - (earliest.skills->>'strength')::BIGINT as strength_gain
FROM ...
```

---

### 3. Get Total Playtime (Sum of Session Durations)

```sql
SELECT
    account_id,
    SUM(duration_seconds) as total_playtime_seconds,
    SUM(duration_seconds) / 3600.0 as total_playtime_hours
FROM plugin_sessions
WHERE event = 'logout'
  AND account_id = ?
GROUP BY account_id;
```

---

### 4. Get Collection Log Entries by Source (Boss)

```sql
SELECT
    item_id,
    item_name,
    quantity,
    obtained_at,
    source
FROM plugin_collection_log
WHERE account_id = ?
  AND source = 'General Graardor'
ORDER BY obtained_at DESC;
```

---

### 5. Get Quest Completion Timeline

```sql
SELECT
    quest_name,
    timestamp as completed_at
FROM plugin_quests
WHERE account_id = ?
  AND state = 'complete'
ORDER BY timestamp ASC;
```

---

### 6. Get Diary Completion Progress

```sql
SELECT
    region,
    easy,
    medium,
    hard,
    elite,
    timestamp
FROM plugin_diaries
WHERE account_id = ?
ORDER BY timestamp DESC;
```

---

### 7. Calculate Loot Value by Source

```sql
SELECT
    source,
    source_type,
    COUNT(*) as drop_count,
    SUM(ge_value * quantity) as total_value
FROM plugin_loot
WHERE account_id = ?
  AND ge_value IS NOT NULL
GROUP BY source, source_type
ORDER BY total_value DESC;
```

---

### 8. Get Bank Value Over Time

```sql
SELECT
    timestamp,
    total_value,
    total_value - LAG(total_value) OVER (ORDER BY timestamp) as value_change
FROM plugin_bank
WHERE account_id = ?
ORDER BY timestamp ASC;
```

---

### 9. Get Most Recent Combat Achievement Progress

```sql
SELECT
    tier_progress,
    completed_tasks,
    timestamp
FROM plugin_combat_achievements
WHERE account_id = ?
ORDER BY timestamp DESC
LIMIT 1;
```

---

### 10. Audit Log: Get Recent Syncs by Token

```sql
SELECT
    sl.synced_at,
    sl.category,
    sl.payload_summary,
    a.name as account_name
FROM plugin_sync_log sl
JOIN accounts a ON sl.account_id = a.id
WHERE sl.token_id = ?
ORDER BY sl.synced_at DESC
LIMIT 50;
```

---

### 11. Get Active Sessions (Login without Logout)

```sql
SELECT
    login.session_id,
    login.world,
    login.timestamp as login_time
FROM plugin_sessions login
LEFT JOIN plugin_sessions logout
    ON login.session_id = logout.session_id
    AND logout.event = 'logout'
WHERE login.account_id = ?
  AND login.event = 'login'
  AND logout.id IS NULL
ORDER BY login.timestamp DESC;
```

---

### 12. Get Rarest Drops (Collection Log Items)

```sql
SELECT
    item_id,
    item_name,
    source,
    COUNT(*) as total_obtained
FROM plugin_collection_log
GROUP BY item_id, item_name, source
HAVING COUNT(*) <= 5
ORDER BY total_obtained ASC, item_name ASC;
```

---

## Schema Evolution

### Future Enhancements

1. **Add skill hiscores tracking** - Store hiscores API data alongside plugin XP
2. **Add death tracking** - New `plugin_deaths` table for death events
3. **Add PvP tracking** - New `plugin_pvp` table for PK events
4. **Add minigame scores** - New `plugin_minigames` table (e.g., LMS, Soul Wars)
5. **Add chat logs** - New `plugin_chat` table (privacy considerations!)

### Migration Versioning

Follow existing pattern in `database/sql/`:

- `013_plugin_api_tables.sql` - Initial plugin tables (this schema)
- `014_plugin_indexes.sql` - Additional indexes based on production analytics
- `015_plugin_partitions.sql` - PostgreSQL partitioning setup

---

## Performance Considerations

### Write Optimization

- **Batch submissions preferred**: Use `/batch` endpoint to reduce HTTP overhead
- **Connection pooling**: Configure adequate pool size for concurrent writes
- **Async inserts**: Consider async commit in PostgreSQL for higher throughput
- **Prepared statements**: Reuse prepared statements for repeated inserts

### Read Optimization

- **Materialized views**: Pre-compute expensive aggregations (XP gains, playtime)
- **Query result caching**: Cache common queries (latest XP, bank value) at application level
- **Partial indexes**: Use partial indexes for common filtered queries (e.g., `WHERE event = 'logout'`)
- **Covering indexes**: Add additional columns to indexes to avoid table lookups

### Storage Optimization

- **JSON compression**: PostgreSQL JSONB is compressed by default
- **Partition pruning**: Drop old partitions after archival
- **Vacuum strategy**: Tune autovacuum for write-heavy tables

---

## Security Considerations

1. **PII in JSON**: Be cautious with `detail` fields in `plugin_activity` - avoid storing chat messages or sensitive data
2. **Rate limiting**: Use `plugin_sync_log` for per-token rate limiting
3. **Data retention**: Implement retention policies (e.g., archive data older than 2 years)
4. **Audit trail**: `plugin_sync_log` provides complete submission audit trail
5. **Token rotation**: Encourage regular API token rotation

---

**End of Schema Documentation**
