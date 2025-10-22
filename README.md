# Codex OSRS Snapshot Agent

Automated toolkit for fetching, diffing, and reporting Old School RuneScape hiscore snapshots. It retrieves player stats, detects mode changes, stores timestamped JSON payloads, and generates Markdown reports ready to paste or archive. Scribe-based logging keeps the entire workflow observable.

## Features
- **SnapshotAgent** – resolves gamemode, fetches JSON, computes deltas, logs to Scribe, and writes snapshots under `data/snapshots/<player>/`.
- **ReportAgent** – produces professional Markdown reports with totals, grouped activities, change tables, and snapshot hashes in `reports/<player>/`.
- **Scribe Logger** – reusable CLI/SDK for structured progress logging (emoji-first format, metadata, dry-run support).
- **Tkinter GUI** – open `python -m app.gui`, type an RSN, and the app fetches everything while auto-copying the Markdown plus JSON path to the clipboard.
- **CLI Runner** – run snapshots from the terminal (single player or batch via `config/accounts.json`).
- **Mode Cache & Activity Index** – figure out a player’s current hiscore listing and keep activity IDs fresh with optional scraping (cache fallback available offline).
- **Pytest Suite** – sanity checks for normalization, delta logic, report generation, mode caching, and logging helpers.

## Quick Start
1. **Install dependencies**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure project metadata**
   ```json
   // config/project.json
   {
     "project_name": "codex-osrs-snapshot",
     "progress_log": "docs/dev_plans/osrs_snapshot_agent/PROGRESS_LOG.md",
     "default_emoji": "ℹ️",
     "default_agent": "Scribe"
   }
   ```

3. **Optional:** define tracked accounts
   ```json
   // config/accounts.json
   [
     {"name": "ArchonBorn", "mode": "hardcore"},
     {"name": "Lynx Titan", "mode": "main"}
   ]
   ```

4. **Run from CLI**
   ```bash
   python main.py                    # uses config/accounts.json
   python main.py --player Karma     # single snapshot (auto mode detection)
   python main.py --player "Iron O_o" --mode ironman
   ```
   Outputs:
   - JSON snapshot under `data/snapshots/<player>/<timestamp>.json`
   - Markdown report under `reports/<player>/<snapshot_id>.md`
   - Clipboard copy with report + JSON link (if clipboard backend available)
   - Scribe log entry (progress log in `docs/dev_plans/osrs_snapshot_agent/PROGRESS_LOG.md`)

5. **Launch GUI**
   ```bash
   python -m app.gui
   ```
   Type a RuneScape name, choose mode (or Auto-detect), click “Fetch Snapshot”. The GUI reuses the agents above and copies report output to the clipboard automatically.

## Scribe Logging
Use the provided CLI utility to append structured entries:
```bash
python scripts/scribe.py "SnapshotAgent fetched hiscore report" \
  --agent SnapshotAgent --status success \
  --meta player=ArchonBorn result=success path=data/snapshots/ArchonBorn/...
```
Logs land in `docs/dev_plans/osrs_snapshot_agent/PROGRESS_LOG.md` with emoji-first format. SnapshotAgent and ReportAgent call Scribe automatically, so manual logging is only needed for manual operations or new tooling.

## Tests
```bash
pytest
```
Covers normalization, delta generation, report rendering, mode cache persistence, and Scribe integration helpers.

## Next Steps / Ideas
- Retry/backoff strategy for API hiccups.
- Async batch runner for multiple players.
- Dashboard integrations (Streamlit, Grafana, etc.).
- Snapshot diff visualizations or notifications (Discord, Slack).

## License
MIT (feel free to adapt the logging/report infrastructure for other projects).
