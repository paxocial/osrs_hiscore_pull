# Database Migrations

Place SQL migration files here as numbered `*.sql` files.
They will be applied to your council's dedicated database schema.

## File Naming

Use sequential numbering:
```
001_create_game_states.sql
002_add_rom_maps.sql
003_add_indexes.sql
```

## Example Migration

```sql
-- Game state snapshots
CREATE TABLE IF NOT EXISTS game_states (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    data JSONB NOT NULL DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_game_states_name ON game_states(name);
```

## Usage

```bash
council db status    # Show pending/applied migrations
council db migrate   # Apply pending migrations
council db migrate --dry-run  # Preview what would run
```

Note: Each council gets its own Postgres schema (council_<slug>).
The `SET search_path` is handled automatically — just write table DDL.
