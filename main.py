"""Entrypoint for running OSRS snapshot tasks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from rich.console import Console

from agents.osrs_snapshot_agent import SnapshotAgent
from agents.report_agent import ReportAgent


def load_accounts(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch OSRS hiscore snapshots.")
    parser.add_argument("--accounts", type=Path, default=Path("config/accounts.json"), help="Path to accounts JSON file.")
    parser.add_argument("--output", type=Path, default=Path("data/snapshots"), help="Snapshot output directory.")
    parser.add_argument("--player", type=str, help="Override player name for single fetch.")
    parser.add_argument("--mode", type=str, default="main", help="Override mode when using --player.")
    return parser.parse_args()


def main() -> None:
    console = Console()
    args = parse_args()

    accounts = load_accounts(args.accounts)
    if args.player:
        accounts = [{"name": args.player, "mode": args.mode}]

    if not accounts:
        console.print("[yellow]No accounts configured. Exiting.[/yellow]")
        return

    agent = SnapshotAgent(args.output, config_path=Path("config/project.json"))
    report_agent = ReportAgent(Path("reports"), scribe_config=Path("config/project.json"))
    results = agent.run(accounts)

    for result in results:
        if result.success:
            console.print(f"[green]✓[/green] {result.player} ({result.mode}) → {result.snapshot_path}")
            report_path = None
            if result.payload and result.snapshot_path:
                report = report_agent.build_from_payload(
                    payload=result.payload,
                    report_source=result.snapshot_path,
                    delta_summary=result.delta_summary,
                )
                report_path = report.report_path if report.success else None
            if report_path:
                console.print(f"   [cyan]Report[/cyan] {report_path}")
        else:
            console.print(f"[red]✗[/red] {result.player} ({result.mode}) → {result.message}")


if __name__ == "__main__":
    main()
