# ReportAgent Overview

## Purpose
Generate Markdown reports (`reports/<player>/<snapshot_id>.md`) summarizing each snapshot. Reports include metadata, total level/XP, skill table, notable activities, and embedded snapshot JSON.

## Integration
- Invoked by `main.py` after SnapshotAgent completes.
- Uses `core/report_builder.py` for rendering.
- Logs completion via Scribe (`Agent: ReportAgent`).

## Future Enhancements
- Optionally ingest into dashboards or LLM summary pipeline.
- Attach delta highlights (top gains, bosses, clues) visually.
