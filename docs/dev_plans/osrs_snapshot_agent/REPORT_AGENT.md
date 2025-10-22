# ReportAgent Overview

## Purpose
Generate Markdown reports (`reports/<player>/<snapshot_id>.md`) summarizing each snapshot. Reports include metadata (schema version, snapshot ID, SHA-256 hash, total level/XP), grouped activity tables, change tables, and embedded JSON.

## Integration
- Invoked by `main.py` after SnapshotAgent completes (with payload + delta summary).
- Uses `core/report_builder.py` for rendering.
- Logs completion via Scribe (`Agent: ReportAgent`).

## Future Enhancements
- Optionally ingest into dashboards or LLM summary pipeline.
- Attach delta highlights (top gains, bosses, clues) visually.
