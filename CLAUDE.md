# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the **Codex OSRS Snapshot Agent** - a Python toolkit for fetching, storing, and reporting on Old School RuneScape hiscore data. The system ingests JSON snapshots from Jagex's hiscores API, computes deltas between snapshots, and generates Markdown reports with structured logging via Scribe.

## Core Architecture

The system follows an agent-based architecture with clear separation of concerns:

- **SnapshotAgent** (`agents/osrs_snapshot_agent.py`) - Main orchestrator for fetching hiscores data, resolving gamemodes, computing deltas, and persisting snapshots
- **ReportAgent** (`agents/report_agent.py`) - Generates Markdown reports from snapshot payloads with change summaries
- **Core Layer** (`core/`) - Low-level utilities:
  - `hiscore_client.py` - HTTP client for OSRS hiscores API with endpoint resolution
  - `mode_cache.py` - Caches player gamemode detection to avoid repeated API calls
  - `index_discovery.py` - Scrapes activity index when cache is stale
  - `processing.py` - Normalizes snapshot data and computes deltas
  - `report_builder.py` - Renders Markdown content
  - `constants.py` - Game mode definitions, skill/activity mappings
- **Support Layer** (`support/`) - Shared utilities like Scribe logging integration
- **GUI Application** (`app/gui.py`) - Tkinter interface for interactive snapshot fetching

## Common Development Commands

### Environment Setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Running the Application
```bash
# Run snapshots for configured accounts (config/accounts.json)
python main.py

# Single player snapshot with auto mode detection
python main.py --player "PlayerName"

# Single player with explicit mode
python main.py --player "PlayerName" --mode ironman

# Launch GUI interface
python -m app.gui
```

### Testing
```bash
pytest                    # Run all tests
pytest tests/test_processing.py  # Run specific test file
```

### Scribe Logging (Development Workflow)
```bash
# Manual logging entries
python scripts/scribe.py "Completed task" \
  --agent YourAgent --status success \
  --meta player=PlayerName duration_ms=842

# Preview entry without writing
python scripts/scribe.py "Test entry" --dry-run
```

## Key Configuration Files

- `config/project.json` - Project metadata and Scribe log path
- `config/accounts.json` - Player accounts and modes for batch processing
- `config/mode_cache.json` - Cached gamemode detection results
- `config/activity_index_cache.json` - Activity ID mappings from web scraping

## Data Flow Patterns

1. **Snapshot Creation**: `SnapshotAgent.run()` → `HiscoreClient` → mode resolution → delta computation → file persistence → Scribe logging
2. **Report Generation**: `ReportAgent.build_from_payload()` → `ReportBuilder` → Markdown rendering → file output → Scribe logging
3. **Mode Detection**: Check cache → API endpoint attempts → cache update → fallback resolution

## Directory Structure Conventions

- `data/snapshots/<player>/<timestamp>.json` - Raw snapshot storage
- `reports/<player>/<snapshot_id>.md` - Generated Markdown reports
- `docs/dev_plans/osrs_snapshot_agent/PROGRESS_LOG.md` - Scribe progress log entries

## Important Development Notes

- All agents auto-log to Scribe - manual logging only needed for custom tooling
- Snapshot filenames use deterministic format: `YYYYMMDD_HHMMSS.json`
- API rate limiting enforced (≤5 concurrent calls when batching)
- Mode cache persists across runs to optimize gamemode detection
- Activity index cache enables offline fallback for activity ID resolution
- GUI application reuses same agents as CLI for consistency

## Testing Strategy

Tests cover:
- Snapshot data normalization and delta computation
- Mode cache persistence and lookup
- Report generation and Markdown rendering
- Scribe logging integration helpers
- HiscoreClient API interaction patterns